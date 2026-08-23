from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .adapters import EngineKind, load_engine_plan
from .bindings import BindingResolutionError
from .core import Change, MissingValue, ReconciliationPlan, plan_reconciliation
from .decisions import DecisionSet, DecisionSource, FieldDecision, load_decisions
from .manifest import ManifestError, load_manifest
from .model import SemanticSnapshot, SemanticValue, SnapshotError, to_plain_value
from .resolution import OperationMode, ResolutionError
from .service import (
    BootstrapAction,
    BootstrapResult,
    DecisionsRequiredError,
    EngineInspection,
    OperationResult,
    UnknownFieldsError,
    bootstrap_engine_from_live,
    inspect_engine,
    operate_engine,
)
from .state import StateError
from .transaction import TransactionError


@dataclass(frozen=True, slots=True)
class CommandArguments:
    command: str
    engine: EngineKind | None
    base: Path | None
    repo: Path | None
    live: Path | None
    manifest: Path | None
    repo_root: Path
    home: Path
    state_root: Path | None
    profile: str
    decisions: Path | None
    check: bool
    from_live: bool
    write: bool
    preview_token: str | None
    output_format: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-config",
        description=(
            "Inspect and reconcile repository-owned AI engine settings with one local home."
        ),
        epilog=(
            "Start with 'ai-config diff ENGINE'. Use 'bootstrap ENGINE --from-live' for a "
            "first live-derived baseline, 'apply' for non-interactive repository changes, "
            "and 'reconcile' when an existing baseline has a conflict."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("status", "diff"):
        command_parser = subparsers.add_parser(
            command,
            help=f"{command.capitalize()} semantic repository/live drift without writing",
            description=f"{command.capitalize()} semantic drift without writing any files.",
        )
        _add_engine_options(command_parser, engine_required=False)
        command_parser.add_argument(
            "--base",
            type=Path,
            help="Raw base snapshot for low-level explicit-file mode",
        )
        command_parser.add_argument(
            "--repo",
            type=Path,
            help="Repository JSON document for low-level explicit-file mode",
        )
        command_parser.add_argument(
            "--live",
            type=Path,
            help="Live JSON document for low-level explicit-file mode",
        )
        command_parser.add_argument(
            "--manifest",
            type=Path,
            help="Manifest for low-level explicit-file mode",
        )
        _add_output_options(command_parser)
    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply deterministic changes that require no choice",
        description=(
            "Apply repository-originated changes, safe initialisation, and deterministic "
            "ordered-set merges. Stop before writing when another change requires a choice or "
            "an unknown field requires classification."
        ),
    )
    _add_engine_options(apply_parser, engine_required=True)
    apply_parser.add_argument(
        "--check",
        action="store_true",
        help="Resolve and validate the operation without writing",
    )
    _add_output_options(apply_parser)
    reconcile_parser = subparsers.add_parser(
        "reconcile",
        help="Resolve live changes and conflicts with explicit decisions",
        description=(
            "Reconcile changes using a decisions file, or prompt for each required decision "
            "when stdin is an interactive terminal."
        ),
    )
    _add_engine_options(reconcile_parser, engine_required=True)
    reconcile_parser.add_argument(
        "--decisions",
        type=Path,
        help="JSON file choosing repo or live for paths that require a decision",
    )
    reconcile_parser.add_argument(
        "--check",
        action="store_true",
        help="Resolve and validate the operation without writing",
    )
    _add_output_options(reconcile_parser)
    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Create the first repository baseline from an existing live configuration",
        description=(
            "Preview a first-time live-to-repository bootstrap without writing. Portable live "
            "values are captured, repository-only values are retained, and local/runtime state "
            "is excluded. Re-run with --write and the emitted --preview-token after reviewing "
            "the plan; bootstrap never modifies the live configuration."
        ),
    )
    _add_engine_options(bootstrap_parser, engine_required=True)
    bootstrap_parser.add_argument(
        "--from-live",
        action="store_true",
        required=True,
        help="Use the current live configuration as the initial portable baseline",
    )
    bootstrap_parser.add_argument(
        "--write",
        action="store_true",
        help="Write the reviewed bootstrap plan; the default is a read-only preview",
    )
    bootstrap_parser.add_argument(
        "--preview-token",
        help="Token emitted by the exact bootstrap preview being approved for --write",
    )
    _add_output_options(bootstrap_parser)
    return parser


