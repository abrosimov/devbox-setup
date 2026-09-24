from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from ai_config import (
    Change,
    ChangeKind,
    ConfigurationFormat,
    FieldManifest,
    FieldScope,
    ReconciliationPlan,
    SemanticSnapshot,
    build_repository_document,
    load_template_variables,
    plan_reconciliation,
    to_plain_value,
)
from ai_config.adapters import EngineKind, parse_engine_manifest
from ai_config_fixtures import REPO_ROOT

MANIFEST_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_codex" / ("config.ai-config.json")
CONFIG_TEMPLATE_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_codex" / ("config.toml.j2")
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ai_config" / "codex"


class TestCodexManifestCoverage:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return parse_engine_manifest(EngineKind.CODEX, MANIFEST_PATH.read_bytes())

    @pytest.fixture
    def repository(self) -> SemanticSnapshot:
        source = CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")
        return SemanticSnapshot.from_value(tomllib.loads(source))

    def test_unrendered_template_parses_with_a_quoted_profile_placeholder(
        self,
        repository: SemanticSnapshot,
    ) -> None:
        """Only the unrendered document can absorb a captured value.

        Its structure is what a capture edits, so Jinja has to stay inside a
        quoted TOML value rather than spanning keys or tables.
        """
        values = {field.path: to_plain_value(field.value) for field in repository.semantic_fields()}

        assert values[("otel", "environment")] == "{{ devbox_active_profile }}"

    @pytest.mark.parametrize("profile", ["personal", "work"])
    def test_environment_renders_the_selected_profile_and_is_the_only_templated_path(
        self,
        profile: str,
    ) -> None:
        document = build_repository_document(
            CONFIG_TEMPLATE_PATH.read_bytes(),
            ConfigurationFormat.TOML,
            load_template_variables(REPO_ROOT, profile),
        )
        values = {
            field.path: to_plain_value(field.value) for field in document.rendered.semantic_fields()
        }

        assert document.templated_paths == {("otel", "environment")}
        assert values[("otel", "environment")] == profile

    def test_every_current_repository_field_is_classified(
        self,
        manifest: FieldManifest,
        repository: SemanticSnapshot,
    ) -> None:
        unclassified = [
            field.path
            for field in repository.semantic_fields()
            if manifest.scope_for(field.path) is None
        ]

        assert unclassified == []

    @pytest.mark.parametrize(
        ("path", "expected_scope"),
        [
            (("personality",), FieldScope.SHARED),
            (("model",), FieldScope.PREFERENCE),
            (("model_reasoning_effort",), FieldScope.PREFERENCE),
            (("service_tier",), FieldScope.SHARED),
            (("sandbox_mode",), FieldScope.SHARED),
            (("features", "memories"), FieldScope.SHARED),
            (("features", "hooks"), FieldScope.SHARED),
            (("hooks", "PreToolUse"), FieldScope.SHARED),
            (("sandbox_workspace_write", "network_access"), FieldScope.SHARED),
            (("otel", "log_user_prompt"), FieldScope.SHARED),
            (("otel", "exporter", "otlp-grpc", "endpoint"), FieldScope.SHARED),
            (("otel", "trace_exporter"), FieldScope.SHARED),
            (("otel", "metrics_exporter", "otlp-grpc", "endpoint"), FieldScope.SHARED),
            (("otel", "environment"), FieldScope.SHARED),
        ],
    )
    def test_current_repository_field_scope(
        self,
        manifest: FieldManifest,
        repository: SemanticSnapshot,
        path: tuple[str, ...],
        expected_scope: FieldScope,
    ) -> None:
        repository_paths = {field.path for field in repository.semantic_fields()}

        assert path in repository_paths
        assert manifest.scope_for(path) is expected_scope


