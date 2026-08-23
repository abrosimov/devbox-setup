"""The endpoint.env contract as enforced by the playbook's preflight awk.

The awk program is read out of install_otelbox_edge.yml and executed verbatim, so
this suite cannot drift from the playbook. It is the second of the two enforcement
points for the same contract — the first is the wrapper regex, covered in the
sibling test_otelbox_edge_run.py.

Regression origin: a machine-local endpoint.env still carrying the v1 variable name
(OTELBOX_EDGE_ENDPOINT) failed this gate silently, and the whole v2 install stopped.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TASKS = REPO_ROOT / "roles/devbox/tasks/darwin/install_otelbox_edge.yml"

_tasks = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
_validate = next(t for t in _tasks if t["name"].endswith("validate the endpoint file contract"))
AWK_ARGV: list[str] = _validate["ansible.builtin.command"]["argv"]
AWK_BIN, AWK_PROGRAM = AWK_ARGV[0], AWK_ARGV[1]

pytestmark = pytest.mark.skipif(not Path(AWK_BIN).exists(), reason=f"{AWK_BIN} not available")


def _check(tmp_path: Path, body: str) -> int:
    endpoint_env = tmp_path / "endpoint.env"
    endpoint_env.write_text(body, encoding="utf-8")
    return subprocess.run(
        [AWK_BIN, AWK_PROGRAM, str(endpoint_env)],
        capture_output=True,
        check=False,
        timeout=30,
    ).returncode


def test_awk_argv_reads_the_deployed_endpoint_file() -> None:
    assert AWK_ARGV[2] == "{{ devbox_otelbox_edge_endpoint_env }}"


def test_valid_endpoint_file_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443\n") == 0


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("v1 variable name", "OTELBOX_EDGE_ENDPOINT=otel.example.com:443\n"),
        (
            "second line",
            "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com:443\nOTELBOX_EDGE_ENDPOINT=x:1\n",
        ),
        ("missing port", "OTELBOX_UPSTREAM_ENDPOINT=otel.example.com\n"),
        ("scheme prefix", "OTELBOX_UPSTREAM_ENDPOINT=https://otel.example.com:443\n"),
        ("empty file", ""),
    ],
)
def test_malformed_endpoint_file_fails(tmp_path: Path, case: str, body: str) -> None:
    assert _check(tmp_path, body) != 0, case
