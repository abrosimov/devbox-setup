"""The runnable examples shipped with the go-observability and tla-plus skills.

Each skill's references point at files under ``examples/``; these tests are what keeps those
files true. Every test needs a toolchain the CI runner does not have (Go, promtool, Java with
tla2tools and CommunityModules), so each skips when its tool is missing and runs on a
provisioned devbox, where ``devbox_packages`` installs all of them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "roles/devbox/files/dot_ai/skills"
OBS = SKILLS / "go-observability/examples"
TLA = SKILLS / "tla-plus/examples/orders"
TLA_SKILL = SKILLS / "tla-plus"
TLA_LIB = Path(os.environ.get("TLA_LIB", Path.home() / ".local/share/tlaplus"))
TLA2TOOLS = Path(os.environ.get("TLA2TOOLS_JAR", TLA_LIB / "tla2tools/tla2tools.jar"))
COMMUNITY = TLA_LIB / "communitymodules/CommunityModules-deps.jar"


Result = subprocess.CompletedProcess[str]


def _run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> Result:
    return subprocess.run(
        args,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
    )


needs_go = pytest.mark.skipif(shutil.which("go") is None, reason="go not installed")
needs_promtool = pytest.mark.skipif(
    shutil.which("promtool") is None, reason="promtool not installed"
)
needs_java = pytest.mark.skipif(shutil.which("java") is None, reason="java not installed")
needs_tla2tools = pytest.mark.skipif(not TLA2TOOLS.is_file(), reason=f"{TLA2TOOLS} missing")
needs_community = pytest.mark.skipif(not COMMUNITY.is_file(), reason=f"{COMMUNITY} missing")
needs_buf = pytest.mark.skipif(shutil.which("buf") is None, reason="buf not installed")
needs_apalache = pytest.mark.skipif(
    shutil.which("apalache-mc") is None, reason="apalache-mc not installed"
)


@needs_go
@pytest.mark.parametrize("module", ["dashboards", "bootstrap"])
def test_go_examples_build(module: str) -> None:
    result = _run(["go", "build", "-o", os.devnull, "."], OBS / module)
    assert result.returncode == 0, result.stderr


@needs_go
def test_dashboard_example_renders_json(tmp_path: Path) -> None:
    result = _run(["go", "run", ".", "-o", str(tmp_path)], OBS / "dashboards")
    assert result.returncode == 0, result.stderr
    rendered = tmp_path / "checkout.json"
    assert rendered.is_file()
    assert '"uid": "checkout"' in rendered.read_text(encoding="utf-8")


@needs_promtool
def test_rule_examples_pass_promtool_check() -> None:
    result = _run(
        ["promtool", "check", "rules", "alerts.yaml", "recording.yaml"], OBS / "rules/checkout"
    )
    assert result.returncode == 0, result.stdout + result.stderr


@needs_promtool
def test_rule_examples_pass_promtool_unit_tests() -> None:
    result = _run(["promtool", "test", "rules", "tests/alerts_test.yaml"], OBS / "rules/checkout")
    assert result.returncode == 0, result.stdout + result.stderr


def _tlc(config: str, module: str, env: dict[str, str] | None = None) -> Result:
    classpath = f"{TLA2TOOLS}:{COMMUNITY}" if COMMUNITY.is_file() else str(TLA2TOOLS)
    tlc = ["java", "-cp", classpath, "tlc2.TLC"]
    options = ["-config", config, "-workers", "auto", "-noTE", "-cleanup", module]
    return _run([*tlc, *options], TLA, env)


@needs_java
@needs_tla2tools
def test_orders_spec_parses() -> None:
    result = _run(["java", "-cp", str(TLA2TOOLS), "tla2sany.SANY", "Orders.tla"], TLA)
    assert result.returncode == 0, result.stdout + result.stderr


@needs_java
@needs_tla2tools
@pytest.mark.parametrize("config", ["MCOrders.cfg", "MCOrdersSafety.cfg"])
def test_orders_model_checks_with_tlc(config: str) -> None:
    result = _tlc(config, "MCOrders.tla")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Model checking completed. No error has been found." in result.stdout


@needs_java
@needs_tla2tools
@needs_community
def test_trace_validation_accepts_happy_path_and_rejects_ship_before_pay() -> None:
    traces = TLA / "traces"
    accepted = _tlc(
        "TraceOrders.cfg", "TraceOrders.tla", {"TRACE_PATH": str(traces / "happy-path.jsonl")}
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    rejected = _tlc(
        "TraceOrders.cfg", "TraceOrders.tla", {"TRACE_PATH": str(traces / "ship-before-pay.jsonl")}
    )
    assert rejected.returncode != 0, rejected.stdout


@needs_apalache
@pytest.mark.parametrize(
    "args",
    [
        ["typecheck", "ApaOrders.tla"],
        ["check", "--cinit=CInit", "--inv=NoDoublePayment", "--length=8", "ApaOrders.tla"],
        ["check", "--cinit=CInit", "--init=Init", "--inv=IndInv", "--length=0", "ApaOrders.tla"],
        ["check", "--cinit=CInit", "--init=IndInv", "--inv=IndInv", "--length=1", "ApaOrders.tla"],
    ],
)
def test_orders_apalache(args: list[str]) -> None:
    result = _run(["apalache-mc", *args], TLA)
    assert result.returncode == 0, result.stdout + result.stderr


@needs_buf
@pytest.mark.parametrize("module", [TLA_SKILL, TLA])
def test_proto_contracts_lint(module: Path) -> None:
    result = _run(["buf", "lint"], module)
    assert result.returncode == 0, result.stdout + result.stderr
