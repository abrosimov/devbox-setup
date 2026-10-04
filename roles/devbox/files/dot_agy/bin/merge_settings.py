#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# json.loads raises JSONDecodeError and Path.read_text raises UnicodeDecodeError when a
# file's bytes do not decode; both mean "this file carries no usable JSON". OSError is
# deliberately absent: a file we failed to *read* is not a file we know to be empty, and
# conflating the two is how a user's live settings get replaced by managed-only content.
PARSE_ERRORS = (json.JSONDecodeError, UnicodeDecodeError)


def merge(base: dict[str, object], overrides: dict[str, object]) -> None:
    for k, v in overrides.items():
        existing = base.get(k)
        if isinstance(v, dict) and isinstance(existing, dict):
            merge(existing, v)
        elif isinstance(v, list) and isinstance(existing, list):
            # union of lists, preserving order
            base[k] = existing + [x for x in v if x not in existing]
        else:
            base[k] = v


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    base_path = Path(sys.argv[1])
    target_path = Path(sys.argv[2])

    if not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(base_path.read_text())
        target_path.chmod(0o600)
        sys.exit(0)

    # An unparseable managed source has nothing to contribute, so leave the live file
    # exactly as it is; an unreadable one is a provisioning fault and propagates.
    try:
        base_data = json.loads(base_path.read_text())
    except PARSE_ERRORS:
        sys.exit(0)

    try:
        target_data = json.loads(target_path.read_text())
    except PARSE_ERRORS:
        target_data = {}

    # We want target_data (app-owned) to be updated with base_data (managed).
    # But for arrays like trustedWorkspaces, we want the union.
    # So we merge base_data INTO target_data.
    merge(target_data, base_data)

    target_path.write_text(json.dumps(target_data, indent=2))
    target_path.chmod(0o600)
