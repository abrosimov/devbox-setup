from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
import yaml
from ai_config import service as service_module
from ai_config.adapters import EngineKind, EnginePaths, resolve_engine_paths
from ai_config.bindings import (
    BindingProviders,
    BindingResolutionError,
    CommandResult,
)
from ai_config.core import BindingProvider, ChangeKind, FieldBinding, ManifestDefinitionError
from ai_config.decisions import DecisionSet, DecisionSource, FieldDecision
from ai_config.document import snapshot_mapping
from ai_config.model import SemanticSnapshot
from ai_config.resolution import OperationMode, ResolutionError
from ai_config.service import (
    BootstrapAction,
    BootstrapError,
    BootstrapResult,
    DecisionsRequiredError,
    OperationResult,
    UnknownFieldsError,
    bootstrap_engine_from_live,
    inspect_engine,
    operate_engine,
)
from ai_config.state import (
    BaseState,
    digest_manifest,
    digest_manifest_source,
    load_base_state,
    parse_base_state,
    render_base_state,
    resolve_state_paths,
)
from ai_config.transaction import (
    ConcurrentModificationError,
    FileExpectation,
    FileWrite,
    MultiFileTransactionResult,
)
from ai_config_fixtures import copy_template_variables

if TYPE_CHECKING:
    from collections.abc import Mapping

SHARED_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "setting", "scope": "shared"}
  ]
}
"""
ORDERED_SHARED_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "zebra", "scope": "shared"},
    {"path": "setting", "scope": "shared"},
    {"path": "alpha", "scope": "shared"}
  ]
}
"""
LOCAL_STATE_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "setting", "scope": "shared"},
    {"path": "machine", "scope": "local-state"}
  ]
}
"""
BOOTSTRAP_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "shared", "scope": "shared"},
    {"path": "repoOnly", "scope": "shared"},
    {"path": "liveOnly", "scope": "shared"},
    {"path": "machine", "scope": "local-state"},
    {"path": "runtime", "scope": "runtime"}
  ]
}
"""
CODEX_PROFILE_MANIFEST = """{
  "schema_version": 1,
  "engine": "codex",
  "fields": [
    {"path": "model", "scope": "shared"},
    {"path": "otel", "scope": "shared"}
  ]
}
"""
CODEX_HOOK_MANIFEST = """{
  "schema_version": 1,
  "engine": "codex",
  "fields": [
    {"path": "hooks", "scope": "shared"}
  ]
}
"""
BINDINGS_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "renderedValue", "scope": "shared"},
    {
      "path": "secretValue",
      "scope": "environment",
      "binding": "keychain:ai-config/account",
      "secret": true
    }
  ]
}
"""
BINDINGS_REPOSITORY = (
    '{"renderedValue": "{{ devbox_rendered_value }}",'
    ' "secretValue": "${AI_CONFIG_KEYCHAIN_VALUE}"}\n'
)
MARKETPLACE_SUFFIX = ".claude/marketplaces/langfuse-observability"
HOME_BINDING_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "model", "scope": "shared"},
    {
      "path": "marketplace.source",
      "scope": "environment",
      "binding": "home:.claude/marketplaces/langfuse-observability"
    }
  ]
}
"""
HOME_BINDING_REPOSITORY = (
    '{"marketplace": {"source": "@home@/.claude/marketplaces/langfuse-observability"},'
    ' "model": "repository"}\n'
)
NO_DECISIONS = DecisionSet(decisions=())


@dataclass(frozen=True, slots=True)
class ServiceTree:
    engine: EngineKind
    repo_root: Path
    home: Path
    state_root: Path
    paths: EnginePaths


@dataclass(slots=True)
class RecordingCommandRunner:
    result: CommandResult
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def __call__(self, arguments: tuple[str, ...], /) -> CommandResult:
        self.calls.append(arguments)
        return self.result