def _add_engine_options(parser: argparse.ArgumentParser, *, engine_required: bool) -> None:
    if engine_required:
        parser.add_argument(
            "engine",
            choices=tuple(EngineKind),
            help="Engine handled by this operation",
        )
    else:
        parser.add_argument(
            "engine",
            nargs="?",
            choices=tuple(EngineKind),
            help="Engine handle; omit only when using explicit-file mode",
        )
    parser.add_argument(
        "--repo-root",
        default=Path.cwd(),
        type=Path,
        help="devbox-setup repository root",
    )
    parser.add_argument(
        "--home",
        default=Path.home(),
        type=Path,
        help="Target home directory containing live engine configuration",
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        help="Override the profile-separated reconciliation state root",
    )
    parser.add_argument(
        "--profile",
        default=os.environ.get("MNEMOSYNE_PERISTASEOS", "default"),
        help="Environment profile used for state and bindings",
    )


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="Output representation",
    )
    parser.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="output_format",
        help="Shortcut for --format json",
    )


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    command_arguments = _command_arguments(parser.parse_args(arguments))
    try:
        if command_arguments.command in {"status", "diff"}:
            return _run_read_only(command_arguments)
        if command_arguments.command == "bootstrap":
            return _run_bootstrap(command_arguments)
        return _run_operation(command_arguments)
    except (
        BindingResolutionError,
        ManifestError,
        ResolutionError,
        SnapshotError,
        StateError,
        TransactionError,
        OSError,
        ValueError,
    ) as error:
        _print_error(error, command_arguments.output_format)
        return 2


def _command_arguments(namespace: argparse.Namespace) -> CommandArguments:
    raw_engine = cast("str | None", namespace.engine)
    return CommandArguments(
        command=cast("str", namespace.command),
        engine=EngineKind(raw_engine) if raw_engine is not None else None,
        base=cast("Path | None", getattr(namespace, "base", None)),
        repo=cast("Path | None", getattr(namespace, "repo", None)),
        live=cast("Path | None", getattr(namespace, "live", None)),
        manifest=cast("Path | None", getattr(namespace, "manifest", None)),
        repo_root=cast("Path", namespace.repo_root),
        home=cast("Path", namespace.home),
        state_root=cast("Path | None", namespace.state_root),
        profile=cast("str", namespace.profile),
        decisions=cast("Path | None", getattr(namespace, "decisions", None)),
        check=cast("bool", getattr(namespace, "check", False)),
        from_live=cast("bool", getattr(namespace, "from_live", False)),
        write=cast("bool", getattr(namespace, "write", False)),
        preview_token=cast("str | None", getattr(namespace, "preview_token", None)),
        output_format=cast("str", namespace.output_format),
    )


def _run_read_only(arguments: CommandArguments) -> int:
    inspection = _build_inspection(arguments)
    plan = inspection.plan if isinstance(inspection, EngineInspection) else inspection
    state_missing = isinstance(inspection, EngineInspection) and inspection.base_state is None
    converged = plan.is_converged() and not state_missing
    engine = arguments.engine
    if arguments.output_format == "json":
        output = (
            _status_json(plan, engine, arguments.profile, state_missing=state_missing)
            if arguments.command == "status"
            else _diff_json(plan, engine, arguments.profile, state_missing=state_missing)
        )
        print(json.dumps(output, indent=2, sort_keys=True))
    elif arguments.command == "status":
        _print_status(plan, state_missing=state_missing)
    else:
        _print_diff(plan)
    return 0 if converged else 1


def _build_inspection(arguments: CommandArguments) -> EngineInspection | ReconciliationPlan:
    if arguments.engine is not None and arguments.base is None:
        if any(path is not None for path in (arguments.repo, arguments.live, arguments.manifest)):
            message = "engine mode cannot be combined with --repo, --live, or --manifest"
            raise ValueError(message)
        return inspect_engine(
            arguments.engine,
            repo_root=arguments.repo_root,
            home=arguments.home,
            profile=arguments.profile,
            state_root=arguments.state_root,
        )
    return _build_explicit_plan(arguments)


def _build_explicit_plan(arguments: CommandArguments) -> ReconciliationPlan:
    if arguments.engine is not None:
        if any(path is not None for path in (arguments.repo, arguments.live, arguments.manifest)):
            message = "engine mode cannot be combined with --repo, --live, or --manifest"
            raise ValueError(message)
        return load_engine_plan(
            arguments.engine,
            repo_root=arguments.repo_root,
            home=arguments.home,
            base_path=arguments.base,
        )
    if arguments.repo is None or arguments.live is None or arguments.manifest is None:
        message = "specify an engine or all of --repo, --live, and --manifest"
        raise ValueError(message)
    base = SemanticSnapshot.from_json_file(arguments.base) if arguments.base is not None else None
    return plan_reconciliation(
        base=base,
        repo=SemanticSnapshot.from_json_file(arguments.repo),
        live=SemanticSnapshot.from_json_file(arguments.live),
        manifest=load_manifest(arguments.manifest),
    )


