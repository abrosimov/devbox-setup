from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("target", "engine"),
    [
        ("claude-push", "claude"),
        ("agy-push", "agy"),
        ("codex-push", "codex"),
    ],
)
def test_ai_push_target_prints_safe_workflow_and_exits_without_ansible(
    target: str,
    engine: str,
) -> None:
    result = subprocess.run(
        ["make", "--no-print-directory", target],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert f"make {target} is intentionally blocked" in output
    assert f"scripts/ai-config diff {engine}" in output
    assert f"scripts/ai-config reconcile {engine}" in output
    assert f"scripts/ai-config apply {engine}" in output
    assert "--check" in output
    assert "No Ansible command was run." in output
    assert "ansible-playbook" not in output
