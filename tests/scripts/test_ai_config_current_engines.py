from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ai_config.adapters import (
    EngineKind,
    engine_adapter,
    load_repository_document,
    parse_engine_manifest,
    resolve_engine_paths,
)
from ai_config.bindings import BindingProviders, CommandResult
from ai_config.core import (
    HOME_BINDING_SENTINEL,
    BindingProvider,
    FieldBinding,
    FieldManifest,
    FieldRule,
    FieldScope,
    home_binding_declaration,
)
from ai_config.decisions import DecisionSet
from ai_config.model import SemanticSnapshot, to_plain_value
from ai_config.resolution import OperationMode
from ai_config.service import inspect_engine, operate_engine
from ai_config.templating import load_template_variables
from ai_config_fixtures import copy_engine_documents

if TYPE_CHECKING:
    from ai_config.model import FieldPath

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_KEY = ".claude/marketplaces/langfuse-observability"
HOME_BOUND_PATH = "syntheticHomeBoundField"


def sentinel_declarations(repository: SemanticSnapshot) -> dict[FieldPath, str]:
    prefix = f"{HOME_BINDING_SENTINEL}/"
    values = {field.path: to_plain_value(field.value) for field in repository.semantic_fields()}
    return {
        path: value
        for path, value in values.items()
        if isinstance(value, str) and value.startswith(prefix)
    }


def home_binding_declarations(manifest: FieldManifest) -> dict[FieldPath, str]:
    return {
        rule.path: home_binding_declaration(rule.binding.key)
        for rule in manifest.rules
        if rule.binding is not None and rule.binding.provider is BindingProvider.HOME
    }


def home_bound_manifest() -> FieldManifest:
    return FieldManifest(
        rules=(
            FieldRule(
                path=("marketplace",),
                scope=FieldScope.ENVIRONMENT,
                binding=FieldBinding(provider=BindingProvider.HOME, key=MARKETPLACE_KEY),
            ),
        )
    )


def engine_declarations(
    engine: EngineKind,
    repo_root: Path,
) -> tuple[dict[FieldPath, str], dict[FieldPath, str]]:
    adapter = engine_adapter(engine)
    manifest = parse_engine_manifest(
        engine,
        (repo_root / adapter.manifest_relative_path).read_bytes(),
    )
    repository = load_repository_document(
        repo_root / adapter.repository_relative_path,
        adapter.configuration_format,
        load_template_variables(repo_root, "personal"),
    )
    return sentinel_declarations(repository.snapshot), home_binding_declarations(manifest)


def seeded_value(account: str) -> str:
    return f"keychain-{account}"


def seeded_keychain(arguments: tuple[str, ...], /) -> CommandResult:
    account = arguments[arguments.index("-a") + 1]
    return CommandResult(returncode=0, stdout=f"{seeded_value(account)}\n")


@dataclass(slots=True)
class EmptyKeychain:
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def __call__(self, arguments: tuple[str, ...], /) -> CommandResult:
        self.calls.append(arguments)
        return CommandResult(returncode=44, stdout="")


def test_personal_claude_settings_carry_the_keychain_langfuse_keys(tmp_path: Path) -> None:
    isolated_repo = tmp_path / "repository"
    isolated_home = tmp_path / "home"
    copy_engine_documents(EngineKind.CLAUDE, isolated_repo)

    operate_engine(
        EngineKind.CLAUDE,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=tmp_path / "state",
        mode=OperationMode.APPLY,
        decisions=DecisionSet(()),
        check=False,
        providers=BindingProviders(home=isolated_home, command_runner=seeded_keychain),
    )
    live = json.loads((isolated_home / ".claude/settings.json").read_text(encoding="utf-8"))
    state_files = [path for path in (tmp_path / "state").rglob("*") if path.is_file()]

    assert state_files
    assert live["env"]["LANGFUSE_PUBLIC_KEY"] == seeded_value("public-key")
    assert live["env"]["LANGFUSE_SECRET_KEY"] == seeded_value("secret-key")
    assert live["env"]["LANGFUSE_HOST"] == "https://langfuse.abrosimov.tech"
    assert live["enabledPlugins"]["langfuse@claude-plugins-official"] is True
    assert all(seeded_value("secret-key").encode() not in path.read_bytes() for path in state_files)


def test_work_claude_settings_apply_without_any_langfuse_keychain_item(tmp_path: Path) -> None:
    isolated_repo = tmp_path / "repository"
    isolated_home = tmp_path / "home"
    copy_engine_documents(EngineKind.CLAUDE, isolated_repo)
    keychain = EmptyKeychain()

    result = operate_engine(
        EngineKind.CLAUDE,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="work",
        state_root=tmp_path / "state",
        mode=OperationMode.APPLY,
        decisions=DecisionSet(()),
        check=False,
        providers=BindingProviders(home=isolated_home, command_runner=keychain),
    )
    live_text = (isolated_home / ".claude/settings.json").read_text(encoding="utf-8")
    live = json.loads(live_text)

    assert result.changed is True
    assert keychain.calls == []
    assert {"LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"}.isdisjoint(live["env"])
    assert "langfuse@claude-plugins-official" not in live["enabledPlugins"]
    assert "langfuse.com" not in live["sandbox"]["network"]["allowedDomains"]
    assert "@omit@" not in live_text