def _run_operation(arguments: CommandArguments) -> int:
    if arguments.engine is None:
        message = "apply and reconcile require an engine"
        raise ValueError(message)
    mode = OperationMode(arguments.command)
    decisions = load_decisions(arguments.decisions) if arguments.decisions else DecisionSet(())
    try:
        result = _operate(arguments, mode, decisions)
    except DecisionsRequiredError as error:
        if mode is OperationMode.RECONCILE and arguments.decisions is None and sys.stdin.isatty():
            interactive = _prompt_decisions(error)
            result = _operate(arguments, mode, interactive)
        else:
            _print_decisions_required(error, arguments.output_format)
            return 1
    except UnknownFieldsError as error:
        _print_unknown_fields(error, arguments.output_format)
        return 1
    _print_operation_result(result, arguments.output_format)
    return 0


def _run_bootstrap(arguments: CommandArguments) -> int:
    if arguments.engine is None or not arguments.from_live:
        message = "bootstrap requires an engine and --from-live"
        raise ValueError(message)
    try:
        result = bootstrap_engine_from_live(
            arguments.engine,
            repo_root=arguments.repo_root,
            home=arguments.home,
            profile=arguments.profile,
            state_root=arguments.state_root,
            write=arguments.write,
            preview_token=arguments.preview_token,
        )
    except UnknownFieldsError as error:
        _print_unknown_fields(error, arguments.output_format)
        return 1
    _print_bootstrap_result(result, arguments.output_format, write=arguments.write)
    return 0


def _operate(
    arguments: CommandArguments,
    mode: OperationMode,
    decisions: DecisionSet,
) -> OperationResult:
    if arguments.engine is None:
        message = "operation requires an engine"
        raise ValueError(message)
    return operate_engine(
        arguments.engine,
        repo_root=arguments.repo_root,
        home=arguments.home,
        profile=arguments.profile,
        state_root=arguments.state_root,
        mode=mode,
        decisions=decisions,
        check=arguments.check,
    )


def _prompt_decisions(error: DecisionsRequiredError) -> DecisionSet:
    decisions: list[FieldDecision] = []
    changes = {change.path: change for change in error.inspection.plan.changes}
    for path in error.paths:
        change = changes[path]
        prompt = f"{'.'.join(path)} ({change.kind.value}) [repo/live]: "
        while True:
            answer = input(prompt).strip().lower()
            try:
                source = DecisionSource(answer)
            except ValueError:
                print("Enter 'repo' or 'live'.", file=sys.stderr)
                continue
            decisions.append(FieldDecision(path=path, source=source))
            break
    return DecisionSet(tuple(decisions))


def _status_json(
    plan: ReconciliationPlan,
    engine: EngineKind | None,
    profile: str,
    *,
    state_missing: bool = False,
) -> dict[str, object]:
    converged = plan.is_converged() and not state_missing
    return {
        "schema_version": 1,
        "engine": engine.value if engine is not None else None,
        "profile": profile,
        "converged": converged,
        "changed": not converged,
        "state_initialisation_required": state_missing,
        "counts": {kind.value: count for kind, count in plan.counts().items()},
    }


def _diff_json(
    plan: ReconciliationPlan,
    engine: EngineKind | None,
    profile: str,
    *,
    state_missing: bool = False,
) -> dict[str, object]:
    converged = plan.is_converged() and not state_missing
    return {
        "schema_version": 1,
        "engine": engine.value if engine is not None else None,
        "profile": profile,
        "converged": converged,
        "changed": not converged,
        "state_initialisation_required": state_missing,
        "changes": [_change_json(change) for change in plan.changes],
    }


def _change_json(change: Change) -> dict[str, object]:
    values = {
        "base": _field_value_json(change.base),
        "repo": _field_value_json(change.repo),
        "live": _field_value_json(change.live),
    }
    if change.sensitive:
        values = dict.fromkeys(values, "<redacted>")
    return {
        "path": list(change.path),
        "kind": change.kind.value,
        "scope": change.scope.value if change.scope is not None else None,
        **values,
    }


