from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from .model import FieldPath, SemanticArray, SemanticSnapshot, SemanticValue


class FieldScope(StrEnum):
    SHARED = "shared"
    ENVIRONMENT = "environment"
    LOCAL_STATE = "local-state"
    RUNTIME = "runtime"


class ChangeKind(StrEnum):
    APPLY_REPO = "apply-repo"
    CAPTURE_LIVE = "capture-live"
    CONFLICT = "conflict"
    INITIALISATION_REQUIRED = "initialisation-required"
    MERGE = "merge"
    PRESERVE_LOCAL = "preserve-local"
    UNKNOWN = "unknown"
    UNCHANGED = "unchanged"


class MissingValue(StrEnum):
    MISSING = "missing"


type FieldValue = SemanticValue | MissingValue


class ManifestDefinitionError(ValueError):
    pass


class BindingProvider(StrEnum):
    PROFILE = "profile"
    ENVIRONMENT = "env"
    KEYCHAIN = "keychain"


class FieldStrategy(StrEnum):
    ATOMIC = "atomic"
    ORDERED_SET = "ordered-set"


@dataclass(frozen=True, slots=True)
class FieldBinding:
    provider: BindingProvider
    key: str

    def __post_init__(self) -> None:
        if not self.key:
            message = "field binding keys must not be empty"
            raise ManifestDefinitionError(message)


@dataclass(frozen=True, slots=True)
class FieldRule:
    path: FieldPath
    scope: FieldScope
    binding: FieldBinding | None = None
    secret: bool = False
    strategy: FieldStrategy = FieldStrategy.ATOMIC

    def __post_init__(self) -> None:
        if not self.path or any(not segment for segment in self.path):
            message = "field rule paths must contain non-empty segments"
            raise ManifestDefinitionError(message)
        if self.binding is not None and self.scope is not FieldScope.ENVIRONMENT:
            message = "field bindings require environment scope"
            raise ManifestDefinitionError(message)
        if self.scope is FieldScope.ENVIRONMENT and self.binding is None:
            message = "environment fields require a binding"
            raise ManifestDefinitionError(message)
        if self.secret and self.binding is None:
            message = "secret fields require a binding"
            raise ManifestDefinitionError(message)
        if self.strategy is FieldStrategy.ORDERED_SET and self.scope is not FieldScope.SHARED:
            message = "ordered-set strategy requires shared scope"
            raise ManifestDefinitionError(message)


@dataclass(frozen=True, slots=True)
class FieldManifest:
    rules: tuple[FieldRule, ...]
    schema_version: int = 1
    engine: str | None = None

    def __post_init__(self) -> None:
        paths = [rule.path for rule in self.rules]
        if len(paths) != len(set(paths)):
            message = "field rule paths must be unique"
            raise ManifestDefinitionError(message)

    def scope_for(self, path: FieldPath) -> FieldScope | None:
        rule = self.rule_for(path)
        return rule.scope if rule is not None else None

    def rule_for(self, path: FieldPath) -> FieldRule | None:
        matching_rules = [
            rule
            for rule in self.rules
            if len(rule.path) <= len(path) and path[: len(rule.path)] == rule.path
        ]
        if not matching_rules:
            return None
        return max(matching_rules, key=lambda rule: len(rule.path))


@dataclass(frozen=True, slots=True)
class Change:
    path: FieldPath
    kind: ChangeKind
    scope: FieldScope | None
    base: FieldValue
    repo: FieldValue
    live: FieldValue
    sensitive: bool
    merged: FieldValue | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationPlan:
    changes: tuple[Change, ...]

    def count(self, kind: ChangeKind) -> int:
        return sum(change.kind is kind for change in self.changes)

    def counts(self) -> dict[ChangeKind, int]:
        counted = Counter(change.kind for change in self.changes)
        return {kind: counted.get(kind, 0) for kind in ChangeKind}

    def is_converged(self) -> bool:
        converged_kinds = {ChangeKind.UNCHANGED, ChangeKind.PRESERVE_LOCAL}
        return all(change.kind in converged_kinds for change in self.changes)


