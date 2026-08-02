"""Declarative table of integration targets.

Each entry pairs a Claude Code hook script with the lifecycle bucket whose
fixtures feed it (under ``fixtures/<lifecycle>/``) and an ``ExpectedInvariants``
contract describing what must be true of the script's response to ANY recorded
or synthetic input.

Invariants enforced per target:
- Exit code lies in ``invariants.exit_codes``.
- Stdout is either empty OR valid JSON (when JSON shape is expected) OR
  free-form text (when ``stdout_can_be_plain_text`` is set).
- If ``invariants.stdout_json_schema`` is set, the JSON conforms to that
  schema.
- Stderr does NOT contain a Python traceback or unhandled-error signature.
- Subprocess returns within ``invariants.max_timeout_seconds``.

The harness does not "compare" anything — it asserts that a single script
behaves within its declared contract. This is the regression model for
production hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

BIN_DIR: Final[Path] = Path(__file__).resolve().parent.parent

# Known JSON output shapes scripts may emit. Validated structurally by the
# integration runner — extend only when a new emit-shape is added to a hook.
StdoutJsonSchema = Literal[
    "pre_tool_use_decision",
    "permission_request_decision",
    "additional_context",
]


@dataclass(frozen=True)
class ExpectedInvariants:
    exit_codes: frozenset[int]
    stdout_can_be_empty: bool = True
    stdout_json_schema: StdoutJsonSchema | None = None
    # When True, stdout may also be free-form text (no JSON parse attempted).
    # Used for hooks like pre_compact_mask that emit a context-preservation
    # blob meant for downstream summarisation rather than structured control.
    stdout_can_be_plain_text: bool = False
    max_timeout_seconds: int = 10


@dataclass(frozen=True)
class IntegrationTarget:
    label: str
    script_path: Path
    lifecycle: str
    invariants: ExpectedInvariants


def _target(
    label: str,
    script_name: str,
    lifecycle: str,
    *,
    exit_codes: frozenset[int],
    stdout_json_schema: StdoutJsonSchema | None = None,
    stdout_can_be_plain_text: bool = False,
    max_timeout_seconds: int = 10,
) -> IntegrationTarget:
    return IntegrationTarget(
        label=label,
        script_path=BIN_DIR / script_name,
        lifecycle=lifecycle,
        invariants=ExpectedInvariants(
            exit_codes=exit_codes,
            stdout_json_schema=stdout_json_schema,
            stdout_can_be_plain_text=stdout_can_be_plain_text,
            max_timeout_seconds=max_timeout_seconds,
        ),
    )


# Common exit-code sets, named so the table reads declaratively.
_PRE_TOOL_USE_CODES: Final = frozenset({0, 2})
_POST_TOOL_USE_CODES: Final = frozenset({0})
_STOP_CODES: Final = frozenset({0, 2})
_PRE_COMPACT_CODES: Final = frozenset({0})


# All hooks listed in hooks.json that read stdin from Claude Code. Lifecycles
# match fixture bucket names (test_integration/fixtures/<lifecycle>/). Scripts
# that fan out across multiple lifecycles (pre_tmpdir_guard runs on both Bash
# and Write matchers) get one IntegrationTarget per lifecycle.
INTEGRATION_TARGETS: tuple[IntegrationTarget, ...] = (
    # --- PreToolUse: Bash matcher chain ------------------------------------
    _target(
        "pre_bash_toolchain_guard.bash",
        "pre_bash_toolchain_guard.py",
        "pre_tool_use_bash",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "pre_tmpdir_guard.bash",
        "pre_tmpdir_guard.py",
        "pre_tool_use_bash",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "bash_decision_gate.bash",
        "bash_decision_gate.py",
        "pre_tool_use_bash",
        exit_codes=_PRE_TOOL_USE_CODES,
        stdout_json_schema="pre_tool_use_decision",
    ),
    _target(
        "pre_bash_boundary_wrap.bash",
        "pre_bash_boundary_wrap.py",
        "pre_tool_use_bash",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    # --- PreToolUse: Write matcher chain -----------------------------------
    _target(
        "pre_tmpdir_guard.write",
        "pre_tmpdir_guard.py",
        "pre_tool_use_write",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "pre_edit_lint_guard.write",
        "pre_edit_lint_guard.py",
        "pre_tool_use_write",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "pre_write_completion_gate.write",
        "pre_write_completion_gate.py",
        "pre_tool_use_write",
        exit_codes=_PRE_TOOL_USE_CODES,
        # gate runs verify-se-completion via subprocess — needs more time.
        max_timeout_seconds=30,
    ),
    _target(
        "pre_write_existing_guard.write",
        "pre_write_existing_guard.py",
        "pre_tool_use_write",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "pre_plan_code_guard.write",
        "pre_plan_code_guard.py",
        "pre_tool_use_write",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    # --- PreToolUse: Edit matcher chain ------------------------------------
    _target(
        "pre_edit_lint_guard.edit",
        "pre_edit_lint_guard.py",
        "pre_tool_use_edit",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    _target(
        "pre_plan_code_guard.edit",
        "pre_plan_code_guard.py",
        "pre_tool_use_edit",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    # --- PreToolUse: MultiEdit matcher chain -------------------------------
    _target(
        "pre_plan_code_guard.multiedit",
        "pre_plan_code_guard.py",
        "pre_tool_use_multiedit",
        exit_codes=_PRE_TOOL_USE_CODES,
    ),
    # --- PostToolUse: Edit matcher chain -----------------------------------
    _target(
        "post_edit_lint.edit",
        "post_edit_lint.py",
        "post_tool_use_edit",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=30,
    ),
    _target(
        "post_edit_typecheck.edit",
        "post_edit_typecheck.py",
        "post_tool_use_edit",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=30,
    ),
    _target(
        "post_edit_cyrillic_guard.edit",
        "post_edit_cyrillic_guard.py",
        "post_tool_use_edit",
        exit_codes=_POST_TOOL_USE_CODES,
    ),
    # --- PostToolUse: Write matcher chain ----------------------------------
    _target(
        "post_edit_lint.write",
        "post_edit_lint.py",
        "post_tool_use_write",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=30,
    ),
    _target(
        "post_edit_typecheck.write",
        "post_edit_typecheck.py",
        "post_tool_use_write",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=30,
    ),
    _target(
        "post_edit_cyrillic_guard.write",
        "post_edit_cyrillic_guard.py",
        "post_tool_use_write",
        exit_codes=_POST_TOOL_USE_CODES,
    ),
    # --- Stop --------------------------------------------------------------
    _target(
        "stop_format",
        "stop_format.py",
        "stop",
        exit_codes=_STOP_CODES,
        max_timeout_seconds=30,
    ),
    _target(
        "stop_lint_gate",
        "stop_lint_gate.py",
        "stop",
        exit_codes=_STOP_CODES,
        max_timeout_seconds=30,
    ),
    # --- PreCompact --------------------------------------------------------
    _target(
        "session_save",
        "session_save.py",
        "pre_compact",
        exit_codes=_PRE_COMPACT_CODES,
        max_timeout_seconds=15,
    ),
    _target(
        "pre_compact_mask",
        "pre_compact_mask.py",
        "pre_compact",
        exit_codes=_PRE_COMPACT_CODES,
        max_timeout_seconds=15,
        # Emits a "--- CONTEXT PRESERVED ---" text blob (intended for the
        # post-compact summary), not structured JSON.
        stdout_can_be_plain_text=True,
    ),
    # --- PostToolUse, all matchers (suggest-checkpoint runs without one) ---
    _target(
        "suggest_checkpoint.edit",
        "suggest_checkpoint.py",
        "post_tool_use_edit",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=15,
    ),
    _target(
        "suggest_checkpoint.write",
        "suggest_checkpoint.py",
        "post_tool_use_write",
        exit_codes=_POST_TOOL_USE_CODES,
        max_timeout_seconds=15,
    ),
)
