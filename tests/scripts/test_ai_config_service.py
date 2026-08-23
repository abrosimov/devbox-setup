from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, cast

import pytest
from ai_config import service as service_module
from ai_config.adapters import EngineKind, EnginePaths, resolve_engine_paths
from ai_config.bindings import (
    BindingProviders,
    BindingResolutionError,
    CommandResult,
)
from ai_config.core import ChangeKind
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
    operate_engine,
)
from ai_config.state import (
    BaseState,
    digest_manifest,
    load_base_state,
    render_base_state,
    resolve_state_paths,
)
from ai_config.transaction import (
    ConcurrentModificationError,
    FileExpectation,
    FileWrite,
    MultiFileTransactionResult,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    {
      "path": "otel.environment",
      "scope": "environment",
      "binding": "profile:devbox_active_profile"
    }
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
    {
      "path": "envValue",
      "scope": "environment",
      "binding": "env:AI_CONFIG_ENV_VALUE"
    },
    {
      "path": "secretValue",
      "scope": "environment",
      "binding": "keychain:ai-config/account",
      "secret": true
    }
  ]
}
"""
NO_DECISIONS = DecisionSet(decisions=())


class BindingFailure(StrEnum):
    ENVIRONMENT = "environment"
    KEYCHAIN = "keychain"


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
) -> ServiceTree:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    state_root = tmp_path / "state"
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    for path in (paths.repository, paths.manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    paths.repository.write_text(repository_source, encoding="utf-8")
    paths.manifest.write_text(manifest_source, encoding="utf-8")
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
            repository_source=(
                '{"envValue":"${AI_CONFIG_ENV_VALUE}",'
                '"secretValue":"${AI_CONFIG_KEYCHAIN_VALUE}"}\n'
            ),
            manifest_source=BINDINGS_MANIFEST,
            live_source='{"envValue":"live","secretValue":"live-secret"}\n',
        )
        runner = RecordingCommandRunner(CommandResult(returncode=0, stdout="secret\n"))
        preview_providers = BindingProviders(
            profile="work",
            environment={"AI_CONFIG_ENV_VALUE": "preview"},
            command_runner=runner,
        )
        changed_providers = BindingProviders(
            profile="work",
            environment={"AI_CONFIG_ENV_VALUE": "changed"},
            command_runner=runner,
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
    def test_codex_profile_binding_preserves_declaration_and_materialises_live(
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
        )
        runner = RecordingCommandRunner(CommandResult(returncode=0, stdout="unused"))
        providers = BindingProviders(profile="work", environment={}, command_runner=runner)

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

    def test_environment_and_keychain_bindings_use_injected_providers_and_fingerprint_secret(
        self,
        tmp_path: Path,
    ) -> None:
        sensitive_value = "keychain-sensitive-value"
        repository_source = (
            '{"envValue": "${AI_CONFIG_ENV_VALUE}", "secretValue": "${AI_CONFIG_KEYCHAIN_VALUE}"}\n'
        )
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=repository_source,
            manifest_source=BINDINGS_MANIFEST,
        )
        runner = RecordingCommandRunner(
            CommandResult(returncode=0, stdout=f"{sensitive_value}\n"),
        )
        providers = BindingProviders(
            profile="work",
            environment={"AI_CONFIG_ENV_VALUE": "environment-value"},
            command_runner=runner,
        )

        result = operate(tree, providers=providers)
        state = load_tree_base(tree, EngineKind.CLAUDE)
        base_bytes = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=tree.home,
            state_root=tree.state_root,
        ).base.read_bytes()

        assert tree.paths.repository.read_text(encoding="utf-8") == repository_source
        assert read_json(tree.paths.live) == {
            "envValue": "environment-value",
            "secretValue": sensitive_value,
        }
        assert snapshot_mapping(state.snapshot) == {
            "envValue": "environment-value",
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

    @pytest.mark.parametrize(
        "failure",
        [BindingFailure.ENVIRONMENT, BindingFailure.KEYCHAIN],
    )
    def test_binding_failure_is_redacted_and_does_not_write(
        self,
        tmp_path: Path,
        failure: BindingFailure,
    ) -> None:
        repository_source = (
            '{"envValue": "${AI_CONFIG_ENV_VALUE}", "secretValue": "${AI_CONFIG_KEYCHAIN_VALUE}"}\n'
        )
        tree = create_tree(
            tmp_path,
            EngineKind.CLAUDE,
            repository_source=repository_source,
            manifest_source=BINDINGS_MANIFEST,
        )
        command_output = "provider-sensitive-output"
        runner = RecordingCommandRunner(
            CommandResult(
                returncode=1 if failure is BindingFailure.KEYCHAIN else 0,
                stdout=command_output,
            ),
        )
        environment = (
            {}
            if failure is BindingFailure.ENVIRONMENT
            else {"AI_CONFIG_ENV_VALUE": "environment-value"}
        )
        providers = BindingProviders(
            profile="work",
            environment=environment,
            command_runner=runner,
        )

        with pytest.raises(BindingResolutionError) as caught:
            operate(tree, providers=providers)

        assert command_output not in str(caught.value)
        assert tree.paths.repository.read_text(encoding="utf-8") == repository_source
        assert not tree.paths.live.exists()
        assert not tree.state_root.exists()
        if failure is BindingFailure.ENVIRONMENT:
            assert runner.calls == []
        else:
            assert len(runner.calls) == 1