def create_tree(
    tmp_path: Path,
    engine: EngineKind,
    *,
    repository_source: str,
    manifest_source: str,
    live_source: str | None = None,
    variables: Mapping[str, object] | None = None,
    profile: str = "work",
) -> ServiceTree:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    state_root = tmp_path / "state"
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    for path in (paths.repository, paths.manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    paths.repository.write_text(repository_source, encoding="utf-8")
    paths.manifest.write_text(manifest_source, encoding="utf-8")
    if variables is not None:
        overlay = repo_root / "profiles" / f"{profile}.yml"
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_text(yaml.safe_dump(dict(variables)), encoding="utf-8")
    if live_source is not None:
        paths.live.parent.mkdir(parents=True, exist_ok=True)
        paths.live.write_text(live_source, encoding="utf-8")
    return ServiceTree(
        engine=engine,
        repo_root=repo_root,
        home=home,
        state_root=state_root,
        paths=paths,
    )


def operate(
    tree: ServiceTree,
    *,
    mode: OperationMode = OperationMode.APPLY,
    decisions: DecisionSet = NO_DECISIONS,
    check: bool = False,
    profile: str = "work",
    providers: BindingProviders | None = None,
) -> OperationResult:
    return operate_engine(
        tree.engine,
        repo_root=tree.repo_root,
        home=tree.home,
        state_root=tree.state_root,
        profile=profile,
        mode=mode,
        decisions=decisions,
        check=check,
        providers=providers,
    )


def bootstrap(
    tree: ServiceTree,
    *,
    write: bool,
    preview_token: str | None = None,
    providers: BindingProviders | None = None,
) -> BootstrapResult:
    return bootstrap_engine_from_live(
        tree.engine,
        repo_root=tree.repo_root,
        home=tree.home,
        state_root=tree.state_root,
        profile="work",
        write=write,
        preview_token=preview_token,
        providers=providers,
    )


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast("dict[str, object]", loaded)


def read_toml(path: Path) -> dict[str, object]:
    loaded: object = tomllib.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return cast("dict[str, object]", loaded)


def load_tree_base(
    tree: ServiceTree,
    engine: EngineKind,
    *,
    profile: str = "work",
) -> BaseState:
    paths = resolve_state_paths(
        engine,
        profile=profile,
        home=tree.home,
        state_root=tree.state_root,
    )
    state = load_base_state(
        paths.base,
        engine=engine,
        profile=profile,
        manifest_digest=digest_manifest(tree.paths.manifest),
    )
    assert state is not None
    return state


def secret_fingerprint(value: str) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


class TestApplyService:
    def test_missing_live_creates_live_and_base(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "repository"}\n',
            manifest_source=SHARED_MANIFEST,
        )

        result = operate(tree)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert result.changed is True
        assert result.state_initialised is True
        assert result.applied == 1
        assert set(result.written_paths) == {
            tree.paths.live,
            resolve_state_paths(
                EngineKind.CLAUDE,
                profile="work",
                home=tree.home,
                state_root=tree.state_root,
            ).base,
        }
        assert read_json(tree.paths.live) == {"setting": "repository"}
        assert snapshot_mapping(state.snapshot) == {"setting": "repository"}

    def test_second_apply_is_idempotent(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "repository"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        first = operate(tree)
        live_before = tree.paths.live.read_bytes()
        base_path = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=tree.home,
            state_root=tree.state_root,
        ).base
        base_before = base_path.read_bytes()

        second = operate(tree)

        assert first.changed is True
        assert second.changed is False
        assert second.state_initialised is False
        assert second.written_paths == ()
        assert tree.paths.live.read_bytes() == live_before
        assert base_path.read_bytes() == base_before

    def test_mode_only_update_preserves_json_source_bytes(self, tmp_path: Path) -> None:
        live_source = '{ "setting": "same" }\n'
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "same"}\n',
            manifest_source=SHARED_MANIFEST,
            live_source=live_source,
        )

        operate(tree)

        assert tree.paths.live.read_text(encoding="utf-8") == live_source

    def test_repository_only_change_updates_live_and_base(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "old"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        operate(tree)
        write_json(tree.paths.repository, {"setting": "repository-new"})

        result = operate(tree)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert result.applied == 1
        assert result.captured == 0
        assert read_json(tree.paths.live) == {"setting": "repository-new"}
        assert snapshot_mapping(state.snapshot) == {"setting": "repository-new"}

    def test_check_reports_change_without_writing(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "repository"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        repository_before = tree.paths.repository.read_bytes()

        result = operate(tree, check=True)

        assert result.changed is True
        assert result.check_mode is True
        assert result.written_paths == ()
        assert tree.paths.repository.read_bytes() == repository_before
        assert not tree.paths.live.exists()
        assert not tree.state_root.exists()


class TestLiveBootstrapService:
    @pytest.fixture
    def tree(self, tmp_path: Path) -> ServiceTree:
        return create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=(
                '{"shared":"repo","repoOnly":true,'
                '"machine":{"path":"repo"},"runtime":{"value":"repo"}}\n'
            ),
            manifest_source=BOOTSTRAP_MANIFEST,
            live_source=(
                '{"shared":"live","liveOnly":true,'
                '"machine":{"path":"live"},"runtime":{"value":"live"}}\n'
            ),
        )

    def test_preview_classifies_without_writing(self, tree: ServiceTree) -> None:
        repository_before = tree.paths.repository.read_bytes()
        live_before = tree.paths.live.read_bytes()

        result = bootstrap(tree, write=False)

        actions = {change.path: change.action for change in result.changes}
        assert actions == {
            ("liveOnly",): BootstrapAction.CAPTURE,
            ("machine", "path"): BootstrapAction.PRESERVE_LOCAL,
            ("repoOnly",): BootstrapAction.KEEP_REPO,
            ("runtime", "value"): BootstrapAction.IGNORE_RUNTIME,
            ("shared",): BootstrapAction.CAPTURE,
        }
        assert result.operation.check_mode is True
        assert result.operation.written_paths == ()
        assert tree.paths.repository.read_bytes() == repository_before
        assert tree.paths.live.read_bytes() == live_before
        assert not tree.state_root.exists()

    def test_write_captures_live_and_retains_repo_only_values(
        self,
        tree: ServiceTree,
    ) -> None:
        preview = bootstrap(tree, write=False)

        result = bootstrap(tree, write=True, preview_token=preview.preview_token)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert result.operation.check_mode is False
        assert result.operation.captured == 2
        assert result.operation.applied == 0
        assert read_json(tree.paths.repository) == {
            "shared": "live",
            "repoOnly": True,
            "liveOnly": True,
            "machine": {"path": "repo"},
            "runtime": {"value": "repo"},
        }
        assert read_json(tree.paths.live) == {
            "shared": "live",
            "liveOnly": True,
            "machine": {"path": "live"},
            "runtime": {"value": "live"},
        }
        assert snapshot_mapping(state.snapshot) == {
            "shared": "live",
            "liveOnly": True,
        }
        follow_up = operate(tree, check=True)
        assert follow_up.applied == 1
        assert follow_up.captured == 0

    def test_refuses_to_replace_an_existing_base(self, tree: ServiceTree) -> None:
        preview = bootstrap(tree, write=False)
        bootstrap(tree, write=True, preview_token=preview.preview_token)

        with pytest.raises(BootstrapError):
            bootstrap(tree, write=False)

    def test_write_requires_a_reviewed_preview_token(self, tree: ServiceTree) -> None:
        repository_before = tree.paths.repository.read_bytes()

        with pytest.raises(BootstrapError):
            bootstrap(tree, write=True)

        assert tree.paths.repository.read_bytes() == repository_before
        assert not tree.state_root.exists()

    @pytest.mark.parametrize("changed_input", ["repository", "live", "manifest", "base"])
    def test_write_rejects_file_input_changed_after_preview(
        self,
        tree: ServiceTree,
        changed_input: str,
    ) -> None:
        preview = bootstrap(tree, write=False)
        if changed_input == "base":
            base_path = resolve_state_paths(
                EngineKind.CLAUDE,
                profile="work",
                home=tree.home,
                state_root=tree.state_root,
            ).base
            base_path.parent.mkdir(parents=True)
            base_path.write_bytes(
                render_base_state(
                    BaseState(
                        engine=EngineKind.CLAUDE,
                        profile="work",
                        manifest_digest=digest_manifest(tree.paths.manifest),
                        snapshot=SemanticSnapshot.from_value({"shared": "live", "liveOnly": True}),
                    )
                )
            )
        else:
            path = {
                "repository": tree.paths.repository,
                "live": tree.paths.live,
                "manifest": tree.paths.manifest,
            }[changed_input]
            path.write_bytes(path.read_bytes() + b"\n")

        with pytest.raises(BootstrapError):
            bootstrap(tree, write=True, preview_token=preview.preview_token)

    def test_write_rejects_binding_changed_after_preview(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=BINDINGS_REPOSITORY,
            manifest_source=BINDINGS_MANIFEST,
            live_source='{"renderedValue":"live","secretValue":"live-secret"}\n',
            variables={"devbox_rendered_value": "rendered"},
        )
        preview_providers = BindingProviders(
            home=tree.home,
            command_runner=RecordingCommandRunner(
                CommandResult(returncode=0, stdout="preview-secret\n"),
            ),
        )
        changed_providers = BindingProviders(
            home=tree.home,
            command_runner=RecordingCommandRunner(
                CommandResult(returncode=0, stdout="changed-secret\n"),
            ),
        )
        preview = bootstrap(tree, write=False, providers=preview_providers)

        with pytest.raises(BootstrapError):
            bootstrap(
                tree,
                write=True,
                preview_token=preview.preview_token,
                providers=changed_providers,
            )

        assert not tree.state_root.exists()

    def test_requires_an_existing_live_configuration(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"shared":"repo"}\n',
            manifest_source=BOOTSTRAP_MANIFEST,
        )

        with pytest.raises(BootstrapError):
            bootstrap(tree, write=False)


