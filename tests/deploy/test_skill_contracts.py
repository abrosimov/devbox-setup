"""Proto contracts shipped inside skills must lint; skipped when buf is not installed."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTO_MODULES = [REPO_ROOT / "roles/devbox/files/dot_ai/skills/tla-plus"]


@pytest.mark.skipif(shutil.which("buf") is None, reason="buf not installed")
@pytest.mark.parametrize("module", PROTO_MODULES, ids=lambda p: p.name)
def test_skill_proto_contracts_lint(module: Path) -> None:
    result = subprocess.run(
        ["buf", "lint"], cwd=module, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
