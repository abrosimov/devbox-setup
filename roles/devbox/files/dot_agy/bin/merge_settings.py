#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def merge(base, overrides):
    for k, v in overrides.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            merge(base[k], v)
        elif isinstance(v, list) and k in base and isinstance(base[k], list):
            # union of lists, preserving order
            base[k] = base[k] + [x for x in v if x not in base[k]]
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

    try:
        base_data = json.loads(base_path.read_text())
    except Exception:
        sys.exit(0)

    try:
        target_data = json.loads(target_path.read_text())
    except Exception:
        target_data = {}

    # We want target_data (app-owned) to be updated with base_data (managed).
    # But for arrays like trustedWorkspaces, we want the union.
    # So we merge base_data INTO target_data.
    merge(target_data, base_data)

    target_path.write_text(json.dumps(target_data, indent=2))
    target_path.chmod(0o600)