class TestDecisionService:
    def test_live_only_change_requires_decision_then_captures_live(
        self,
        tmp_path: Path,
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "old"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        operate(tree)
        write_json(tree.paths.live, {"setting": "live-new"})
        repository_before = tree.paths.repository.read_bytes()
        base_path = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=tree.home,
            state_root=tree.state_root,
        ).base
        base_before = base_path.read_bytes()

        with pytest.raises(DecisionsRequiredError) as caught:
            operate(tree)

        assert caught.value.paths == (("setting",),)
        assert tree.paths.repository.read_bytes() == repository_before
        assert base_path.read_bytes() == base_before

        decisions = DecisionSet(
            decisions=(FieldDecision(path=("setting",), source=DecisionSource.LIVE),),
        )
        result = operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert result.applied == 0
        assert result.captured == 1
        assert read_json(tree.paths.repository) == {"setting": "live-new"}
        assert read_json(tree.paths.live) == {"setting": "live-new"}
        assert snapshot_mapping(state.snapshot) == {"setting": "live-new"}

    def test_capture_live_preserves_repository_json_order(self, tmp_path: Path) -> None:
        repository_source = """{
  "zebra": true,
  "setting": "old",
  "alpha": true
}
"""
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=repository_source,
            manifest_source=ORDERED_SHARED_MANIFEST,
        )
        operate(tree)
        live_source = repository_source.replace('"old"', '"live"')
        tree.paths.live.write_text(live_source, encoding="utf-8")
        decisions = DecisionSet(
            decisions=(FieldDecision(path=("setting",), source=DecisionSource.LIVE),),
        )

        operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)

        assert tree.paths.repository.read_text(encoding="utf-8") == live_source

    @pytest.mark.parametrize(
        ("source", "expected", "applied", "captured"),
        [
            (DecisionSource.REPO, "repository-new", 1, 0),
            (DecisionSource.LIVE, "live-new", 0, 1),
        ],
    )
    def test_concurrent_change_uses_explicit_decision(
        self,
        tmp_path: Path,
        source: DecisionSource,
        expected: str,
        applied: int,
        captured: int,
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "old"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        operate(tree)
        write_json(tree.paths.repository, {"setting": "repository-new"})
        write_json(tree.paths.live, {"setting": "live-new"})
        decisions = DecisionSet(
            decisions=(FieldDecision(path=("setting",), source=source),),
        )

        result = operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)

        assert result.plan.count(ChangeKind.CONFLICT) == 1
        assert result.applied == applied
        assert result.captured == captured
        assert read_json(tree.paths.repository) == {"setting": expected}
        assert read_json(tree.paths.live) == {"setting": expected}

    def test_decision_for_automatic_repository_change_is_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "old"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        operate(tree)
        write_json(tree.paths.repository, {"setting": "repository-new"})
        decision = DecisionSet(
            decisions=(FieldDecision(path=("setting",), source=DecisionSource.LIVE),),
        )

        with pytest.raises(ResolutionError):
            operate(tree, mode=OperationMode.RECONCILE, decisions=decision)

        assert read_json(tree.paths.live) == {"setting": "old"}