def _field_value_json(value: SemanticValue | MissingValue) -> object:
    if value is MissingValue.MISSING:
        return {"missing": True}
    return to_plain_value(value)


def _operation_json(result: OperationResult) -> dict[str, object]:
    converged = not result.check_mode or not result.changed
    return {
        "schema_version": 1,
        "engine": result.engine.value,
        "profile": result.profile,
        "changed": result.changed,
        "check_mode": result.check_mode,
        "converged": converged,
        "applied": result.applied,
        "captured": result.captured,
        "preserved": result.preserved,
        "unknown": 0,
        "conflicts": 0,
        "initialisation_required": 0,
        "state_initialised": result.state_initialised,
    }


def _bootstrap_json(result: BootstrapResult, *, write: bool) -> dict[str, object]:
    counts = {
        action.value: sum(change.action is action for change in result.changes)
        for action in BootstrapAction
    }
    operation = result.operation
    return {
        "schema_version": 1,
        "engine": operation.engine.value,
        "profile": operation.profile,
        "source": "live",
        "write": write,
        "changed": operation.changed,
        "check_mode": operation.check_mode,
        "state_initialised": operation.state_initialised,
        "preview_token": result.preview_token,
        "counts": counts,
        "changes": [
            {"action": change.action.value, "path": list(change.path)} for change in result.changes
        ],
        "written_paths": [str(path) for path in operation.written_paths],
    }


def _print_operation_result(result: OperationResult, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_operation_json(result), indent=2, sort_keys=True))
        return
    state = (
        "would change"
        if result.check_mode and result.changed
        else ("changed" if result.changed else "unchanged")
    )
    print(
        f"{result.engine.value}: {state} "
        f"applied={result.applied} captured={result.captured} preserved={result.preserved}"
    )


def _print_bootstrap_result(
    result: BootstrapResult,
    output_format: str,
    *,
    write: bool,
) -> None:
    if output_format == "json":
        print(json.dumps(_bootstrap_json(result, write=write), indent=2, sort_keys=True))
        return
    for change in result.changes:
        print(f"{change.action.value}\t{'.'.join(change.path)}")
    counts = " ".join(
        f"{action.value}={sum(change.action is action for change in result.changes)}"
        for action in BootstrapAction
    )
    state = "written" if write else "preview"
    print(f"{result.operation.engine.value}: bootstrap {state} {counts}")
    print(f"preview-token\t{result.preview_token}")
    for path in result.operation.written_paths:
        print(f"written\t{path}")
    if not write:
        print(
            "No files were written. Re-run with --write --preview-token TOKEN after reviewing "
            "this plan.",
            file=sys.stderr,
        )


def _print_decisions_required(error: DecisionsRequiredError, output_format: str) -> None:
    if output_format == "json":
        output = _status_json(
            error.inspection.plan,
            error.inspection.engine,
            error.inspection.profile,
            state_missing=error.inspection.base_state is None,
        )
        output["requires_decisions"] = True
        output["decision_paths"] = [list(path) for path in error.paths]
        print(json.dumps(output, indent=2, sort_keys=True))
        return
    print(str(error), file=sys.stderr)
    for path in error.paths:
        print(f"  {'.'.join(path)}", file=sys.stderr)


def _print_unknown_fields(error: UnknownFieldsError, output_format: str) -> None:
    if output_format == "json":
        output = _status_json(
            error.inspection.plan,
            error.inspection.engine,
            error.inspection.profile,
            state_missing=error.inspection.base_state is None,
        )
        output["unknown_paths"] = [list(path) for path in error.paths]
        print(json.dumps(output, indent=2, sort_keys=True))
        return
    print(str(error), file=sys.stderr)
    for path in error.paths:
        print(f"  {'.'.join(path)}", file=sys.stderr)


def _print_error(error: Exception, output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "error": type(error).__name__,
                    "message": str(error),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    print(str(error), file=sys.stderr)


def _print_status(plan: ReconciliationPlan, *, state_missing: bool) -> None:
    state = "converged" if plan.is_converged() and not state_missing else "drift"
    counts = " ".join(f"{kind.value}={count}" for kind, count in plan.counts().items() if count > 0)
    if state_missing:
        counts = f"{counts} state-initialisation-required=1".strip()
    print(f"{state} {counts}".rstrip())


def _print_diff(plan: ReconciliationPlan) -> None:
    for change in plan.changes:
        path = ".".join(change.path)
        print(f"{change.kind.value}\t{path}")