@pytest.mark.parametrize("engine", tuple(EngineKind))
def test_current_repository_documents_apply_and_converge_in_an_isolated_home(
    tmp_path: Path,
    engine: EngineKind,
) -> None:
    isolated_repo = tmp_path / "repository"
    isolated_home = tmp_path / "home"
    state_root = tmp_path / "state"
    copy_engine_documents(engine, isolated_repo)
    providers = BindingProviders(home=isolated_home, command_runner=seeded_keychain)

    first = operate_engine(
        engine,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=state_root,
        mode=OperationMode.APPLY,
        decisions=DecisionSet(()),
        check=False,
        providers=providers,
    )
    second = operate_engine(
        engine,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=state_root,
        mode=OperationMode.APPLY,
        decisions=DecisionSet(()),
        check=False,
        providers=providers,
    )
    inspection = inspect_engine(
        engine,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=state_root,
        providers=providers,
    )
    paths = resolve_engine_paths(engine, repo_root=isolated_repo, home=isolated_home)

    assert first.changed is True
    assert second.changed is False
    assert paths.live.exists()
    assert inspection.base_state is not None
    assert inspection.plan.is_converged() is True


@pytest.mark.parametrize("engine", tuple(EngineKind))
def test_current_repository_home_declarations_match_their_manifest_bindings(
    engine: EngineKind,
) -> None:
    declared, expected = engine_declarations(engine, REPO_ROOT)

    assert declared == expected


def _add_home_bound_field(repo_root: Path, engine: EngineKind, declaration: str) -> None:
    """Give a copied Claude document and manifest one HOME-bound field."""
    adapter = engine_adapter(engine)

    manifest_path = repo_root / adapter.manifest_relative_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["fields"].append(
        {
            "path": HOME_BOUND_PATH,
            "scope": "environment",
            "binding": f"home:{MARKETPLACE_KEY}",
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    document_path = repo_root / adapter.repository_relative_path
    document = json.loads(document_path.read_text(encoding="utf-8"))
    document[HOME_BOUND_PATH] = declaration
    document_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def test_home_declaration_guard_matches_a_synthetic_home_bound_field(tmp_path: Path) -> None:
    """No engine currently binds a field to $HOME, so exercise the guard synthetically.

    The langfuse marketplace path used to be the only HOME-bound field. It went
    away when the hook stopped being a plugin (see bin/vendor/README.md), which
    would otherwise leave this mechanism with no coverage at all.
    """
    engine = EngineKind.CLAUDE
    isolated_repo = tmp_path / "repository"
    copy_engine_documents(engine, isolated_repo)
    _add_home_bound_field(isolated_repo, engine, home_binding_declaration(MARKETPLACE_KEY))

    declared, expected = engine_declarations(engine, isolated_repo)

    assert declared == expected
    assert declared


def test_declaration_guard_trips_on_a_stale_placeholder_in_a_current_document(
    tmp_path: Path,
) -> None:
    engine = EngineKind.CLAUDE
    isolated_repo = tmp_path / "repository"
    copy_engine_documents(engine, isolated_repo)
    _add_home_bound_field(
        isolated_repo,
        engine,
        f"{HOME_BINDING_SENTINEL}/{MARKETPLACE_KEY}-renamed",
    )

    declared, expected = engine_declarations(engine, isolated_repo)

    assert declared != expected


@pytest.mark.parametrize(
    "declared",
    [
        None,
        "@home@/.claude/marketplaces/langfuse-observabilty",
        "@home@",
        "@HOME@/.claude/marketplaces/langfuse-observability",
        "/Users/someone/.claude/marketplaces/langfuse-observability",
    ],
)
def test_declaration_guard_trips_on_a_placeholder_that_does_not_match_its_binding(
    declared: str | None,
) -> None:
    repository = SemanticSnapshot.from_value({} if declared is None else {"marketplace": declared})

    assert sentinel_declarations(repository) != home_binding_declarations(home_bound_manifest())


def test_declaration_guard_trips_on_a_sentinel_left_without_a_binding() -> None:
    manifest = FieldManifest(rules=(FieldRule(path=("marketplace",), scope=FieldScope.SHARED),))
    repository = SemanticSnapshot.from_value(
        {"marketplace": f"{HOME_BINDING_SENTINEL}/{MARKETPLACE_KEY}"},
    )

    assert sentinel_declarations(repository) != home_binding_declarations(manifest)


def test_declaration_guard_accepts_a_matching_placeholder() -> None:
    repository = SemanticSnapshot.from_value(
        {"marketplace": f"{HOME_BINDING_SENTINEL}/{MARKETPLACE_KEY}"},
    )

    assert sentinel_declarations(repository) == home_binding_declarations(home_bound_manifest())