class TestWriteSafety:
    def test_unknown_field_blocks_base_initialisation(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "same", "vendor": true}\n',
            manifest_source=SHARED_MANIFEST,
            live_source='{"setting": "same", "vendor": true}\n',
        )

        with pytest.raises(UnknownFieldsError) as caught:
            operate(tree)

        assert caught.value.paths == (("vendor",),)
        assert not tree.state_root.exists()

    def test_unknown_field_blocks_configuration_write(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "old"}\n',
            manifest_source=SHARED_MANIFEST,
        )
        operate(tree)
        write_json(tree.paths.repository, {"setting": "repository-new"})
        write_json(
            tree.paths.live,
            {"setting": "old", "unknownVendorField": "preserve-me"},
        )
        base_path = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=tree.home,
            state_root=tree.state_root,
        ).base
        base_before = base_path.read_bytes()

        with pytest.raises(UnknownFieldsError) as caught:
            operate(tree)

        assert caught.value.paths == (("unknownVendorField",),)
        assert read_json(tree.paths.repository) == {"setting": "repository-new"}
        assert read_json(tree.paths.live) == {
            "setting": "old",
            "unknownVendorField": "preserve-me",
        }
        assert base_path.read_bytes() == base_before

    def test_local_state_is_preserved_while_shared_fields_apply(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=('{"setting": "old", "machine": {"path": "repository-local"}}\n'),
            manifest_source=LOCAL_STATE_MANIFEST,
            live_source='{"setting": "old", "machine": {"path": "live-local"}}\n',
        )
        operate(tree)
        write_json(
            tree.paths.repository,
            {"setting": "repository-new", "machine": {"path": "repository-local"}},
        )

        result = operate(tree)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert result.preserved == 1
        assert read_json(tree.paths.live) == {
            "setting": "repository-new",
            "machine": {"path": "live-local"},
        }
        assert snapshot_mapping(state.snapshot) == {"setting": "repository-new"}

    def test_codex_hook_runtime_state_is_preserved_while_definitions_apply(
        self,
        tmp_path: Path,
    ) -> None:
        runtime_key = "/Users/example/.codex/config.toml:session_end:0:0"
        tree = create_tree(
            tmp_path,
            EngineKind.CODEX,
            repository_source='[hooks]\ndefinition = "old"\n',
            manifest_source=CODEX_HOOK_MANIFEST,
            live_source=(
                '[hooks]\ndefinition = "old"\n\n'
                f'[hooks.state."{runtime_key}"]\n'
                'enabled = true\ntrusted_hash = "sha256:runtime"\n'
            ),
        )
        operate(tree)
        tree.paths.repository.write_text(
            '[hooks]\ndefinition = "repository-new"\n',
            encoding="utf-8",
        )

        result = operate(tree)
        live = tomllib.loads(tree.paths.live.read_text(encoding="utf-8"))
        state = load_tree_base(tree, EngineKind.CODEX)

        assert result.applied == 1
        assert result.captured == 0
        assert result.preserved == 2
        assert live == {
            "hooks": {
                "definition": "repository-new",
                "state": {
                    runtime_key: {
                        "enabled": True,
                        "trusted_hash": "sha256:runtime",
                    }
                },
            }
        }
        assert snapshot_mapping(state.snapshot) == {"hooks": {"definition": "repository-new"}}

    @pytest.mark.parametrize(
        ("live_source", "unknown_path"),
        [
            (
                '[hooks]\ndefinition = "old"\n\n[hooks.state."dynamic"]\nunexpected = true\n',
                ("hooks", "state", "dynamic", "unexpected"),
            ),
            (
                '[hooks]\ndefinition = "old"\nstate = "malformed"\n',
                ("hooks", "state"),
            ),
        ],
    )
    def test_codex_unknown_hook_state_blocks_writes(
        self,
        tmp_path: Path,
        live_source: str,
        unknown_path: tuple[str, ...],
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CODEX,
            repository_source='[hooks]\ndefinition = "old"\n',
            manifest_source=CODEX_HOOK_MANIFEST,
            live_source=live_source,
        )

        with pytest.raises(UnknownFieldsError) as caught:
            operate(tree)

        assert caught.value.paths == (unknown_path,)
        assert not tree.state_root.exists()

    def test_source_change_after_planning_aborts_base_initialisation(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source='{"setting": "same"}\n',
            manifest_source=SHARED_MANIFEST,
            live_source='{"setting": "same"}\n',
        )
        real_write = service_module.write_validated_files

        def race_before_transaction(
            *,
            engine: str,
            state_directory: Path,
            writes: tuple[FileWrite, ...],
            expectations: tuple[FileExpectation, ...],
        ) -> MultiFileTransactionResult:
            write_json(tree.paths.live, {"setting": "external-change"})
            return real_write(
                engine=engine,
                state_directory=state_directory,
                writes=writes,
                expectations=expectations,
            )

        monkeypatch.setattr(service_module, "write_validated_files", race_before_transaction)

        with pytest.raises(ConcurrentModificationError):
            operate(tree)

        assert read_json(tree.paths.live) == {"setting": "external-change"}
        assert not tree.state_root.joinpath("claude", "work", "base.json").exists()


