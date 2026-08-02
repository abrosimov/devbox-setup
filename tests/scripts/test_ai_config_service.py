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
from ai_config.resolution import OperationMode, ResolutionError
from ai_config.service import (
    DecisionsRequiredError,
    OperationResult,
    UnknownFieldsError,
    operate_engine,
)
from ai_config.state import (
    BaseState,
    digest_manifest,
    load_base_state,
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
LOCAL_STATE_MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [
    {"path": "setting", "scope": "shared"},
    {"path": "machine", "scope": "local-state"}
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
