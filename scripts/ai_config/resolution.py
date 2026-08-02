from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from .core import Change, ChangeKind, FieldManifest, MissingValue, ReconciliationPlan
from .decisions import DecisionSet, DecisionSource
from .document import MutableConfiguration, assign_value, copy_path, snapshot_mapping
from .model import to_plain_value

if TYPE_CHECKING:
    from .model import FieldPath, SemanticSnapshot


class ResolutionError(ValueError):
    pass


class OperationMode(StrEnum):
    APPLY = "apply"
    RECONCILE = "reconcile"


@dataclass(frozen=True, slots=True)
class ResolvedDocuments:
    repository: MutableConfiguration
    live: MutableConfiguration
    applied_paths: tuple[FieldPath, ...]
    captured_paths: tuple[FieldPath, ...]
    required_decisions: tuple[FieldPath, ...]
    unknown_paths: tuple[FieldPath, ...]


def resolve_documents(
    *,
    plan: ReconciliationPlan,
    repository: SemanticSnapshot,
    resolved_repository: SemanticSnapshot,
    live: SemanticSnapshot,
    manifest: FieldManifest,
    mode: OperationMode,
    decisions: DecisionSet,
    live_exists: bool,
) -> ResolvedDocuments:
    repository_configuration = snapshot_mapping(repository)
    resolved_repository_configuration = snapshot_mapping(resolved_repository)
    live_configuration = snapshot_mapping(live)
    applied: list[FieldPath] = []
    captured: list[FieldPath] = []
    required: list[FieldPath] = []
    unknown: list[FieldPath] = []
    used_decisions: set[FieldPath] = set()

    for change in plan.changes:
        if change.kind is ChangeKind.UNKNOWN:
            unknown.append(change.path)
            continue
        if change.kind in {ChangeKind.UNCHANGED, ChangeKind.PRESERVE_LOCAL}:
            continue
        if _apply_merged_change(
            change,
            repository_configuration,
            live_configuration,
        ):
            applied.append(change.path)
            captured.append(change.path)
            continue
        source = _source_for_change(
            change.kind,
            change.path,
            mode=mode,
            decisions=decisions,
            live_exists=live_exists,
        )
        if source is None:
            required.append(change.path)
            continue
        if _requires_explicit_decision(change.kind, live_exists=live_exists):
            used_decisions.add(change.path)
        if source is DecisionSource.REPO:
            copy_path(resolved_repository_configuration, live_configuration, change.path)
            applied.append(change.path)
            continue
        rule = manifest.rule_for(change.path)
        if rule is not None and (rule.binding is not None or rule.secret):
            message = "bound or secret fields cannot be captured from live configuration"
            raise ResolutionError(message)
        copy_path(live_configuration, repository_configuration, change.path)
        captured.append(change.path)

    extra_decisions = {
        decision.path for decision in decisions.decisions if decision.path not in used_decisions
    }
    if extra_decisions:
        message = "decisions file contains paths that do not require a decision"
        raise ResolutionError(message)
    return ResolvedDocuments(
        repository=repository_configuration,
        live=live_configuration,
        applied_paths=tuple(applied),
        captured_paths=tuple(captured),
        required_decisions=tuple(required),
        unknown_paths=tuple(unknown),
    )


def _apply_merged_change(
    change: Change,
    repository: MutableConfiguration,
    live: MutableConfiguration,
) -> bool:
    if change.kind is not ChangeKind.MERGE:
        return False
    if change.merged is None or change.merged is MissingValue.MISSING:
        message = "merge changes require a merged value"
        raise ResolutionError(message)
    merged = to_plain_value(change.merged)
    assign_value(repository, change.path, merged)
    assign_value(live, change.path, merged)
    return True


def _source_for_change(
    kind: ChangeKind,
    path: FieldPath,
    *,
    mode: OperationMode,
    decisions: DecisionSet,
    live_exists: bool,
) -> DecisionSource | None:
    if kind is ChangeKind.APPLY_REPO:
        return DecisionSource.REPO
    if kind is ChangeKind.INITIALISATION_REQUIRED and not live_exists:
        return DecisionSource.REPO
    if mode is OperationMode.APPLY:
        return None
    return decisions.source_for(path)


def _requires_explicit_decision(kind: ChangeKind, *, live_exists: bool) -> bool:
    return kind in {ChangeKind.CAPTURE_LIVE, ChangeKind.CONFLICT} or (
        kind is ChangeKind.INITIALISATION_REQUIRED and live_exists
    )