class TestBindingsAndRedaction:
    def test_codex_profile_template_preserves_declaration_and_materialises_live(
        self,
        tmp_path: Path,
    ) -> None:
        repository_source = (
            'model = "gpt-test"\n\n[otel]\nenvironment = "{{ devbox_active_profile }}"\n'
        )
        tree = create_tree(
            tmp_path,
            EngineKind.CODEX,
            repository_source=repository_source,
            manifest_source=CODEX_PROFILE_MANIFEST,
            variables={"devbox_active_profile": "work"},
        )
        runner = RecordingCommandRunner(CommandResult(returncode=0, stdout="unused"))
        providers = BindingProviders(home=tree.home, command_runner=runner)

        operate(tree, profile="work", providers=providers)
        state = load_tree_base(tree, EngineKind.CODEX)
        live = read_toml(tree.paths.live)
        otel = live["otel"]

        assert tree.paths.repository.read_text(encoding="utf-8") == repository_source
        assert isinstance(otel, dict)
        assert otel["environment"] == "work"
        assert snapshot_mapping(state.snapshot) == {
            "model": "gpt-test",
            "otel": {"environment": "work"},
        }
        assert runner.calls == []

    def test_rendering_and_keychain_binding_keep_both_declarations_and_hide_the_secret(
        self,
        tmp_path: Path,
    ) -> None:
        sensitive_value = "keychain-sensitive-value"
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=BINDINGS_REPOSITORY,
            manifest_source=BINDINGS_MANIFEST,
            variables={"devbox_rendered_value": "rendered-value"},
        )
        runner = RecordingCommandRunner(
            CommandResult(returncode=0, stdout=f"{sensitive_value}\n"),
        )
        providers = BindingProviders(home=tree.home, command_runner=runner)

        result = operate(tree, providers=providers)
        state = load_tree_base(tree, EngineKind.CLAUDE)
        base_bytes = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=tree.home,
            state_root=tree.state_root,
        ).base.read_bytes()

        assert tree.paths.repository.read_text(encoding="utf-8") == BINDINGS_REPOSITORY
        assert read_json(tree.paths.live) == {
            "renderedValue": "rendered-value",
            "secretValue": sensitive_value,
        }
        assert snapshot_mapping(state.snapshot) == {
            "renderedValue": "rendered-value",
            "secretValue": secret_fingerprint(sensitive_value),
        }
        assert sensitive_value.encode() not in base_bytes
        assert sensitive_value not in repr(result.plan)
        assert "sha256:" in repr(result.plan)
        expected_arguments = (
            "security",
            "find-generic-password",
            "-s",
            "ai-config",
            "-a",
            "account",
            "-w",
        )
        assert runner.calls
        assert all(arguments == expected_arguments for arguments in runner.calls)

    def test_binding_failure_is_redacted_and_does_not_write(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=BINDINGS_REPOSITORY,
            manifest_source=BINDINGS_MANIFEST,
            variables={"devbox_rendered_value": "rendered-value"},
        )
        command_output = "provider-sensitive-output"
        runner = RecordingCommandRunner(
            CommandResult(returncode=1, stdout=command_output),
        )
        providers = BindingProviders(home=tree.home, command_runner=runner)

        with pytest.raises(BindingResolutionError) as caught:
            operate(tree, providers=providers)

        assert command_output not in str(caught.value)
        assert tree.paths.repository.read_text(encoding="utf-8") == BINDINGS_REPOSITORY
        assert not tree.paths.live.exists()
        assert not tree.state_root.exists()
        assert len(runner.calls) == 1


