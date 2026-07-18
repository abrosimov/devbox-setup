#!/usr/bin/env python3
"""Proposal-discipline hook — dispatcher for UserPromptSubmit and Stop events.

Mitigates two recurring failure modes in long iterative dev sessions:

1. Full-rewrite-on-feedback: when the user iterates on a numbered proposal,
   Claude emits a four-screen rewrite instead of a delta. The user cannot
   tell what changed.
2. Renumbering: when the user answers numbered open questions, the next
   reply renumbers/reorders items, breaking parallel reading.

For each event, the hook inspects the payload and the JSONL transcript to
decide whether to inject ``additionalContext`` reminding Claude to operate
in delta-only / preserve-numbering mode. False positives degrade to a mild
nudge Claude can ignore; false negatives leave the existing behaviour
unchanged. Detection is conservative: a reminder is only injected when the
prior assistant turn looks like a proposal AND the user's reply looks like
iteration on it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, hooks

if TYPE_CHECKING:
    from collections.abc import Mapping

LONG_RESPONSE_LINE_THRESHOLD: Final[int] = 40

# The User Authority Protocol mandates "[Awaiting your decision]" at the end of
# every proposal. Detecting it is the highest-precision signal that the prior
# turn was a proposal awaiting iteration.
_AWAITING_DECISION_RE: Final[re.Pattern[str]] = re.compile(
    r"\[Awaiting your decision\]",
    re.IGNORECASE,
)

_NUMBERED_ITEM_RE: Final[re.Pattern[str]] = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)

_PROPOSAL_SIGNAL_RES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bOption\s+[A-Z0-9]\b"),
    re.compile(r"§\s*\d+"),
    re.compile(r"^\s*[A-Z]\)\s", re.MULTILINE),
)

_FEEDBACK_PATTERNS_EN: Final[re.Pattern[str]] = re.compile(
    r"\b("
    r"change\s+(?:this|that|it)|"
    r"instead\s+of|"
    r"option\s+[a-z0-9]+|"
    r"but\s+(?:make|do|use|try)|"
    r"actually,|"
    r"wait,|"
    r"scratch\s+that|"
    r"rewrite|"
    r"revise|"
    r"tweak|"
    r"adjust|"
    r"what\s+about|"
    r"why\s+not|"
    r"let'?s\s+try|"
    r"no,\s|"
    r"swap\s+(?:out|for)"
    r")\b",
    re.IGNORECASE,
)

_FEEDBACK_PATTERNS_RU: Final[re.Pattern[str]] = re.compile(
    r"("
    r"поменяй|"
    r"переделай|"
    r"подправь|"
    r"исправь|"
    r"вместо\s+|"
    r"что\s+насчет|"
    r"что\s+насчёт|"
    r"опция\s+\d+|"
    r"вариант\s+\d+|"
    r"а\s+если|"  # noqa: RUF001 -- intentional Cyrillic in Russian feedback regex
    r"может\s+лучше|"
    r"нет,\s|"
    r"давай\s+(?:переделаем|поменяем|сменим)|"
    r"вместо\s+этого"
    r")",
    re.IGNORECASE,
)

FEEDBACK_REMINDER: Final[str] = (
    "[proposal-discipline] This message looks like iteration on a prior proposal. "
    "Use Iteration voice mode: emit ONLY changed sections as "
    "`[§N CHANGED] why / before / after`, `[§N ADDED] why / content`, "
    "`[§N REMOVED] why`. Do not restate unchanged sections. "
    "Preserve the original numbering and ordering from the prior proposal — "
    "never renumber, never reorder, never collapse two items into one."
)

NUMBERED_REMINDER: Final[str] = (
    "[proposal-discipline] The user appears to be answering numbered open "
    "questions from the prior turn. Reference each item by its original "
    "question number. Preserve numbering exactly so the user can read "
    "question and answer as a parallel timeline."
)

DELTA_NEXT_TURN_REMINDER: Final[str] = (
    "[proposal-discipline] The last response was a long rewrite while the "
    "user was iterating on a structured proposal. Next iteration: emit only "
    "the delta against the prior proposal, preserving numbering. See the "
    "Iteration voice mode in USER_AUTHORITY_PROTOCOL."
)


def count_numbered_items(text: str) -> int:
    return len(_NUMBERED_ITEM_RE.findall(text))


def detect_feedback(prompt: str) -> bool:
    return bool(_FEEDBACK_PATTERNS_EN.search(prompt) or _FEEDBACK_PATTERNS_RU.search(prompt))


def detect_numbered_answers(prompt: str) -> bool:
    return count_numbered_items(prompt) >= 2


def looks_like_proposal(text: str) -> bool:
    if _AWAITING_DECISION_RE.search(text):
        return True
    if count_numbered_items(text) >= 3:
        return True
    return any(pattern.search(text) for pattern in _PROPOSAL_SIGNAL_RES)


def _read_jsonl_entries(path: Path) -> list[Mapping[str, object]]:
    try:
        raw = path.read_text(errors="ignore")
    except OSError:
        return []
    out: list[Mapping[str, object]] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _role_of(entry: Mapping[str, object]) -> str:
    msg = entry.get("message")
    if isinstance(msg, dict):
        role = msg.get("role")
        if isinstance(role, str):
            return role
    entry_type = entry.get("type")
    if isinstance(entry_type, str):
        return entry_type
    return ""


def _extract_text(entry: Mapping[str, object]) -> str:
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)


def _has_human_text(entry: Mapping[str, object]) -> bool:
    """Distinguish a real user prompt from a tool-result envelope.

    Tool-result-only user messages have content blocks of type ``tool_result``
    and no plain ``text`` block. They are not human input and would skew
    feedback detection.
    """
    msg = entry.get("message")
    if not isinstance(msg, dict):
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if not isinstance(content, list):
        return False
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                return True
    return False


def read_last_assistant_text(transcript_path: Path | None) -> str | None:
    if transcript_path is None or not transcript_path.exists():
        return None
    for entry in reversed(_read_jsonl_entries(transcript_path)):
        if _role_of(entry) != "assistant":
            continue
        text = _extract_text(entry)
        if text.strip():
            return text
    return None


def read_last_user_text(transcript_path: Path | None) -> str | None:
    if transcript_path is None or not transcript_path.exists():
        return None
    for entry in reversed(_read_jsonl_entries(transcript_path)):
        if _role_of(entry) != "user":
            continue
        if not _has_human_text(entry):
            continue
        text = _extract_text(entry)
        if text.strip():
            return text
    return None


def _transcript_path_from(payload: Mapping[str, object]) -> Path | None:
    raw = payload.get("transcript_path")
    if not isinstance(raw, str) or not raw:
        return None
    return Path(raw)


def handle_user_prompt_submit(payload: Mapping[str, object]) -> str | None:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None

    prior_assistant = read_last_assistant_text(_transcript_path_from(payload))
    if not prior_assistant or not looks_like_proposal(prior_assistant):
        return None

    reminders: list[str] = []
    if detect_feedback(prompt):
        reminders.append(FEEDBACK_REMINDER)
    if detect_numbered_answers(prompt):
        reminders.append(NUMBERED_REMINDER)

    if not reminders:
        return None
    return "\n\n".join(reminders)


def handle_stop(payload: Mapping[str, object]) -> str | None:
    message = payload.get("assistant_message")
    if not isinstance(message, str) or not message.strip():
        return None

    line_count = len(message.splitlines())
    if line_count < LONG_RESPONSE_LINE_THRESHOLD:
        return None

    prior_user = read_last_user_text(_transcript_path_from(payload))
    if not prior_user:
        return None

    if not (detect_feedback(prior_user) or detect_numbered_answers(prior_user)):
        return None
    return DELTA_NEXT_TURN_REMINDER


def dispatch(payload: Mapping[str, object]) -> str | None:
    event = payload.get("hook_event_name", "")
    if event == "UserPromptSubmit":
        return handle_user_prompt_submit(payload)
    if event == "Stop":
        # ``stop_hook_active`` is set by Claude Code when a Stop hook already
        # blocked the prior stop. We never block, so this matters less, but we
        # still skip to avoid piling reminders on a single turn cycle.
        if payload.get("stop_hook_active"):
            return None
        return handle_stop(payload)
    return None


def main() -> int:
    env.setup()
    data = hooks.read_hook_input()
    if not data:
        return hooks.ALLOW

    reminder = dispatch(data)
    if reminder:
        hooks.write_additional_context(reminder)
    return hooks.ALLOW


if __name__ == "__main__":
    sys.exit(main())
