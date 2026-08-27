from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ai_config.adapters import (
    EngineKind,
    engine_adapter,
    load_snapshot,
    parse_engine_manifest,
    resolve_engine_paths,
)
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

if TYPE_CHECKING:
    from ai_config.model import FieldPath

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_KEY = ".claude/marketplaces/langfuse-observability"


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
    repository = load_snapshot(
        repo_root / adapter.repository_relative_path,
        adapter.configuration_format,
    )
    return sentinel_declarations(repository), home_binding_declarations(manifest)


def copy_engine_documents(engine: EngineKind, repo_root: Path) -> None:
    adapter = engine_adapter(engine)
    for relative_path in (adapter.repository_relative_path, adapter.manifest_relative_path):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative_path, destination)


@pytest.mark.parametrize("engine", tuple(EngineKind))
def test_current_repository_documents_apply_and_converge_in_an_isolated_home(
    tmp_path: Path,
    engine: EngineKind,
) -> None:
    isolated_repo = tmp_path / "repository"
    isolated_home = tmp_path / "home"
    state_root = tmp_path / "state"
    copy_engine_documents(engine, isolated_repo)

    first = operate_engine(
        engine,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=state_root,
        mode=OperationMode.APPLY,
        decisions=DecisionSet(()),
        check=False,
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
    )
    inspection = inspect_engine(
        engine,
        repo_root=isolated_repo,
        home=isolated_home,
        profile="personal",
        state_root=state_root,
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


def test_home_declaration_guard_is_not_vacuous() -> None:
    expectations = [engine_declarations(engine, REPO_ROOT)[1] for engine in EngineKind]

    assert any(expectations)


def test_declaration_guard_trips_on_a_stale_placeholder_in_a_current_document(
    tmp_path: Path,
) -> None:
    engine = EngineKind.CLAUDE
    isolated_repo = tmp_path / "repository"
    copy_engine_documents(engine, isolated_repo)
    document = isolated_repo / engine_adapter(engine).repository_relative_path
    current = document.read_text(encoding="utf-8")
    stale = current.replace(
        f"{HOME_BINDING_SENTINEL}/{MARKETPLACE_KEY}",
        f"{HOME_BINDING_SENTINEL}/{MARKETPLACE_KEY}-renamed",
    )
    assert stale != current
    document.write_text(stale, encoding="utf-8")

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