class TestHomeBindings:
    def test_system_providers_bind_the_target_home_not_the_process_environment(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path / "process-home"))
        target_home = tmp_path / "target-home"
        binding = FieldBinding(provider=BindingProvider.HOME, key=MARKETPLACE_SUFFIX)

        resolved = BindingProviders(home=target_home).resolve(binding)

        assert resolved == f"{target_home}/.claude/marketplaces/langfuse-observability"
        assert Path(resolved).is_absolute()
        assert "process-home" not in resolved

    def test_live_path_is_materialised_while_the_repository_declaration_is_preserved(
        self,
        tmp_path: Path,
    ) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=HOME_BINDING_REPOSITORY,
            manifest_source=HOME_BINDING_MANIFEST,
            live_source=(
                '{"marketplace": {"source": "/somebody/elses/home"}, "model": "repository"}\n'
            ),
        )
        expected = f"{tree.home}/{MARKETPLACE_SUFFIX}"

        operate(tree)
        state = load_tree_base(tree, EngineKind.CLAUDE)

        assert tree.paths.repository.read_text(encoding="utf-8") == HOME_BINDING_REPOSITORY
        assert read_json(tree.paths.live) == {
            "marketplace": {"source": expected},
            "model": "repository",
        }
        assert snapshot_mapping(state.snapshot) == {
            "marketplace": {"source": expected},
            "model": "repository",
        }

    def test_bound_field_cannot_be_captured_from_live(self, tmp_path: Path) -> None:
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=HOME_BINDING_REPOSITORY,
            manifest_source=HOME_BINDING_MANIFEST,
        )
        operate(tree)
        live_edit: dict[str, object] = {
            "marketplace": {"source": "/locally/edited"},
            "model": "repository",
        }
        write_json(tree.paths.live, live_edit)
        decisions = DecisionSet(
            decisions=(FieldDecision(path=("marketplace", "source"), source=DecisionSource.LIVE),),
        )

        with pytest.raises(ResolutionError):
            operate(tree, mode=OperationMode.RECONCILE, decisions=decisions)

        assert tree.paths.repository.read_text(encoding="utf-8") == HOME_BINDING_REPOSITORY
        assert read_json(tree.paths.live) == live_edit


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "roles/devbox/files/dot_codex/config.ai-config.json"
OLD_MANIFEST = Path(__file__).parent / "fixtures/ai_config/codex/pre-preference-manifest.json"
REASONING_MANIFEST = OLD_MANIFEST.with_name("reasoning-preference-manifest.json")


