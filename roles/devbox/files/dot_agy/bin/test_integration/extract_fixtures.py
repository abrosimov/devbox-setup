#!/usr/bin/env python3
"""Extract anonymised hook fixtures from Claude Code session logs.

Walks ``~/.claude/projects/*/<session>.jsonl``, finds ``tool_use`` events and
the few stdin-driven CLI tools (statusline), wraps each into a hook-payload
JSON file, anonymises it, and writes it under ``fixtures/<bucket>/<sha8>.json``.

Stdlib only. Idempotent: re-running over the same logs produces the same files
because the SHA8 of an anonymised payload is stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent))
sys.path.insert(0, str(THIS_DIR))

from test_integration.anonymise import anonymise

# tool_name → fixture bucket name (matches lifecycle ids in targets.py).
TOOL_NAME_TO_BUCKET: dict[str, str] = {
    "Bash": "pre_tool_use_bash",
    "Write": "pre_tool_use_write",
    "Edit": "pre_tool_use_edit",
    "MultiEdit": "pre_tool_use_multiedit",
}

POST_TOOL_BUCKETS: dict[str, str] = {
    "Edit": "post_tool_use_edit",
    "Write": "post_tool_use_write",
    "MultiEdit": "post_tool_use_multiedit",
    "NotebookEdit": "post_tool_use_notebookedit",
}


def _stable_sha8(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _walk_jsonl(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.jsonl"))


def _iter_records(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except OSError:
        return []
    return out


def _build_pre_payload(tool_use: dict[str, Any]) -> dict[str, Any] | None:
    name = tool_use.get("name")
    if not isinstance(name, str):
        return None
    tool_input = tool_use.get("input") or {}
    if not isinstance(tool_input, dict):
        return None
    return {
        "tool_name": name,
        "tool_input": tool_input,
        "hook_event_name": "PreToolUse",
    }


def _build_post_payload(record: dict[str, Any], tool_use: dict[str, Any]) -> dict[str, Any] | None:
    name = tool_use.get("name")
    if not isinstance(name, str):
        return None
    if name not in POST_TOOL_BUCKETS:
        return None
    tool_input = tool_use.get("input") or {}
    if not isinstance(tool_input, dict):
        return None
    tool_response_obj = record.get("toolUseResult")
    if isinstance(tool_response_obj, dict):
        tool_response: Any = tool_response_obj
    else:
        tool_response = ""
    return {
        "tool_name": name,
        "tool_input": tool_input,
        "tool_response": tool_response,
        "hook_event_name": "PostToolUse",
    }


def _is_statusline_payload(obj: dict[str, Any]) -> bool:
    # The statusline reads ``{"cwd":..., "model":..., "workspace":..., ...}``.
    # If the log captures the literal stdin payload we can replay it directly.
    return "cwd" in obj and "model" in obj and ("workspace" in obj or "context_window" in obj)


def _collect_tool_uses(records: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for record in records:
        rtype = record.get("type")
        if rtype != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "tool_use":
                continue
            payload = _build_pre_payload(item)
            if payload is None:
                continue
            bucket = TOOL_NAME_TO_BUCKET.get(payload["tool_name"])
            if bucket is None:
                continue
            out.append((bucket, payload))
    return out


def _index_assistant_tool_uses(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    # Index assistant tool_use entries by tool_use_id so we can pair them with
    # the user-role tool_result that follows.
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            tool_id = item.get("id")
            if isinstance(tool_id, str):
                index[tool_id] = item
    return index


def _pair_tool_result(
    record: dict[str, Any],
    item: dict[str, Any],
    tool_use_index: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    tool_id = item.get("tool_use_id")
    if not isinstance(tool_id, str):
        return None
    tool_use = tool_use_index.get(tool_id)
    if tool_use is None:
        return None
    payload = _build_post_payload(record, tool_use)
    if payload is None:
        return None
    bucket = POST_TOOL_BUCKETS.get(payload["tool_name"])
    if bucket is None:
        return None
    return bucket, payload


def _collect_post_tool_uses(
    records: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    tool_use_index = _index_assistant_tool_uses(records)

    for record in records:
        if record.get("type") != "user":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            paired = _pair_tool_result(record, item, tool_use_index)
            if paired is not None:
                out.append(paired)
    return out


def _collect_statuslines(records: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for record in records:
        rtype = record.get("type")
        if rtype not in {"system", "queued_command"}:
            continue
        # Bare statusline payloads embedded in logs are rare. Skip unless the
        # whole record actually matches the shape.
        if _is_statusline_payload(record):
            out.append(("cli_statusline", record))
    return out


def write_fixture(bucket: str, payload: dict[str, Any], out_dir: Path) -> bool:
    anon = anonymise(payload)
    bucket_dir = out_dir / bucket
    bucket_dir.mkdir(parents=True, exist_ok=True)
    sha = _stable_sha8(anon)
    target = bucket_dir / f"{sha}.json"
    if target.exists():
        return False
    target.write_text(json.dumps(anon, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def extract(
    root: Path,
    out_dir: Path,
    max_per_bucket: int,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    per_bucket_seen: Counter[str] = Counter()

    files = _walk_jsonl(root)
    for path in files:
        records = _iter_records(path)
        if not records:
            continue
        candidates: list[tuple[str, dict[str, Any]]] = []
        candidates.extend(_collect_tool_uses(records))
        candidates.extend(_collect_post_tool_uses(records))
        candidates.extend(_collect_statuslines(records))
        for bucket, payload in candidates:
            if per_bucket_seen[bucket] >= max_per_bucket:
                continue
            if write_fixture(bucket, payload, out_dir):
                per_bucket_seen[bucket] += 1
                counts[bucket] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract anonymised hook fixtures from Claude Code session logs.",
    )
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".claude" / "projects"),
        help="Session-log root directory (default: ~/.claude/projects)",
    )
    parser.add_argument(
        "--out",
        default=str(THIS_DIR / "fixtures"),
        help="Output directory for fixture buckets (default: ./fixtures)",
    )
    parser.add_argument(
        "--max-per-bucket",
        type=int,
        default=50,
        help="Cap fixtures per bucket (default: 50)",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = extract(root, out_dir, args.max_per_bucket)
    if not counts:
        sys.stdout.write("No fixtures extracted (no .jsonl files or no recognisable events).\n")
        return 0
    sys.stdout.write("Extracted fixtures per bucket:\n")
    for bucket in sorted(counts):
        sys.stdout.write(f"  {bucket}: {counts[bucket]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
