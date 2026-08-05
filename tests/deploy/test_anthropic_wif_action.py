from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION = REPO_ROOT / ".github" / "actions" / "anthropic-wif" / "action.yml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "anthropic-wif-check.yml"


def test_action_contains_only_non_secret_wif_identifiers() -> None:
    text = ACTION.read_text()

    assert "secrets." not in text
    assert "ANTHROPIC_API_KEY=" not in text
    assert "fdrl_012fnG39en6i4J9iXBaeNWfM" in text
    assert "c0297d32-a375-42a3-bca8-ea26b3824e08" in text
    assert "svac_015intzGxfwcxbtjc8dnHgJW" in text
    assert "wrkspc_01YFje15eC5qAC1jaBxhSRFT" in text


def test_check_workflow_requests_only_the_permissions_wif_needs() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())

    assert workflow[True] == {"workflow_dispatch": None}
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert workflow["jobs"]["exchange"]["steps"][-1]["run"] == (
        "with-anthropic-wif check-anthropic-wif"
    )


def test_check_never_calls_the_messages_api() -> None:
    action_dir = ACTION.parent
    text = "\n".join(path.read_text() for path in sorted((action_dir / "bin").iterdir()))

    assert "/v1/oauth/token" in text
    assert "/v1/messages" not in text