class TestPreferenceOperations:
    @pytest.mark.parametrize("live_model", [None, "gpt-6-astra"])
    def test_model_bootstrap_preserves_source_and_defers_missing_default(self, tree, live_model):
        tree.paths.repository.write_text('model = "gpt-5.6-sol"\n')
        tree.paths.live.parent.mkdir(parents=True)
        tree.paths.live.write_text(f'model = "{live_model}"\n' if live_model else "")
        source_before = tree.paths.repository.read_bytes()
        live_before = tree.paths.live.read_bytes()
        preview = bootstrap(tree, write=False)
        choice = next(change for change in preview.changes if change.path == ("model",))
        assert choice.action is (
            BootstrapAction.PRESERVE_LOCAL if live_model else BootstrapAction.KEEP_REPO
        )
        bootstrap(tree, write=True, preview_token=preview.preview_token)
        assert tree.paths.repository.read_bytes() == source_before
        assert tree.paths.live.read_bytes() == live_before
        operate(tree)
        assert tomllib.loads(tree.paths.live.read_text())["model"] == (live_model or "gpt-5.6-sol")

    @pytest.mark.parametrize("model", ["gpt-5.6-sol", "gpt-6-astra"])
    def test_local_model_survives_repeated_apply_and_reconcile(self, tree, model):
        tree.paths.repository.write_text('model = "gpt-5.6-sol"\n')
        tree.paths.live.parent.mkdir(parents=True)
        tree.paths.live.write_text(f'model = "{model}"\n')
        original = tree.paths.repository.read_bytes()
        for mode in (OperationMode.APPLY, OperationMode.RECONCILE, OperationMode.APPLY):
            result = operate(tree, mode=mode)
            assert result.captured == 0
            assert tomllib.loads(tree.paths.live.read_text())["model"] == model
            assert tree.paths.repository.read_bytes() == original
        assert not operate(tree).changed

    def test_fresh_model_uses_actual_repository_sol_default(self, tree):
        source = (MANIFEST.parent / "config.toml.j2").read_bytes()
        tree.paths.repository.write_bytes(source)
        copy_template_variables(tree.repo_root)
        operate(tree)
        assert tomllib.loads(tree.paths.live.read_text())["model"] == "gpt-5.6-sol"
        assert tree.paths.repository.read_bytes() == source

    @pytest.mark.parametrize("previous_manifest", [OLD_MANIFEST, REASONING_MANIFEST])
    def test_migration_only_persists_once(self, tree, previous_manifest):
        operate(tree)
        paths = resolve_state_paths(
            EngineKind.CODEX, profile="work", home=tree.home, state_root=tree.state_root
        )
        state = json.loads(paths.base.read_bytes())
        state["manifest_digest"] = digest_manifest_source(previous_manifest.read_bytes())
        state["snapshot"]["model"] = "gpt-6-astra"
        if previous_manifest == OLD_MANIFEST:
            state["snapshot"]["model_reasoning_effort"] = "medium"
        paths.base.write_text(json.dumps(state))
        live_before = tree.paths.live.read_bytes()
        repo_before = tree.paths.repository.read_bytes()
        assert operate(tree).written_paths == (paths.base,)
        assert json.loads(paths.base.read_bytes())["manifest_digest"] == digest_manifest(
            tree.paths.manifest
        )
        assert tree.paths.live.read_bytes() == live_before
        assert tree.paths.repository.read_bytes() == repo_before
        assert not operate(tree).changed

    @pytest.fixture
    def tree(self, tmp_path):
        return create_tree(
            tmp_path,
            EngineKind.CODEX,
            repository_source='service_tier = "old"\nmodel_reasoning_effort = "medium"\n',
            manifest_source=MANIFEST.read_text(),
        )

    def test_first_install_default_and_repeated_apply(self, tree):
        original = tree.paths.repository.read_bytes()
        operate(tree)
        assert tomllib.loads(tree.paths.live.read_text())["model_reasoning_effort"] == "medium"
        assert not operate(tree).changed
        assert tree.paths.repository.read_bytes() == original

    @pytest.mark.parametrize("previous_manifest", [None, OLD_MANIFEST, REASONING_MANIFEST])
    def test_preserves_choice_applies_other_update_and_excludes_baseline(
        self, tree, previous_manifest
    ):
        operate(tree)
        paths = resolve_state_paths(
            EngineKind.CODEX, profile="work", home=tree.home, state_root=tree.state_root
        )
        if previous_manifest is not None:
            paths.base.write_bytes(
                render_base_state(
                    BaseState(
                        engine=EngineKind.CODEX,
                        profile="work",
                        manifest_digest=digest_manifest_source(previous_manifest.read_bytes()),
                        snapshot=SemanticSnapshot.from_value(
                            {
                                "service_tier": "old",
                                "model": "gpt-6-astra",
                                "model_reasoning_effort": "medium",
                            }
                        ),
                    )
                )
            )
        tree.paths.live.write_text(
            'service_tier = "old"\nmodel = "gpt-5.6-sol"\nmodel_reasoning_effort = "max"\n'
        )
        tree.paths.repository.write_text(
            'service_tier = "new"\nmodel = "gpt-6-astra"\nmodel_reasoning_effort = "low"\n'
        )
        original = tree.paths.repository.read_bytes()
        base_before = paths.base.read_bytes()
        live_before = tree.paths.live.read_bytes()
        assert operate(tree, check=True).changed
        assert paths.base.read_bytes() == base_before
        assert tree.paths.live.read_bytes() == live_before
        result = operate(tree)
        assert result.captured == 0
        live = tomllib.loads(tree.paths.live.read_text())
        assert live["service_tier"] == "new"
        assert live["model"] == "gpt-5.6-sol"
        assert live["model_reasoning_effort"] == "max"
        assert "model" not in json.loads(paths.base.read_text())["snapshot"]
        assert "model_reasoning_effort" not in json.loads(paths.base.read_text())["snapshot"]
        assert tree.paths.repository.read_bytes() == original
        assert not operate(tree).changed

    @pytest.mark.parametrize("baseline", ["current", "previous", "reasoning", "unknown"])
    def test_other_conflict_or_unrecognised_digest_blocks_without_writes(self, tree, baseline):
        operate(tree)
        paths = resolve_state_paths(
            EngineKind.CODEX, profile="work", home=tree.home, state_root=tree.state_root
        )
        if baseline != "current":
            state = json.loads(paths.base.read_text())
            state["manifest_digest"] = (
                digest_manifest_source(OLD_MANIFEST.read_bytes())
                if baseline == "previous"
                else digest_manifest_source(REASONING_MANIFEST.read_bytes())
                if baseline == "reasoning"
                else "unknown"
            )
            paths.base.write_text(json.dumps(state))
        tree.paths.live.write_text('service_tier = "local"\nmodel_reasoning_effort = "high"\n')
        tree.paths.repository.write_text(
            'service_tier = "new"\nmodel_reasoning_effort = "medium"\n'
        )
        before = [
            path.read_bytes() for path in (paths.base, tree.paths.live, tree.paths.repository)
        ]
        with pytest.raises(DecisionsRequiredError):
            operate(tree)
        assert [
            path.read_bytes() for path in (paths.base, tree.paths.live, tree.paths.repository)
        ] == before

    @pytest.mark.parametrize("value", ["true", "42", "[]", "{}", '""', '{nested = "high"}'])
    @pytest.mark.parametrize("source", ["live", "repository"])
    def test_invalid_preference_type_rejected_before_writes(self, tree, value, source):
        tree.paths.live.parent.mkdir(parents=True)
        target = tree.paths.live if source == "live" else tree.paths.repository
        target.write_text(f'service_tier = "old"\nmodel_reasoning_effort = {value}\n')
        before = target.read_bytes()
        with pytest.raises(ManifestDefinitionError):
            operate(tree)
        assert target.read_bytes() == before

    def test_preference_object_cannot_hide_under_local_child_rule(self, tree):
        manifest = json.loads(tree.paths.manifest.read_bytes())
        manifest["fields"].append({"path": "model_reasoning_effort.nested", "scope": "local-state"})
        tree.paths.manifest.write_text(json.dumps(manifest))
        tree.paths.live.parent.mkdir(parents=True)
        tree.paths.live.write_text('model_reasoning_effort = {nested = "high"}\n')
        with pytest.raises(ManifestDefinitionError):
            operate(tree)

    def test_previous_digest_does_not_migrate_to_unrecognised_target(self, tree):
        operate(tree)
        paths = resolve_state_paths(
            EngineKind.CODEX, profile="work", home=tree.home, state_root=tree.state_root
        )
        state = json.loads(paths.base.read_bytes())
        state["manifest_digest"] = digest_manifest_source(OLD_MANIFEST.read_bytes())
        paths.base.write_text(json.dumps(state))
        tree.paths.manifest.write_bytes(tree.paths.manifest.read_bytes() + b"\n")
        inspection = inspect_engine(
            tree.engine,
            repo_root=tree.repo_root,
            home=tree.home,
            state_root=tree.state_root,
            profile="work",
        )
        assert inspection.base_state is None

    @pytest.mark.parametrize("default_present", [False, True])
    def test_bootstrap_and_reconcile_never_capture_preference(self, tree, default_present):
        if not default_present:
            tree.paths.repository.write_text('service_tier = "old"\n')
        tree.paths.live.parent.mkdir(parents=True)
        tree.paths.live.write_text('service_tier = "old"\nmodel_reasoning_effort = "high"\n')
        original = tree.paths.repository.read_bytes()
        preview = bootstrap(tree, write=False)
        preference = next(
            change for change in preview.changes if change.path == ("model_reasoning_effort",)
        )
        assert preference.action is BootstrapAction.PRESERVE_LOCAL
        bootstrap(tree, write=True, preview_token=preview.preview_token)
        assert tree.paths.repository.read_bytes() == original
        assert operate(tree, mode=OperationMode.RECONCILE).captured == 0
        assert tree.paths.repository.read_bytes() == original
        inspection = inspect_engine(
            tree.engine,
            repo_root=tree.repo_root,
            home=tree.home,
            state_root=tree.state_root,
            profile="work",
        )
        assert inspection.base_state is not None
        assert ("model_reasoning_effort",) not in {
            field.path for field in inspection.base_state.snapshot.semantic_fields()
        }

    def test_absent_preference_remains_absent(self, tree):
        tree.paths.repository.write_text('service_tier = "old"\n')
        operate(tree)
        assert "model_reasoning_effort" not in tomllib.loads(tree.paths.live.read_text())
        assert not operate(tree).changed

    def test_bootstrap_without_live_preference_keeps_default_for_next_apply(self, tree):
        tree.paths.live.parent.mkdir(parents=True)
        tree.paths.live.write_text('service_tier = "old"\n')
        original = tree.paths.repository.read_bytes()
        live_before = tree.paths.live.read_bytes()
        preview = bootstrap(tree, write=False)
        preference = next(
            change for change in preview.changes if change.path == ("model_reasoning_effort",)
        )
        assert preference.action is BootstrapAction.KEEP_REPO
        bootstrap(tree, write=True, preview_token=preview.preview_token)
        assert tree.paths.repository.read_bytes() == original
        assert tree.paths.live.read_bytes() == live_before
        operate(tree)
        assert tomllib.loads(tree.paths.live.read_text())["model_reasoning_effort"] == "medium"

    @pytest.mark.parametrize(
        ("source", "target", "demoted"),
        [
            (OLD_MANIFEST, REASONING_MANIFEST, ("model_reasoning_effort",)),
            (OLD_MANIFEST, MANIFEST, ("model", "model_reasoning_effort")),
            (REASONING_MANIFEST, MANIFEST, ("model",)),
        ],
    )
    def test_recognised_migration_changes_only_preference_scope(self, source, target, demoted):
        old = json.loads(source.read_bytes())
        new = json.loads(target.read_bytes())
        for field_name in demoted:
            rule = next(rule for rule in old["fields"] if rule["path"] == field_name)
            assert rule["scope"] == "shared"
            rule["scope"] = "preference"
        # otel.environment also left the manifest on the way to the current one:
        # the value is a Jinja expression in config.toml.j2 now, and provenance
        # comes from the render. It carries no preference semantics, so the
        # migration still only has preference scope to reconcile.
        removed = [rule for rule in old["fields"] if rule["path"] == "otel.environment"]
        if removed and not any(rule["path"] == "otel.environment" for rule in new["fields"]):
            old["fields"].remove(removed[0])
        assert old == new
        snapshot = {
            "model": "gpt-6-astra",
            "model_reasoning_effort": "high",
            "service_tier": "default",
            "features": {"hooks": True},
        }
        state = BaseState(
            engine=EngineKind.CODEX,
            profile="work",
            manifest_digest=digest_manifest_source(source.read_bytes()),
            snapshot=SemanticSnapshot.from_value(snapshot),
        )
        migrated = parse_base_state(
            render_base_state(state),
            engine=EngineKind.CODEX,
            profile="work",
            manifest_digest=digest_manifest_source(target.read_bytes()),
        )
        assert migrated is not None
        assert snapshot_mapping(migrated.snapshot) == {
            key: value for key, value in snapshot.items() if key not in demoted
        }
