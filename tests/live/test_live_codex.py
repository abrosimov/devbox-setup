"""Codex honours the config.toml that `ai-config apply codex` generated.

`codex app-server` answers `hooks/list` with every hook it discovered, where it
read it from, and whether it trusts it. That is the whole loop the repository
cares about — generated, discovered, trusted — proved by the same binary that
later enforces it, with no model call and no account.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from codex_hook_trust.allowlist import Allowlist, DeclaredHook, build_allowlist
from codex_hook_trust.appserver import StdioAppServer, spawn_app_server
from codex_hook_trust.trust import EX_CONFIG, HookInventory, Ownership, classify, list_hooks
from codex_hook_trust.trust import plan_trust as plan_hook_trust
from engines import require_binary
from generation import REPO_ROOT, apply_engine
from throwaway import ThrowawayHome

pytestmark = pytest.mark.live

HOOK_TRUST: Final = REPO_ROOT / "scripts" / "codex-hook-trust.py"
_APP_SERVER_TIMEOUT_SECONDS: Final = 120.0
_TRUST_TIMEOUT_SECONDS: Final = 300.0
_TRUSTED: Final = "trusted"
_MODIFIED: Final = "modified"
_TRUSTED_HASH_PREFIX: Final = 'trusted_hash = "sha256:'


@dataclass(frozen=True, slots=True)
class GeneratedCodex:
    home: ThrowawayHome
    codex_home: Path
    allowlist: Allowlist


def generate(root: Path) -> GeneratedCodex:
    require_binary("codex")
    home = ThrowawayHome.create(root)
    codex_home = home.directory(".codex")
    codex_home.chmod(0o700)
    apply_engine("codex", home)
    return GeneratedCodex(
        home=home,
        codex_home=codex_home,
        allowlist=build_allowlist(repo_root=REPO_ROOT, codex_home=codex_home, plugin_ids=()),
    )


def inventory(generated: GeneratedCodex) -> HookInventory:
    with spawn_app_server(
        codex_home=generated.codex_home,
        timeout=_APP_SERVER_TIMEOUT_SECONDS,
        search_path=os.environ.get("PATH"),
    ) as client:
        return list_hooks(client, generated.codex_home)


def grant_trust(generated: GeneratedCodex, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(HOOK_TRUST),
            "--repo-root",
            str(REPO_ROOT),
            "--codex-home",
            str(generated.codex_home),
            "--json",
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=_TRUST_TIMEOUT_SECONDS,
        env=generated.home.environment(),
        cwd=REPO_ROOT,
        check=False,
    )


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> GeneratedCodex:
    return generate(tmp_path_factory.mktemp("codex-live") / "home")


@pytest.fixture(scope="module")
def discovered(generated: GeneratedCodex) -> HookInventory:
    return inventory(generated)


@pytest.fixture
def fresh(tmp_path: Path) -> GeneratedCodex:
    return generate(tmp_path / "home")


def test_the_app_server_echoes_the_throwaway_codex_home(generated: GeneratedCodex) -> None:
    process = subprocess.Popen(
        [require_binary("codex"), "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=generated.home.environment(CODEX_HOME=str(generated.codex_home)),
    )
    client = StdioAppServer(process, timeout=_APP_SERVER_TIMEOUT_SECONDS)
    try:
        initialised = client.request(
            "initialize", {"clientInfo": {"name": "devbox-setup-live", "version": "1"}}
        )
    finally:
        client.close()

    assert Path(str(initialised["codexHome"])).resolve() == generated.codex_home.resolve()


def test_the_app_server_answers_without_errors(discovered: HookInventory) -> None:
    assert discovered.errors == ()


def test_every_hook_the_repository_declares_is_discovered(
    generated: GeneratedCodex,
    discovered: HookInventory,
) -> None:
    plan = plan_hook_trust(discovered, generated.allowlist)
    assert plan.undiscovered == ()
    assert {
        DeclaredHook(event_name=hook.event_name, command=hook.command)
        for hook in plan.owned
        if hook.command is not None
    } == set(generated.allowlist.declared)


def test_every_discovered_hook_is_read_from_the_throwaway_home(
    generated: GeneratedCodex,
    discovered: HookInventory,
) -> None:
    assert discovered.hooks
    for hook in discovered.hooks:
        assert Path(hook.source_path).resolve() == generated.codex_home.resolve() / "config.toml"


def test_no_hook_the_repository_does_not_declare_is_present(
    generated: GeneratedCodex,
    discovered: HookInventory,
) -> None:
    foreign = [
        hook
        for hook in discovered.hooks
        if classify(hook, generated.allowlist) is Ownership.FOREIGN
    ]
    assert foreign == []


def test_granting_trust_leaves_every_declared_hook_trusted_and_enabled(
    fresh: GeneratedCodex,
) -> None:
    before = plan_hook_trust(inventory(fresh), fresh.allowlist)
    assert before.pending, "expected a freshly generated config.toml to start untrusted"

    completed = grant_trust(fresh)
    assert completed.returncode == 0, completed.stderr

    after = plan_hook_trust(inventory(fresh), fresh.allowlist)
    assert after.pending == ()
    assert after.disabled == ()
    assert {hook.trust_status for hook in after.owned} == {_TRUSTED}
    assert len(after.owned) == len(fresh.allowlist.declared)


def test_a_stale_trusted_hash_is_seen_as_modified_and_trusted_again(
    fresh: GeneratedCodex,
) -> None:
    """The production failure mode: a Codex upgrade invalidates every stored hash.

    `trusted_hash` pins the shape Codex hashed a hook into, and that shape has
    already changed once upstream. When it changes the stored hash stops
    matching, Codex resolves the hook to `modified`, and drops it from dispatch
    without an error, a log line or any change to `hooks/list` reporting it
    discovered and enabled. Re-running the trust step is the repair; this is
    what proves the step still detects the state it repairs.
    """
    assert grant_trust(fresh).returncode == 0
    _invalidate_trusted_hashes(fresh.codex_home / "config.toml")

    stale = plan_hook_trust(inventory(fresh), fresh.allowlist)
    assert {hook.trust_status for hook in stale.owned} == {_MODIFIED}
    assert len(stale.pending) == len(fresh.allowlist.declared)
    assert grant_trust(fresh, "--check", "--fail-on-drift").returncode == EX_CONFIG

    assert grant_trust(fresh).returncode == 0
    repaired = plan_hook_trust(inventory(fresh), fresh.allowlist)
    assert {hook.trust_status for hook in repaired.owned} == {_TRUSTED}
    assert repaired.pending == ()


def test_a_configuration_codex_cannot_parse_is_reported_rather_than_ignored(
    fresh: GeneratedCodex,
) -> None:
    """Codex is the engine that fails loudly on a broken configuration.

    Pinned because the other two do not: Claude Code and agy both accept an
    unparseable file, fall back to defaults and dispatch nothing. Codex answers
    `hooks/list` with a parse error naming the file, line and column, and its own
    CLI refuses to start. If a future Codex starts swallowing this instead, the
    repository loses its only engine-side signal and this test says so.
    """
    config = fresh.codex_home / "config.toml"
    config.write_text('model = "gpt-5"\n[hooks\nSessionStart = [[[\n', encoding="utf-8")

    discovered = inventory(fresh)

    assert discovered.hooks == ()
    assert any(str(config) in error for error in discovered.errors), discovered.errors
    completed = grant_trust(fresh, "--check")
    assert completed.returncode == EX_CONFIG, completed.stdout
    assert "hooks/list reported an error" in completed.stderr


def test_an_undeclared_hook_is_refused_rather_than_trusted(fresh: GeneratedCodex) -> None:
    _declare_undeclared_stop_hook(fresh.codex_home / "config.toml")

    completed = grant_trust(fresh, "--check")

    assert completed.returncode == EX_CONFIG, completed.stdout
    refused = plan_hook_trust(inventory(fresh), fresh.allowlist).refused
    assert [hook.event_name for hook in refused] == ["stop"]


def test_a_configuration_without_its_hooks_block_reports_every_hook_undiscovered(
    fresh: GeneratedCodex,
) -> None:
    _remove_hooks_table(fresh.codex_home / "config.toml")

    completed = grant_trust(fresh, "--check")

    assert completed.returncode == EX_CONFIG, completed.stdout
    plan = plan_hook_trust(inventory(fresh), fresh.allowlist)
    assert plan.owned == ()
    assert set(plan.undiscovered) == set(fresh.allowlist.declared)


def _invalidate_trusted_hashes(config: Path) -> None:
    """Age every stored hash the way a Codex upgrade would: the hook is untouched."""
    stored = config.read_text(encoding="utf-8")
    aged = stored.replace(_TRUSTED_HASH_PREFIX, f"{_TRUSTED_HASH_PREFIX}0000")
    assert aged != stored, "trust was granted but no trusted_hash was written"
    config.write_text(aged, encoding="utf-8")


def _declare_undeclared_stop_hook(config: Path) -> None:
    lines = config.read_text(encoding="utf-8").splitlines()
    index = next(number for number, line in enumerate(lines) if line.startswith("Stop = ["))
    lines[index] = (
        lines[index].removesuffix("]")
        + ', { hooks = [{ command = "/usr/bin/true", type = "command" }] }]'
    )
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _remove_hooks_table(config: Path) -> None:
    """Reproduce the deploy failure this suite exists for: hooks silently absent."""
    lines = config.read_text(encoding="utf-8").splitlines()
    start = lines.index("[hooks]")
    end = next(
        number
        for number, line in enumerate(lines[start + 1 :], start=start + 1)
        if line.startswith("[")
    )
    config.write_text("\n".join(lines[:start] + lines[end:]) + "\n", encoding="utf-8")
