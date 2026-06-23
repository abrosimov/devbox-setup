"""Integration tests for Claude Code hook scripts.

Two layers:

1. **Smoke regression** — for each ``IntegrationTarget`` in
   ``targets.INTEGRATION_TARGETS``: feed every fixture under
   ``fixtures/<lifecycle>/`` (recorded + ``synth_<sha>.json`` +
   ``canonical_<n>_<id>.json``) into the script and assert the declared
   ``ExpectedInvariants`` contract (exit code, stdout shape, no traceback
   in stderr, timeout).

2. **Hypothesis property tests** — generative inputs against a handful of
   high-blast-radius hooks, with permanent ``@example`` regression pins for
   schema bugs we've shipped before. These run the script against fresh
   inputs that recorded fixtures don't cover.

The harness does not compare against an "old" implementation — that died
when the bash counterparts were removed. The contract is: a script must
remain correct on real input AND on the property-generated input space.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from test_integration.runner import RunRequest, parse_stdin_fixture, run_script
from test_integration.targets import (
    INTEGRATION_TARGETS,
    ExpectedInvariants,
    IntegrationTarget,
)

FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"


# Indicators that the subprocess raised an unhandled exception. Hooks must
# never crash — if they need to refuse work they exit with the appropriate
# code (BLOCK=2 for PreToolUse / Stop). A traceback in stderr is a bug.
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)")
_UNHANDLED_ERROR_RE = re.compile(r"^\w*Error:\s", re.MULTILINE)


# ---------------------------------------------------------------------------
# Layer 1 — smoke regression across recorded + synthetic + canonical fixtures.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SmokeFailure:
    fixture_name: str
    reason: str
    detail: str


def _list_fixtures(lifecycle: str) -> list[Path]:
    bucket = FIXTURES_DIR / lifecycle
    if not bucket.is_dir():
        return []
    return sorted(bucket.glob("*.json"))


def _load_fixture(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        obj = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    # Strip the documentation marker before sending to the script — handlers
    # never see ``__doc__`` from real Claude Code stdin.
    return {k: v for k, v in obj.items() if k != "__doc__"}


def _infer_env_for_lifecycle(lifecycle: str, fixture: dict[str, Any]) -> dict[str, str]:
    # PreToolUse-Bash hooks expect ``CC_BASH_COMMAND``. PermissionRequest
    # handlers also benefit from this when they read the env shortcut.
    if lifecycle not in {"pre_tool_use_bash", "permission_request"}:
        return {}
    tool_input = fixture.get("tool_input")
    if not isinstance(tool_input, dict):
        return {}
    command = tool_input.get("command")
    if not isinstance(command, str):
        return {}
    return {"CC_BASH_COMMAND": command}


def _check_stdout(text: str, invariants: ExpectedInvariants) -> tuple[bool, str]:
    if not text.strip():
        return True, ""
    if invariants.stdout_can_be_plain_text and invariants.stdout_json_schema is None:
        return True, ""
    try:
        obj = json.loads(text)
    except (ValueError, json.JSONDecodeError) as exc:
        return False, f"stdout is non-empty but not valid JSON: {exc}"
    if invariants.stdout_json_schema is None:
        return True, ""
    return _validate_schema(obj, invariants.stdout_json_schema)


def _validate_pre_tool_use_decision(obj: Any) -> tuple[bool, str]:
    # Shape: {"hookSpecificOutput": {"permissionDecision": "allow"|"deny"|"ask",
    #         "permissionDecisionReason"?: str}}
    if not isinstance(obj, dict):
        return False, "expected object at root"
    hook_specific = obj.get("hookSpecificOutput")
    if not isinstance(hook_specific, dict):
        return False, "missing hookSpecificOutput object"
    decision = hook_specific.get("permissionDecision")
    if decision not in {"allow", "deny", "ask"}:
        return False, f"permissionDecision must be allow/deny/ask, got {decision!r}"
    return True, ""


def _validate_permission_request_decision(obj: Any) -> tuple[bool, str]:
    # Shape: {"hookSpecificOutput": {"hookEventName": "PermissionRequest",
    #         "decision": {"behavior": "allow"|"deny", ...}}}
    if not isinstance(obj, dict):
        return False, "expected object at root"
    hook_specific = obj.get("hookSpecificOutput")
    if not isinstance(hook_specific, dict):
        return False, "missing hookSpecificOutput object"
    decision = hook_specific.get("decision")
    if not isinstance(decision, dict):
        return False, "missing hookSpecificOutput.decision object"
    behavior = decision.get("behavior")
    if behavior not in {"allow", "deny"}:
        return False, f"decision.behavior must be allow/deny, got {behavior!r}"
    return True, ""


def _validate_additional_context(obj: Any) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "expected object at root"
    if "additionalContext" not in obj:
        return False, "missing additionalContext key"
    if not isinstance(obj["additionalContext"], str):
        return False, "additionalContext must be a string"
    return True, ""


_SCHEMA_VALIDATORS = {
    "pre_tool_use_decision": _validate_pre_tool_use_decision,
    "permission_request_decision": _validate_permission_request_decision,
    "additional_context": _validate_additional_context,
}


def _validate_schema(obj: Any, schema: str) -> tuple[bool, str]:
    validator = _SCHEMA_VALIDATORS.get(schema)
    if validator is None:
        return False, f"unknown schema id: {schema}"
    return validator(obj)


def _check_stderr_clean(stderr: str) -> tuple[bool, str]:
    if _TRACEBACK_RE.search(stderr):
        return False, "stderr contains a Python traceback"
    if _UNHANDLED_ERROR_RE.search(stderr):
        return False, "stderr contains an unhandled-error signature"
    return True, ""


def _check_one_fixture(
    target: IntegrationTarget,
    fixture: dict[str, Any],
    tmp_root: Path,
) -> list[SmokeFailure]:
    stdin, env_overrides, argv, cwd_hint = parse_stdin_fixture(fixture)
    inferred = _infer_env_for_lifecycle(target.lifecycle, fixture)
    merged_env = {**inferred, **env_overrides}
    request_cwd = Path(cwd_hint) if cwd_hint else None

    request = RunRequest(
        script_path=target.script_path,
        argv=tuple(argv),
        stdin=stdin,
        env_overrides=merged_env,
        cwd=request_cwd,
        timeout=target.invariants.max_timeout_seconds,
    )
    result = run_script(request, tmp_root)

    failures: list[SmokeFailure] = []
    fixture_name = fixture.get("__name__", "<unknown>")
    if not isinstance(fixture_name, str):
        fixture_name = "<unknown>"

    if result.timed_out:
        failures.append(
            SmokeFailure(
                fixture_name=fixture_name,
                reason="timeout",
                detail=f"exceeded {target.invariants.max_timeout_seconds}s",
            ),
        )
        return failures

    if result.error is not None and not result.permission_denied:
        failures.append(
            SmokeFailure(
                fixture_name=fixture_name,
                reason="runner error",
                detail=result.error,
            ),
        )
        return failures

    if result.returncode not in target.invariants.exit_codes:
        failures.append(
            SmokeFailure(
                fixture_name=fixture_name,
                reason="exit code out of contract",
                detail=(
                    f"got {result.returncode}, allowed "
                    f"{sorted(target.invariants.exit_codes)}; "
                    f"stderr[0:200]={result.stderr[:200]!r}"
                ),
            ),
        )

    stdout_ok, stdout_reason = _check_stdout(result.stdout, target.invariants)
    if not stdout_ok:
        failures.append(
            SmokeFailure(
                fixture_name=fixture_name,
                reason="stdout contract violation",
                detail=f"{stdout_reason}; stdout[0:200]={result.stdout[:200]!r}",
            ),
        )

    stderr_ok, stderr_reason = _check_stderr_clean(result.stderr)
    if not stderr_ok:
        failures.append(
            SmokeFailure(
                fixture_name=fixture_name,
                reason="stderr contract violation",
                detail=f"{stderr_reason}; stderr[0:400]={result.stderr[:400]!r}",
            ),
        )

    return failures


def _format_failures(target: IntegrationTarget, failures: list[SmokeFailure]) -> str:
    lines: list[str] = [
        f"Integration regression failures for target '{target.label}':",
        f"  script: {target.script_path}",
        f"  lifecycle: {target.lifecycle}",
        f"  contract: {target.invariants}",
        f"  failing fixtures: {len({f.fixture_name for f in failures})}",
        "",
    ]
    by_reason: dict[str, list[SmokeFailure]] = {}
    for failure in failures:
        by_reason.setdefault(failure.reason, []).append(failure)
    for reason, group in sorted(by_reason.items()):
        lines.append(f"  [{reason}] x {len(group)}")
        for failure in group[:3]:
            lines.append(f"    fixture: {failure.fixture_name}")
            lines.append(f"      detail: {_truncate(failure.detail)}")
        if len(group) > 3:
            lines.append(f"    ... and {len(group) - 3} more")
    return "\n".join(lines)


def _truncate(text: str, limit: int = 400) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"... (truncated, total {len(text)} chars)"


@pytest.mark.integration
@pytest.mark.parametrize("target", INTEGRATION_TARGETS, ids=lambda t: t.label)
def test_smoke_regression(target: IntegrationTarget, tmp_path: Path) -> None:
    fixture_paths = _list_fixtures(target.lifecycle)
    if not fixture_paths:
        pytest.skip(f"no fixtures for lifecycle '{target.lifecycle}'")

    failures: list[SmokeFailure] = []
    for index, path in enumerate(fixture_paths):
        fixture = _load_fixture(path)
        if fixture is None:
            continue
        fixture_with_name = dict(fixture)
        fixture_with_name["__name__"] = path.name
        failures.extend(
            _check_one_fixture(
                target,
                fixture_with_name,
                tmp_path / f"run_{index}",
            ),
        )

    if failures:
        pytest.fail(_format_failures(target, failures))


# ---------------------------------------------------------------------------
# Layer 2 — hypothesis property tests against a small input space.
# ---------------------------------------------------------------------------


PROPERTY_SETTINGS = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


def _target_by_label(label: str) -> IntegrationTarget:
    for target in INTEGRATION_TARGETS:
        if target.label == label:
            return target
    msg = f"unknown integration target: {label}"
    raise KeyError(msg)


_SAFE_PATH_CHARS = st.characters(
    min_codepoint=0x20,
    max_codepoint=0x7E,
    blacklist_characters="'\"\\`",
)
_SAFE_PATH = st.text(_SAFE_PATH_CHARS, min_size=0, max_size=80)


_BASH_COMMAND_TEMPLATES = (
    "echo {}",
    "ls {}",
    "cat {}",
    "rm -rf {}",
    "rm {}",
    "git status",
    "git push origin master",
    "git reset --hard",
    "git rebase main",
    "go build ./...",
    "go fmt",
    "gofmt -w .",
    "pip install requests",
    "python -m venv .venv",
    "pytest -k {}",
    "mypy {}",
    "uv run pytest",
    "kubectl delete ns prod",
    "find / -name *.log",
    "rm -rf /tmp/{}",
    "ENV=prod {} ./script.sh",
    "cd /tmp && ls",
    'echo "$(cat /etc/passwd)"',
    "git commit --amend",
    "drop table users",
    "DROP DATABASE foo",
)


def _bash_commands() -> st.SearchStrategy[str]:
    return st.builds(
        lambda template, fragment: template.format(fragment) if "{}" in template else template,
        st.sampled_from(_BASH_COMMAND_TEMPLATES),
        _SAFE_PATH,
    )


def _bash_payload() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda cmd: {
            "tool_name": "Bash",
            "tool_input": {"command": cmd},
            "hook_event_name": "PreToolUse",
        },
        _bash_commands(),
    )


def _existing_write_payload() -> st.SearchStrategy[dict[str, object]]:
    return st.builds(
        lambda path, content: {
            "tool_name": "Write",
            "tool_input": {"file_path": path, "content": content},
            "hook_event_name": "PreToolUse",
        },
        st.sampled_from(
            [
                "/tmp/maybe.txt",
                "/nonexistent/path.txt",
                "/etc/hostname",
            ],
        ),
        st.text(min_size=0, max_size=80),
    )


def _run_target(
    target: IntegrationTarget,
    stdin: str,
    env_overrides: dict[str, str],
    tmp_root: Path,
) -> None:
    request = RunRequest(
        script_path=target.script_path,
        stdin=stdin,
        env_overrides=env_overrides,
        timeout=target.invariants.max_timeout_seconds,
    )
    result = run_script(request, tmp_root)
    assert not result.timed_out, f"hook timed out: {target.label}"
    assert result.error is None or result.permission_denied, (
        f"runner error for {target.label}: {result.error}"
    )
    assert result.returncode in target.invariants.exit_codes, (
        f"{target.label}: returncode {result.returncode} not in "
        f"{sorted(target.invariants.exit_codes)}; stderr={result.stderr[:200]!r}"
    )
    stdout_ok, stdout_reason = _check_stdout(result.stdout, target.invariants)
    assert stdout_ok, f"{target.label} stdout violation: {stdout_reason}"
    stderr_ok, stderr_reason = _check_stderr_clean(result.stderr)
    assert stderr_ok, f"{target.label} stderr violation: {stderr_reason}"


# Permanent regression: this @example used to expose a schema bug where
# pre_bash_safety_gate emitted PreToolUse-shape JSON
# (``hookSpecificOutput.permissionDecision``) when it should have emitted
# PermissionRequest-shape (``hookSpecificOutput.decision.behavior``). Fixed in
# ``hooks.write_permission_request_decision``. Retained as an @example so the
# property test always exercises this input even when the random draw misses it.
@example(
    payload={
        "tool_name": "Bash",
        "tool_input": {"command": "echo "},
        "hook_event_name": "PreToolUse",
    },
)
@pytest.mark.integration
@PROPERTY_SETTINGS
@given(payload=_bash_payload())
def test_pre_bash_safety_gate_property(payload: dict[str, object], tmp_path: Path) -> None:
    target = _target_by_label("pre_bash_safety_gate.bash")
    stdin = json.dumps(payload, ensure_ascii=False)
    env: dict[str, str] = {}
    tool_input = payload["tool_input"]
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            env["CC_BASH_COMMAND"] = command
    _run_target(target, stdin, env, tmp_path)


@pytest.mark.integration
@PROPERTY_SETTINGS
@given(payload=_existing_write_payload())
def test_pre_write_existing_guard_property(payload: dict[str, object], tmp_path: Path) -> None:
    target = _target_by_label("pre_write_existing_guard.write")
    stdin = json.dumps(payload, ensure_ascii=False)
    _run_target(target, stdin, {}, tmp_path)