def plan_reconciliation(
    *,
    base: SemanticSnapshot | None,
    repo: SemanticSnapshot,
    live: SemanticSnapshot,
    manifest: FieldManifest,
) -> ReconciliationPlan:
    base_fields = _field_values(base)
    repo_fields = _field_values(repo)
    live_fields = _field_values(live)
    paths = sorted(base_fields.keys() | repo_fields.keys() | live_fields.keys())
    changes = tuple(
        _plan_field(
            path=path,
            base_present=base is not None,
            base=base_fields.get(path, MissingValue.MISSING),
            repo=repo_fields.get(path, MissingValue.MISSING),
            live=live_fields.get(path, MissingValue.MISSING),
            rule=manifest.rule_for(path),
        )
        for path in paths
    )
    return ReconciliationPlan(changes=changes)


def _field_values(snapshot: SemanticSnapshot | None) -> dict[FieldPath, SemanticValue]:
    if snapshot is None:
        return {}
    return {field.path: field.value for field in snapshot.semantic_fields()}


def _plan_field(
    *,
    path: FieldPath,
    base_present: bool,
    base: FieldValue,
    repo: FieldValue,
    live: FieldValue,
    rule: FieldRule | None,
) -> Change:
    scope = rule.scope if rule is not None else None
    if scope is None:
        kind = ChangeKind.UNKNOWN
    elif scope in {FieldScope.LOCAL_STATE, FieldScope.RUNTIME}:
        kind = ChangeKind.PRESERVE_LOCAL
    elif repo == live:
        kind = ChangeKind.UNCHANGED
    elif rule is not None and rule.binding is not None:
        kind = ChangeKind.APPLY_REPO
    elif not base_present:
        kind = ChangeKind.INITIALISATION_REQUIRED
    elif rule is not None and rule.strategy is FieldStrategy.ORDERED_SET:
        kind, merged = _plan_ordered_set(base=base, repo=repo, live=live)
        return Change(
            path=path,
            kind=kind,
            scope=scope,
            base=base,
            repo=repo,
            live=live,
            sensitive=rule.secret,
            merged=merged,
        )
    elif repo == base:
        kind = ChangeKind.CAPTURE_LIVE
    elif live == base:
        kind = ChangeKind.APPLY_REPO
    else:
        kind = ChangeKind.CONFLICT
    return Change(
        path=path,
        kind=kind,
        scope=scope,
        base=base,
        repo=repo,
        live=live,
        sensitive=rule.secret if rule is not None else False,
    )


def _plan_ordered_set(
    *,
    base: FieldValue,
    repo: FieldValue,
    live: FieldValue,
) -> tuple[ChangeKind, SemanticArray]:
    base_items = _ordered_set_items(base)
    repo_items = _ordered_set_items(repo)
    live_items = _ordered_set_items(live)
    order = tuple(dict.fromkeys((*base_items, *repo_items, *live_items)))
    merged_items = tuple(
        item
        for item in order
        if _merge_membership(
            base=item in base_items,
            repo=item in repo_items,
            live=item in live_items,
        )
    )
    merged = SemanticArray(items=merged_items)
    if merged_items == repo_items:
        return ChangeKind.APPLY_REPO, merged
    if merged_items == live_items:
        return ChangeKind.CAPTURE_LIVE, merged
    return ChangeKind.MERGE, merged


def _ordered_set_items(value: FieldValue) -> tuple[SemanticValue, ...]:
    if value is MissingValue.MISSING:
        return ()
    if not isinstance(value, SemanticArray):
        message = "ordered-set fields must be arrays"
        raise ManifestDefinitionError(message)
    if len(value.items) != len(set(value.items)):
        message = "ordered-set fields must not contain duplicate values"
        raise ManifestDefinitionError(message)
    return value.items


def _merge_membership(*, base: bool, repo: bool, live: bool) -> bool:
    if repo == live:
        return repo
    if repo == base:
        return live
    return repo
