from __future__ import annotations

import importlib.util
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "roles/devbox/files/dot_codex/bin/reconcile_config.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("reconcile_codex_config", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECONCILER = _load_module()

MANAGED = """\
personality = "pragmatic"
model = "gpt-5.6-sol"

[features]
memories = true

[sandbox_workspace_write]
network_access = true

[otel]
environment = "personal"
"""


def test_reconcile_replaces_owned_values_and_preserves_app_state() -> None:
    live = """\
personality = "friendly"
model = "old-model"
notify = ["/machine/local/notifier"]

[features]
memories = false
js_repl = false

[projects."/Users/example/project"]
trust_level = "trusted"

[plugins.example]
enabled = true

[otel]
environment = "old"
"""

    result = RECONCILER.reconcile(MANAGED, live)
    parsed = tomllib.loads(result)

    assert parsed["personality"] == "pragmatic"
    assert parsed["model"] == "gpt-5.6-sol"
    assert parsed["notify"] == ["/machine/local/notifier"]
    assert parsed["features"] == {"memories": True}
    assert "js_repl" not in parsed["features"]
    assert parsed["projects"]["/Users/example/project"]["trust_level"] == "trusted"
    assert parsed["plugins"]["example"]["enabled"] is True
    assert parsed["otel"]["environment"] == "personal"


def test_reconcile_removes_legacy_telemetry_marker_block() -> None:
    live = """\
model = "old-model"

# BEGIN devbox otelcol-edge telemetry
[otel]
environment = "legacy"
# END devbox otelcol-edge telemetry

[desktop]
analytics = false
"""

    result = RECONCILER.reconcile(MANAGED, live)

    assert "otelcol-edge" not in result
    assert tomllib.loads(result)["desktop"]["analytics"] is False


def test_reconcile_is_idempotent() -> None:
    once = RECONCILER.reconcile(MANAGED, "[desktop]\nanalytics = false\n")
    twice = RECONCILER.reconcile(MANAGED, once)

    assert twice == once


def test_invalid_live_config_is_rejected() -> None:
    with pytest.raises(RECONCILER.ReconcileError, match="invalid TOML in live config"):
        RECONCILER.reconcile(MANAGED, "[features\n")


def test_cli_creates_private_config_and_check_reports_no_drift(tmp_path: Path) -> None:
    managed = tmp_path / "managed.toml"
    target = tmp_path / "config.toml"
    managed.write_text(MANAGED, encoding="utf-8")

    first = subprocess.run(
        [sys.executable, SCRIPT, "--managed", managed, "--target", target],
        check=True,
        capture_output=True,
        text=True,
    )
    check = subprocess.run(
        [sys.executable, SCRIPT, "--managed", managed, "--target", target, "--check"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert first.stdout.strip() == "changed"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert check.returncode == 0
    assert check.stdout.strip() == "unchanged"
