"""`ai-config apply codex` must not undo what `scripts/codex-hook-trust.py` writes.

Both own parts of `~/.codex/config.toml`: `hooks` is repository-owned (`shared`),
while the trust step writes `hooks.state."<key>".trusted_hash` underneath it.
Pinned against the real manifest and the real key shape, not a synthetic fixture.
"""

from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest
from ai_config.adapters import EngineKind, resolve_engine_paths
from ai_config.decisions import DecisionSet
from ai_config.resolution import OperationMode
from ai_config.service import operate_engine
from ai_config.state import resolve_state_paths
from ai_config_fixtures import copy_template_variables

REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_SOURCE = REPO_ROOT / "roles/devbox/files/dot_codex"
PROFILE = "personal"
TRUST_KEY = "/Users/example/.codex/config.toml:session_start:0:0"
TRUSTED_HASH = "sha256:d0a7803e3584f8cc918be14d24f7c61c35ad945e696a5d6a62ede2d1ba4dd4b9"


@pytest.fixture
def tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    state_root = tmp_path / "state"
    paths = resolve_engine_paths(EngineKind.CODEX, repo_root=repo_root, home=home)
    paths.repository.parent.mkdir(parents=True)
    shutil.copy(CODEX_SOURCE / "config.toml.j2", paths.repository)
    shutil.copy(CODEX_SOURCE / "config.ai-config.json", paths.manifest)
    copy_template_variables(repo_root)
    paths.live.parent.mkdir(parents=True)
    paths.live.write_text(
        paths.repository.read_text(encoding="utf-8").replace("{{ devbox_active_profile }}", PROFILE)
        + f'\n[hooks.state."{TRUST_KEY}"]\n'
        f'trusted_hash = "{TRUSTED_HASH}"\nenabled = true\n',
        encoding="utf-8",
    )
    return repo_root, home, state_root


def apply_codex(tree: tuple[Path, Path, Path]) -> None:
    repo_root, home, state_root = tree
    operate_engine(
        EngineKind.CODEX,
        repo_root=repo_root,
        home=home,
        profile=PROFILE,
        state_root=state_root,
        mode=OperationMode.APPLY,
        decisions=DecisionSet(decisions=()),
        check=False,
    )


def table(value: object, *keys: str) -> dict[str, object]:
    for key in keys:
        assert isinstance(value, dict)
        value = value[key]
    assert isinstance(value, dict)
    return value


def live_table(tree: tuple[Path, Path, Path], *keys: str) -> dict[str, object]:
    repo_root, home, _ = tree
    live = resolve_engine_paths(EngineKind.CODEX, repo_root=repo_root, home=home).live
    return table(tomllib.loads(live.read_text(encoding="utf-8")), *keys)


def test_apply_preserves_a_granted_trusted_hash(tree: tuple[Path, Path, Path]) -> None:
    apply_codex(tree)

    assert live_table(tree, "hooks", "state", TRUST_KEY) == {
        "trusted_hash": TRUSTED_HASH,
        "enabled": True,
    }


def test_repeated_applies_keep_the_trusted_hash(tree: tuple[Path, Path, Path]) -> None:
    apply_codex(tree)
    apply_codex(tree)

    assert live_table(tree, "hooks", "state", TRUST_KEY)["trusted_hash"] == TRUSTED_HASH


def test_apply_still_owns_the_hook_definitions(tree: tuple[Path, Path, Path]) -> None:
    apply_codex(tree)
    hooks = live_table(tree, "hooks")
    declared = table(
        tomllib.loads((CODEX_SOURCE / "config.toml.j2").read_text(encoding="utf-8")),
        "hooks",
    )

    assert {event: hooks[event] for event in declared} == declared


def test_machine_local_trust_never_leaks_into_the_recorded_base_state(
    tree: tuple[Path, Path, Path],
) -> None:
    _, home, state_root = tree
    apply_codex(tree)
    base_path = resolve_state_paths(
        EngineKind.CODEX,
        profile=PROFILE,
        home=home,
        state_root=state_root,
    ).base
    recorded = table(json.loads(base_path.read_text(encoding="utf-8")), "snapshot", "hooks")

    assert "state" not in recorded
