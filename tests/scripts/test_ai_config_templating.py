"""Provenance of a repository value, and what the reconciler may do with it.

`docs/design/ai-config-claude-boundaries.md` states the invariant these cover:
"Live resolved value must not become the portable source declaration." It used
to be enforced by hand through one manifest binding per profile-dependent field.
It now holds for every leaf a Jinja expression produced, which is decided by
rendering the source twice — once against the real variables, once against
type-preserving probes — and taking every leaf that differs.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
import yaml
from ai_config import (
    Change,
    ChangeKind,
    ConfigurationFormat,
    EngineKind,
    EnginePaths,
    FieldManifest,
    FieldRule,
    FieldScope,
    MissingValue,
    ReconciliationPlan,
    SemanticSnapshot,
    SnapshotError,
    TemplateError,
    build_repository_document,
    divergent_paths,
    load_template_variables,
    parse_snapshot,
    probe_variables,
    render_source,
    resolve_engine_paths,
)
from ai_config.decisions import DecisionSet, DecisionSource, FieldDecision
from ai_config.resolution import OperationMode, ResolutionError, resolve_documents
from ai_config.service import inspect_engine, operate_engine

if TYPE_CHECKING:
    from pathlib import Path

NO_DECISIONS = DecisionSet(decisions=())
VARIABLES = {
    "devbox_active_profile": "personal",
    "devbox_langfuse_user_id": "someone@example.com",
    "devbox_hook_timeout": 60,
    "devbox_enable_sandbox": True,
    "devbox_extra_allow": ["Bash(git status)"],
}


def document(source: str, configuration_format: ConfigurationFormat = ConfigurationFormat.JSON):
    return build_repository_document(source.encode(), configuration_format, VARIABLES)


def provenance(
    source: str,
    configuration_format: ConfigurationFormat = ConfigurationFormat.JSON,
) -> frozenset[tuple[str, ...]]:
    """The probe comparison alone, for sources whose unrendered form does not parse."""
    rendered = parse_snapshot(render_source(source.encode(), VARIABLES), configuration_format)
    probe = parse_snapshot(
        render_source(source.encode(), probe_variables(VARIABLES)),
        configuration_format,
    )
    return divergent_paths(rendered, probe)


class TestTemplatedPathDetection:
    def test_a_literal_only_document_has_no_templated_path(self) -> None:
        assert document('{"model": "opus", "nested": {"value": 1}}').templated_paths == frozenset()

    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("{{ devbox_active_profile }}", "personal"),
            ("{{ devbox_active_profile }}-suffix", "personal-suffix"),
            ("prefix-{{ devbox_active_profile }}", "prefix-personal"),
            ("{{ devbox_active_profile | upper }}", "PERSONAL"),
            ("{{ devbox_langfuse_user_id.split('@')[1] }}", "example.com"),
        ],
    )
    def test_a_partly_templated_string_is_templated(
        self,
        expression: str,
        expected: str,
    ) -> None:
        rendered = document(json.dumps({"value": expression}))
        values = {
            field.path: field.value.value  # type: ignore[union-attr]
            for field in rendered.rendered.semantic_fields()
        }

        assert rendered.templated_paths == {("value",)}
        assert values[("value",)] == expected

    def test_a_templated_item_marks_the_whole_array(self) -> None:
        """Arrays are atomic leaves here, so the array is the unit of provenance."""
        source = json.dumps(
            {
                "permissions": {
                    "allow": ["Read", "{{ devbox_active_profile }}", "Write"],
                    "deny": ["Bash(rm -rf /)"],
                }
            }
        )

        assert document(source).templated_paths == {("permissions", "allow")}

    def test_a_control_block_marks_the_leaves_it_governs(self) -> None:
        """A leaf that only one of the two renders produces counts as templated."""
        source = (
            '{"always": "literal"'
            '{% if devbox_enable_sandbox %}, "sandbox": {"enabled": true}{% endif %}}'
        )

        assert provenance(source) == {("sandbox", "enabled")}

    @pytest.mark.parametrize(
        ("expression", "path"),
        [
            ("timeout = {{ devbox_hook_timeout }}", ("timeout",)),
            ("enabled = {{ devbox_enable_sandbox | lower }}", ("enabled",)),
            ("allow = {{ devbox_extra_allow | tojson }}", ("allow",)),
        ],
    )
    def test_non_string_variables_are_probed_without_breaking_the_document(
        self,
        expression: str,
        path: tuple[str, ...],
    ) -> None:
        """A probe keeps its variable's type, so the probe render still parses.

        An integer probed with a string would leave `timeout = <marker>`, which
        is not TOML, and provenance would be unavailable rather than wrong.
        """
        assert provenance(expression, ConfigurationFormat.TOML) == {path}

    def test_an_unrendered_source_that_does_not_parse_is_rejected(self) -> None:
        """The unrendered structure is the write-back base, so it must parse.

        That confines Jinja to value positions: an expression spanning keys or
        table headers would leave a capture with nowhere to write.
        """
        source = '{"always": "literal"{% if devbox_enable_sandbox %}, "extra": 1{% endif %}}'

        with pytest.raises(SnapshotError):
            document(source)

    def test_a_probe_differs_from_every_real_value(self) -> None:
        probes = probe_variables(VARIABLES)

        assert set(probes) == set(VARIABLES)
        assert all(probes[name] != VARIABLES[name] for name in VARIABLES)

    def test_detection_compares_rendered_documents_not_source_text(self) -> None:
        """Provenance is structural, so it survives any spelling of the expression."""
        rendered = SemanticSnapshot.from_value({"a": "personal", "b": "literal"})
        probe = SemanticSnapshot.from_value({"a": "probe", "b": "literal"})

        assert divergent_paths(rendered, probe) == {("a",)}

    def test_an_expression_no_variable_reaches_is_still_templated(self) -> None:
        """The probe render alone would miss it: both contexts produce `ab`.

        The second comparison, rendered against unrendered, catches it — otherwise
        a live edit would replace the expression with one profile's literal.
        """
        source = json.dumps({"value": "{{ 'a' ~ 'b' }}", "plain": "literal"})

        assert provenance(source) == frozenset()
        assert document(source).templated_paths == {("value",)}

    def test_an_undefined_variable_is_an_error_rather_than_an_empty_string(self) -> None:
        with pytest.raises(TemplateError, match="devbox_missing"):
            render_source(b'{"value": "{{ devbox_missing }}"}', VARIABLES)


def test_resolution_refuses_to_capture_a_templated_change_it_is_handed() -> None:
    """The enforcement point, reached by handing it the plan the planner will not make.

    `_plan_field` routes every templated path to apply-repo, so this guard is
    unreachable through the normal flow. It exists so that a later change to the
    classification cannot reopen the write-back route unnoticed.
    """
    change = Change(
        path=("value",),
        kind=ChangeKind.CAPTURE_LIVE,
        scope=FieldScope.SHARED,
        base=MissingValue.MISSING,
        repo=MissingValue.MISSING,
        live=MissingValue.MISSING,
        sensitive=False,
        templated=True,
    )

    with pytest.raises(ResolutionError, match="templated"):
        resolve_documents(
            plan=ReconciliationPlan(changes=(change,)),
            repository=SemanticSnapshot.from_value({"value": "{{ devbox_active_profile }}"}),
            resolved_repository=SemanticSnapshot.from_value({"value": "personal"}),
            live=SemanticSnapshot.from_value({"value": "hand-edited"}),
            manifest=FieldManifest(rules=(FieldRule(path=("value",), scope=FieldScope.SHARED),)),
            mode=OperationMode.RECONCILE,
            decisions=DecisionSet(
                decisions=(FieldDecision(path=("value",), source=DecisionSource.LIVE),),
            ),
            live_exists=True,
        )


@dataclass(frozen=True, slots=True)
class TemplatedTree:
    engine: EngineKind
    repo_root: Path
    home: Path
    state_root: Path
    paths: EnginePaths


CLAUDE_MANIFEST = json.dumps(
    {
        "schema_version": 1,
        "engine": "claude",
        "fields": [
            {"path": "templated", "scope": "shared"},
            {"path": "literal", "scope": "shared"},
        ],
    }
)
CODEX_MANIFEST = json.dumps(
    {
        "schema_version": 1,
        "engine": "codex",
        "fields": [
            {"path": "otel", "scope": "shared"},
            {"path": "personality", "scope": "shared"},
        ],
    }
)
CLAUDE_SOURCE = '{"templated": "{{ devbox_active_profile }}-edge", "literal": "repository"}\n'
CODEX_SOURCE = (
    'personality = "repository"\n\n[otel]\nenvironment = "{{ devbox_active_profile }}-edge"\n'
)
TEMPLATED_PATH = {EngineKind.CLAUDE: ("templated",), EngineKind.CODEX: ("otel", "environment")}
LITERAL_PATH = {EngineKind.CLAUDE: ("literal",), EngineKind.CODEX: ("personality",)}


def build_templated_tree(tmp_path: Path, engine: EngineKind) -> TemplatedTree:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    paths.repository.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    source, manifest = (
        (CLAUDE_SOURCE, CLAUDE_MANIFEST)
        if engine is EngineKind.CLAUDE
        else (CODEX_SOURCE, CODEX_MANIFEST)
    )
    paths.repository.write_text(source, encoding="utf-8")
    paths.manifest.write_text(manifest, encoding="utf-8")
    overlay = repo_root / "profiles" / "personal.yml"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(yaml.safe_dump({"devbox_active_profile": "personal"}), encoding="utf-8")
    return TemplatedTree(
        engine=engine,
        repo_root=repo_root,
        home=home,
        state_root=tmp_path / "state",
        paths=paths,
    )


def operate(
    tree: TemplatedTree,
    *,
    mode: OperationMode = OperationMode.APPLY,
    decisions: DecisionSet = NO_DECISIONS,
):
    return operate_engine(
        tree.engine,
        repo_root=tree.repo_root,
        home=tree.home,
        state_root=tree.state_root,
        profile="personal",
        mode=mode,
        decisions=decisions,
        check=False,
    )


def hand_edit_live(tree: TemplatedTree, templated: str, literal: str) -> None:
    if tree.engine is EngineKind.CLAUDE:
        tree.paths.live.write_text(
            json.dumps({"templated": templated, "literal": literal}) + "\n",
            encoding="utf-8",
        )
        return
    tree.paths.live.write_text(
        f'personality = "{literal}"\n\n[otel]\nenvironment = "{templated}"\n',
        encoding="utf-8",
    )


def read_live(tree: TemplatedTree) -> dict[str, object]:
    text = tree.paths.live.read_text(encoding="utf-8")
    return json.loads(text) if tree.engine is EngineKind.CLAUDE else tomllib.loads(text)


def live_templated_value(tree: TemplatedTree) -> object:
    live = read_live(tree)
    if tree.engine is EngineKind.CLAUDE:
        return live["templated"]
    otel = live["otel"]
    assert isinstance(otel, dict)
    return otel["environment"]


@pytest.mark.parametrize("engine", [EngineKind.CLAUDE, EngineKind.CODEX])
class TestTemplatedFieldIsNeverCaptured:
    def test_a_diverged_templated_field_is_reported_and_leaves_the_source_alone(
        self,
        tmp_path: Path,
        engine: EngineKind,
    ) -> None:
        tree = build_templated_tree(tmp_path, engine)
        operate(tree)
        source_before = tree.paths.repository.read_bytes()
        hand_edit_live(tree, templated="hand-edited", literal="repository")

        inspection = inspect_engine(
            engine,
            repo_root=tree.repo_root,
            home=tree.home,
            profile="personal",
            state_root=tree.state_root,
        )
        change = next(
            item for item in inspection.plan.changes if item.path == TEMPLATED_PATH[engine]
        )
        result = operate(tree)

        assert change.templated is True
        assert change.kind is ChangeKind.APPLY_REPO
        assert result.captured == 0
        assert tree.paths.repository.read_bytes() == source_before
        assert live_templated_value(tree) == "personal-edge"

    def test_a_decision_cannot_route_a_templated_field_back_into_the_source(
        self,
        tmp_path: Path,
        engine: EngineKind,
    ) -> None:
        """Choosing live is refused rather than silently ignored."""
        tree = build_templated_tree(tmp_path, engine)
        operate(tree)
        source_before = tree.paths.repository.read_bytes()
        hand_edit_live(tree, templated="hand-edited", literal="repository")
        decisions = DecisionSet(
            decisions=(FieldDecision(path=TEMPLATED_PATH[engine], source=DecisionSource.LIVE),),
        )

        with pytest.raises(ResolutionError):
            operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)

        assert tree.paths.repository.read_bytes() == source_before

    def test_a_literal_neighbour_is_still_capturable(
        self,
        tmp_path: Path,
        engine: EngineKind,
    ) -> None:
        """The guard is per leaf, and a capture must not flatten the expression."""
        tree = build_templated_tree(tmp_path, engine)
        operate(tree)
        hand_edit_live(tree, templated="hand-edited", literal="live-choice")
        decisions = DecisionSet(
            decisions=(FieldDecision(path=LITERAL_PATH[engine], source=DecisionSource.LIVE),),
        )

        result = operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)
        source = tree.paths.repository.read_text(encoding="utf-8")

        assert result.captured == 1
        assert "live-choice" in source
        assert "{{ devbox_active_profile }}-edge" in source
        assert live_templated_value(tree) == "personal-edge"

    def test_the_source_still_renders_for_another_profile_after_a_capture(
        self,
        tmp_path: Path,
        engine: EngineKind,
    ) -> None:
        """The point of refusing the capture: the source stays profile-agnostic."""
        tree = build_templated_tree(tmp_path, engine)
        operate(tree)
        hand_edit_live(tree, templated="hand-edited", literal="live-choice")
        operate(
            tree,
            mode=OperationMode.RECONCILE,
            decisions=DecisionSet(
                decisions=(FieldDecision(path=LITERAL_PATH[engine], source=DecisionSource.LIVE),),
            ),
        )
        (tree.repo_root / "profiles" / "work.yml").write_text(
            yaml.safe_dump({"devbox_active_profile": "work"}),
            encoding="utf-8",
        )

        rendered = build_repository_document(
            tree.paths.repository.read_bytes(),
            ConfigurationFormat.JSON if engine is EngineKind.CLAUDE else ConfigurationFormat.TOML,
            load_template_variables(tree.repo_root, "work"),
        )
        values = {field.path: field.value for field in rendered.rendered.semantic_fields()}

        assert rendered.templated_paths == {TEMPLATED_PATH[engine]}
        assert values[TEMPLATED_PATH[engine]].value == "work-edge"  # type: ignore[union-attr]