class TestCodexManifestClassification:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        runtime_key = "/Users/example/.codex/config.toml:session_start:0:0"
        runtime = SemanticSnapshot.from_value(
            {
                "hooks": {
                    "state": {
                        runtime_key: {
                            "enabled": True,
                            "trusted_hash": "sha256:runtime",
                        }
                    }
                }
            }
        )
        return parse_engine_manifest(
            EngineKind.CODEX,
            MANIFEST_PATH.read_bytes(),
            runtime_snapshots=(runtime,),
        )

    @pytest.mark.parametrize(
        ("path", "expected_scope"),
        [
            (("features", "js_repl"), FieldScope.SHARED),
            (("hooks", "SessionStart"), FieldScope.SHARED),
            (
                (
                    "hooks",
                    "state",
                    "/Users/example/.codex/config.toml:session_start:0:0",
                    "trusted_hash",
                ),
                FieldScope.RUNTIME,
            ),
            (("plugins", "example", "enabled"), FieldScope.SHARED),
            (("marketplaces", "example", "enabled"), FieldScope.RUNTIME),
            (
                ("marketplaces", "openai-bundled", "source"),
                FieldScope.RUNTIME,
            ),
            (
                ("marketplaces", "openai-bundled", "last_updated"),
                FieldScope.RUNTIME,
            ),
            (("desktop", "analytics"), FieldScope.LOCAL_STATE),
            (("tui", "notifications"), FieldScope.SHARED),
            (("tui", "model_availability_nux", "gpt-5.5"), FieldScope.RUNTIME),
            (("tool_suggest", "enabled"), FieldScope.SHARED),
            (("skills", "config", "example-skill", "enabled"), FieldScope.SHARED),
            (("mcp_servers", "example", "command"), FieldScope.RUNTIME),
            (("projects", "/Users/example/project", "trust_level"), FieldScope.LOCAL_STATE),
            (("notify",), FieldScope.LOCAL_STATE),
            (("notice", "model_migrations", "gpt-example"), FieldScope.RUNTIME),
            (("notice", "unrecognised"), FieldScope.RUNTIME),
            (("hooks", "state"), None),
            (("hooks", "state", "dynamic"), None),
            (("hooks", "state", "dynamic", "unexpected"), None),
            (("hooks", "state", "dynamic", "enabled", "nested"), None),
            (("state", "opaque"), None),
        ],
    )
    def test_classifies_only_supported_paths(
        self,
        manifest: FieldManifest,
        path: tuple[str, ...],
        expected_scope: FieldScope | None,
    ) -> None:
        assert manifest.scope_for(path) is expected_scope

    @pytest.mark.parametrize("field", ["enabled", "trusted_hash"])
    def test_hook_runtime_state_is_preserved(
        self,
        field: str,
    ) -> None:
        runtime_key = "/Users/example/.codex/config.toml:session_end:0:0"
        live_value: object = True if field == "enabled" else "sha256:runtime"
        live = SemanticSnapshot.from_value({"hooks": {"state": {runtime_key: {field: live_value}}}})
        manifest = parse_engine_manifest(
            EngineKind.CODEX,
            MANIFEST_PATH.read_bytes(),
            runtime_snapshots=(live,),
        )
        plan = plan_reconciliation(
            base=SemanticSnapshot.from_value({}),
            repo=SemanticSnapshot.from_value({}),
            live=live,
            manifest=manifest,
        )
        changes = {change.path: change for change in plan.changes}
        path = ("hooks", "state", runtime_key, field)

        assert changes[path].kind is ChangeKind.PRESERVE_LOCAL
        assert changes[path].scope is FieldScope.RUNTIME


class TestCodexManifestReconciliation:
    @pytest.fixture
    def plan(self) -> ReconciliationPlan:
        return plan_reconciliation(
            base=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "base.json"),
            repo=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "repo.json"),
            live=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "live.json"),
            manifest=parse_engine_manifest(EngineKind.CODEX, MANIFEST_PATH.read_bytes()),
        )

    @pytest.fixture
    def changes(self, plan: ReconciliationPlan) -> dict[tuple[str, ...], Change]:
        return {change.path: change for change in plan.changes}

    @pytest.mark.parametrize(
        "path",
        [
            ("features", "memories"),
        ],
    )
    def test_repository_changes_are_apply_repo(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.APPLY_REPO
        assert changes[path].scope is FieldScope.SHARED

    @pytest.mark.parametrize(
        "path",
        [
            ("plugins", "example", "enabled"),
            ("tui", "notifications"),
            ("tool_suggest", "enabled"),
            ("skills", "config", "example-skill", "enabled"),
        ],
    )
    def test_portable_live_changes_are_capture_live(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.CAPTURE_LIVE
        assert changes[path].scope is FieldScope.SHARED

    def test_templated_environment_applies_repository_instead_of_capturing_live(self) -> None:
        """Same fixture, same divergence, opposite outcome from the templated flag.

        Without it the live value would be captured into the TOML source, which
        would replace `{{ devbox_active_profile }}` with one profile's name.
        """
        path = ("otel", "environment")
        manifest = parse_engine_manifest(EngineKind.CODEX, MANIFEST_PATH.read_bytes())
        converged = SemanticSnapshot.from_value({"otel": {"environment": "personal"}})
        live = SemanticSnapshot.from_value({"otel": {"environment": "hand-edited"}})

        literal = plan_reconciliation(
            base=converged,
            repo=converged,
            live=live,
            manifest=manifest,
        )
        templated = plan_reconciliation(
            base=converged,
            repo=converged,
            live=live,
            manifest=manifest,
            templated_paths=frozenset({path}),
        )

        literal_change = next(change for change in literal.changes if change.path == path)
        templated_change = next(change for change in templated.changes if change.path == path)
        assert literal_change.kind is ChangeKind.CAPTURE_LIVE
        assert literal_change.templated is False
        assert templated_change.kind is ChangeKind.APPLY_REPO
        assert templated_change.templated is True
        assert templated_change.scope is FieldScope.SHARED

    @pytest.mark.parametrize(
        "path",
        [
            ("desktop", "analytics"),
            ("projects", "/Users/example/Projects/machine-local", "trust_level"),
            ("notify",),
        ],
    )
    def test_local_project_paths_are_preserved(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.PRESERVE_LOCAL
        assert changes[path].scope is FieldScope.LOCAL_STATE

    @pytest.mark.parametrize(
        ("path", "expected_kind", "expected_scope"),
        [
            (
                ("marketplaces", "example", "enabled"),
                ChangeKind.PRESERVE_LOCAL,
                FieldScope.RUNTIME,
            ),
            (
                ("mcp_servers", "example", "command"),
                ChangeKind.PRESERVE_LOCAL,
                FieldScope.RUNTIME,
            ),
            (
                ("notice", "model_migrations", "gpt-example-old"),
                ChangeKind.PRESERVE_LOCAL,
                FieldScope.RUNTIME,
            ),
            (("futureVendorSetting", "enabled"), ChangeKind.UNKNOWN, None),
        ],
    )
    def test_runtime_and_unknown_fields_remain_non_portable(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
        expected_kind: ChangeKind,
        expected_scope: FieldScope | None,
    ) -> None:
        assert changes[path].kind is expected_kind
        assert changes[path].scope is expected_scope
