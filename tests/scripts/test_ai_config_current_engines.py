from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from ai_config.adapters import EngineKind, engine_adapter, resolve_engine_paths
from ai_config.decisions import DecisionSet
from ai_config.resolution import OperationMode
from ai_config.service import inspect_engine, operate_engine

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("engine", tuple(EngineKind))
def test_current_repository_documents_apply_and_converge_in_an_isolated_home(
    tmp_path: Path,
    engine: EngineKind,
) -> None:
    adapter = engine_adapter(engine)
    isolated_repo = tmp_path / "repository"
    isolated_home = tmp_path / "home"
    state_root = tmp_path / "state"
    for relative_path in (
        adapter.repository_relative_path,
        adapter.manifest_relative_path,
    ):
        source = REPO_ROOT / relative_path
        destination = isolated_repo / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

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
