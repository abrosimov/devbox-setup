from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from .adapters import (
    EngineAdapterSpec,
    EngineKind,
    EnginePaths,
    engine_adapter,
    parse_engine_manifest,
    parse_snapshot,
    resolve_engine_paths,
)
from .bindings import BindingProviders, resolve_snapshot_bindings
from .core import (
    ChangeKind,
    FieldManifest,
    FieldScope,
    MissingValue,
    ReconciliationPlan,
    plan_reconciliation,
)
from .document import (
    copy_path,
    fingerprint_sensitive_fields,
    portable_projection,
    render_document,
    snapshot_mapping,
    validate_document,
)
from .model import FieldPath, SemanticSnapshot
from .resolution import OperationMode, resolve_documents
from .state import (
    BaseState,
    EngineStatePaths,
    digest_manifest_source,
    parse_base_state,
    render_base_state,
    resolve_state_paths,
    validate_base_state,
)
from .transaction import FileExpectation, FileWrite, write_validated_files

if TYPE_CHECKING:
    from pathlib import Path

    from .decisions import DecisionSet
    from .transaction import BytesValidator


class OperationError(ValueError):
    pass


class BootstrapError(OperationError):
    pass


class DecisionsRequiredError(OperationError):
    def __init__(self, inspection: EngineInspection, paths: tuple[FieldPath, ...]) -> None:
        self.inspection = inspection
        self.paths = paths
        message = "reconciliation requires explicit field decisions"
        super().__init__(message)


class UnknownFieldsError(OperationError):
    def __init__(self, inspection: EngineInspection, paths: tuple[FieldPath, ...]) -> None:
        self.inspection = inspection
        self.paths = paths
        message = "unknown fields block configuration writes"
        super().__init__(message)


class BootstrapAction(StrEnum):
    CAPTURE = "capture"
    KEEP_REPO = "keep-repo"
    PRESERVE_LOCAL = "preserve-local"
    IGNORE_RUNTIME = "ignore-runtime"


@dataclass(frozen=True, slots=True)
class BootstrapChange:
    path: FieldPath
    action: BootstrapAction


@dataclass(frozen=True, slots=True)
class EngineInspection:
    engine: EngineKind
    profile: str
    adapter: EngineAdapterSpec
    paths: EnginePaths
    state_paths: EngineStatePaths
    manifest: FieldManifest
    manifest_digest: str
    repository: SemanticSnapshot
    repository_source: bytes
    resolved_repository: SemanticSnapshot
    live: SemanticSnapshot
    live_source: bytes | None
    live_exists: bool
    base_state: BaseState | None
    base_source: bytes | None
    manifest_source: bytes
    plan: ReconciliationPlan


@dataclass(frozen=True, slots=True)
class OperationResult:
    engine: EngineKind
    profile: str
    plan: ReconciliationPlan
    changed: bool
    check_mode: bool
    applied: int
    captured: int
    preserved: int
    state_initialised: bool
    written_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    changes: tuple[BootstrapChange, ...]
    operation: OperationResult
    preview_token: str


@dataclass(frozen=True, slots=True)
class _FormatValidator:
    adapter: EngineAdapterSpec

    def __call__(self, candidate: bytes, /) -> None:
        validate_document(candidate, self.adapter.configuration_format)


def inspect_engine(
    engine: EngineKind,
    *,
    repo_root: Path,
    home: Path,
    profile: str,
    state_root: Path | None = None,
    providers: BindingProviders | None = None,
) -> EngineInspection:
    adapter = engine_adapter(engine)
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    state_paths = resolve_state_paths(
        engine,
        profile=profile,
        home=home,
        state_root=state_root,
    )
    manifest_source = paths.manifest.read_bytes()
    declared_manifest = parse_engine_manifest(engine, manifest_source)
    if declared_manifest.engine != engine.value:
        message = f"manifest engine does not match requested engine: {engine.value}"
        raise OperationError(message)
    current_manifest_digest = digest_manifest_source(manifest_source)
    repository_source = paths.repository.read_bytes()
    repository = parse_snapshot(repository_source, adapter.configuration_format)
    live_source = _read_optional_bytes(paths.live)
    live_exists = live_source is not None
    live = (
        parse_snapshot(live_source, adapter.configuration_format)
        if live_source is not None
        else SemanticSnapshot.from_value({})
    )
    base_source = _read_optional_bytes(state_paths.base)
    base_state = (
        parse_base_state(
            base_source,
            engine=engine,
            profile=profile,
            manifest_digest=current_manifest_digest,
        )
        if base_source is not None
        else None
    )
    runtime_snapshots = (live,) if base_state is None else (base_state.snapshot, live)
    manifest = parse_engine_manifest(
        engine,
        manifest_source,
        runtime_snapshots=runtime_snapshots,
    )
    active_providers = providers or BindingProviders.system(profile, paths.home)
    resolved_repository = resolve_snapshot_bindings(repository, manifest, active_providers)
    comparable_repository = fingerprint_sensitive_fields(resolved_repository, manifest)
    comparable_live = fingerprint_sensitive_fields(live, manifest)
    plan = plan_reconciliation(
        base=base_state.snapshot if base_state is not None else None,
        repo=comparable_repository,
        live=comparable_live,
        manifest=manifest,
    )
    return EngineInspection(
        engine=engine,
        profile=profile,
        adapter=adapter,
        paths=paths,
        state_paths=state_paths,
        manifest=manifest,
        manifest_digest=current_manifest_digest,
        repository=repository,
        repository_source=repository_source,
        resolved_repository=resolved_repository,
        live=live,
        live_source=live_source,
        live_exists=live_exists,
        base_state=base_state,
        base_source=base_source,
        manifest_source=manifest_source,
        plan=plan,
    )


def operate_engine(
    engine: EngineKind,
    *,
    repo_root: Path,
    home: Path,
    profile: str,
    mode: OperationMode,
    decisions: DecisionSet,
    check: bool,
    state_root: Path | None = None,
    providers: BindingProviders | None = None,
) -> OperationResult:
    inspection = inspect_engine(
        engine,
        repo_root=repo_root,
        home=home,
        profile=profile,
        state_root=state_root,
        providers=providers,
    )
    return _operate_inspection(
        inspection,
        mode=mode,
        decisions=decisions,
        check=check,
        providers=providers,
    )


def bootstrap_engine_from_live(
    engine: EngineKind,
    *,
    repo_root: Path,
    home: Path,
    profile: str,
    write: bool,
    preview_token: str | None = None,
    state_root: Path | None = None,
    providers: BindingProviders | None = None,
) -> BootstrapResult:
    inspection = inspect_engine(
        engine,
        repo_root=repo_root,
        home=home,
        profile=profile,
        state_root=state_root,
        providers=providers,
    )
    current_preview_token = _bootstrap_preview_token(inspection)
    if write and preview_token is None:
        message = "bootstrap --write requires the preview token from a reviewed preview"
        raise BootstrapError(message)
    if write and preview_token != current_preview_token:
        message = "bootstrap inputs changed after preview; review a new preview before writing"
        raise BootstrapError(message)
    if inspection.base_source is not None:
        message = "bootstrap requires an uninitialised engine state; base state already exists"
        raise BootstrapError(message)
    if not inspection.live_exists:
        message = "live configuration is required for --from-live bootstrap"
        raise BootstrapError(message)
    unknown_paths = tuple(
        change.path for change in inspection.plan.changes if change.kind is ChangeKind.UNKNOWN
    )
    if unknown_paths:
        raise UnknownFieldsError(inspection, unknown_paths)
    changes = _build_live_bootstrap_plan(inspection)
    operation = _bootstrap_from_live(
        inspection,
        check=not write,
        changes=changes,
    )
    return BootstrapResult(
        changes=changes,
        operation=operation,
        preview_token=current_preview_token,
    )


def _bootstrap_preview_token(inspection: EngineInspection) -> str:
    resolved_repository = json.dumps(
        snapshot_mapping(inspection.resolved_repository),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    inputs = {
        "schema_version": 1,
        "engine": inspection.engine.value,
        "profile": inspection.profile,
        "repository_path": str(inspection.paths.repository.absolute()),
        "live_path": str(inspection.paths.live.absolute()),
        "manifest_path": str(inspection.paths.manifest.absolute()),
        "base_path": str(inspection.state_paths.base.absolute()),
        "repository": _source_digest(inspection.repository_source),
        "live": _source_digest(inspection.live_source),
        "manifest": _source_digest(inspection.manifest_source),
        "base": _source_digest(inspection.base_source),
        "resolved_repository": _source_digest(resolved_repository),
    }
    canonical = json.dumps(inputs, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _source_digest(source: bytes | None) -> str | None:
    return hashlib.sha256(source).hexdigest() if source is not None else None


def _operate_inspection(
    inspection: EngineInspection,
    *,
    mode: OperationMode,
    decisions: DecisionSet,
    check: bool,
    providers: BindingProviders | None,
) -> OperationResult:
    unknown_paths = tuple(
        change.path for change in inspection.plan.changes if change.kind is ChangeKind.UNKNOWN
    )
    if unknown_paths:
        raise UnknownFieldsError(inspection, unknown_paths)
    resolved = resolve_documents(
        plan=inspection.plan,
        repository=inspection.repository,
        resolved_repository=inspection.resolved_repository,
        live=inspection.live,
        manifest=inspection.manifest,
        mode=mode,
        decisions=decisions,
        live_exists=inspection.live_exists,
    )
    if resolved.required_decisions:
        raise DecisionsRequiredError(inspection, resolved.required_decisions)

    repository = SemanticSnapshot.from_value(resolved.repository)
    active_providers = providers or BindingProviders.system(
        inspection.profile,
        inspection.paths.home,
    )
    resolved_repository = resolve_snapshot_bindings(
        repository,
        inspection.manifest,
        active_providers,
    )
    live = SemanticSnapshot.from_value(resolved.live)
    comparable_repository = fingerprint_sensitive_fields(
        resolved_repository,
        inspection.manifest,
    )
    comparable_live = fingerprint_sensitive_fields(live, inspection.manifest)
    repo_portable = portable_projection(comparable_repository, inspection.manifest)
    live_portable = portable_projection(comparable_live, inspection.manifest)
    if repo_portable != live_portable:
        message = "resolved documents do not converge"
        raise OperationError(message)

    repository_changed = repository != inspection.repository or not _mode_matches(
        inspection.paths.repository,
        inspection.adapter.repository_mode,
    )
    live_changed = (
        live != inspection.live
        or not inspection.live_exists
        or not _mode_matches(inspection.paths.live, inspection.adapter.live_mode)
    )
    base_state = BaseState(
        engine=inspection.engine,
        profile=inspection.profile,
        manifest_digest=inspection.manifest_digest,
        snapshot=live_portable,
    )
    base_changed = inspection.base_state != base_state or not _mode_matches(
        inspection.state_paths.base,
        0o600,
    )
    writes = _build_writes(
        inspection=inspection,
        repository=repository,
        live=live,
        base_state=base_state,
        repository_changed=repository_changed,
        live_changed=live_changed,
        base_changed=base_changed,
    )
    expectations = _build_expectations(inspection, writes)
    if writes and not check:
        result = write_validated_files(
            engine=inspection.engine.value,
            state_directory=inspection.state_paths.root,
            writes=writes,
            expectations=expectations,
        )
        written_paths = tuple(file.target for file in result.files if file.changed)
    else:
        written_paths = ()
    return OperationResult(
        engine=inspection.engine,
        profile=inspection.profile,
        plan=inspection.plan,
        changed=bool(writes),
        check_mode=check,
        applied=len(resolved.applied_paths),
        captured=len(resolved.captured_paths),
        preserved=inspection.plan.count(ChangeKind.PRESERVE_LOCAL),
        state_initialised=inspection.base_state is None,
        written_paths=written_paths,
    )


def _build_live_bootstrap_plan(inspection: EngineInspection) -> tuple[BootstrapChange, ...]:
    changes: list[BootstrapChange] = []
    for change in inspection.plan.changes:
        if change.kind is ChangeKind.UNCHANGED:
            continue
        if change.kind is ChangeKind.PRESERVE_LOCAL:
            action = (
                BootstrapAction.IGNORE_RUNTIME
                if change.scope is FieldScope.RUNTIME
                else BootstrapAction.PRESERVE_LOCAL
            )
        elif change.kind is ChangeKind.APPLY_REPO:
            action = BootstrapAction.KEEP_REPO
        elif change.kind is ChangeKind.INITIALISATION_REQUIRED:
            action = (
                BootstrapAction.KEEP_REPO
                if change.live is MissingValue.MISSING
                else BootstrapAction.CAPTURE
            )
        else:
            message = f"invalid change during live bootstrap: {change.kind.value}"
            raise BootstrapError(message)
        changes.append(BootstrapChange(path=change.path, action=action))
    return tuple(changes)


def _bootstrap_from_live(
    inspection: EngineInspection,
    *,
    check: bool,
    changes: tuple[BootstrapChange, ...],
) -> OperationResult:
    repository_configuration = snapshot_mapping(inspection.repository)
    live_configuration = snapshot_mapping(inspection.live)
    captured_paths = tuple(
        change.path for change in changes if change.action is BootstrapAction.CAPTURE
    )
    for path in captured_paths:
        copy_path(live_configuration, repository_configuration, path)
    repository = SemanticSnapshot.from_value(repository_configuration)
    live_portable = portable_projection(
        fingerprint_sensitive_fields(inspection.live, inspection.manifest),
        inspection.manifest,
    )
    base_state = BaseState(
        engine=inspection.engine,
        profile=inspection.profile,
        manifest_digest=inspection.manifest_digest,
        snapshot=live_portable,
    )
    repository_changed = repository != inspection.repository or not _mode_matches(
        inspection.paths.repository,
        inspection.adapter.repository_mode,
    )
    writes = _build_bootstrap_writes(
        inspection=inspection,
        repository=repository,
        base_state=base_state,
        repository_changed=repository_changed,
    )
    expectations = _build_expectations(inspection, writes)
    if writes and not check:
        result = write_validated_files(
            engine=inspection.engine.value,
            state_directory=inspection.state_paths.root,
            writes=writes,
            expectations=expectations,
        )
        written_paths = tuple(file.target for file in result.files if file.changed)
    else:
        written_paths = ()
    return OperationResult(
        engine=inspection.engine,
        profile=inspection.profile,
        plan=inspection.plan,
        changed=bool(writes),
        check_mode=check,
        applied=0,
        captured=len(captured_paths),
        preserved=inspection.plan.count(ChangeKind.PRESERVE_LOCAL),
        state_initialised=True,
        written_paths=written_paths,
    )


def _build_bootstrap_writes(
    *,
    inspection: EngineInspection,
    repository: SemanticSnapshot,
    base_state: BaseState,
    repository_changed: bool,
) -> tuple[FileWrite, ...]:
    writes: list[FileWrite] = []
    if repository_changed:
        writes.append(
            FileWrite(
                target=inspection.paths.repository,
                candidate=render_document(
                    snapshot_mapping(repository),
                    inspection.adapter.configuration_format,
                    source=inspection.repository_source,
                ),
                validate=_FormatValidator(inspection.adapter),
                mode=inspection.adapter.repository_mode,
                expected=inspection.repository_source,
            )
        )
    writes.append(
        FileWrite(
            target=inspection.state_paths.base,
            candidate=render_base_state(base_state),
            validate=validate_base_state,
            mode=0o600,
            expected=None,
        )
    )
    return tuple(writes)


def _build_writes(
    *,
    inspection: EngineInspection,
    repository: SemanticSnapshot,
    live: SemanticSnapshot,
    base_state: BaseState,
    repository_changed: bool,
    live_changed: bool,
    base_changed: bool,
) -> tuple[FileWrite, ...]:
    writes: list[FileWrite] = []
    validator: BytesValidator = _FormatValidator(inspection.adapter)
    if repository_changed:
        writes.append(
            FileWrite(
                target=inspection.paths.repository,
                candidate=render_document(
                    snapshot_mapping(repository),
                    inspection.adapter.configuration_format,
                    source=inspection.repository_source,
                ),
                validate=validator,
                mode=inspection.adapter.repository_mode,
                expected=inspection.repository_source,
            )
        )
    if live_changed:
        writes.append(
            FileWrite(
                target=inspection.paths.live,
                candidate=render_document(
                    snapshot_mapping(live),
                    inspection.adapter.configuration_format,
                    source=inspection.live_source,
                ),
                validate=validator,
                mode=inspection.adapter.live_mode,
                expected=inspection.live_source,
            )
        )
    if base_changed:
        writes.append(
            FileWrite(
                target=inspection.state_paths.base,
                candidate=render_base_state(base_state),
                validate=validate_base_state,
                mode=0o600,
                expected=(inspection.base_source),
            )
        )
    return tuple(writes)


def _build_expectations(
    inspection: EngineInspection,
    writes: tuple[FileWrite, ...],
) -> tuple[FileExpectation, ...]:
    written_paths = {write.target.absolute() for write in writes}
    sources = (
        (inspection.paths.repository, inspection.repository_source),
        (inspection.paths.live, inspection.live_source),
        (inspection.state_paths.base, inspection.base_source),
        (inspection.paths.manifest, inspection.manifest_source),
    )
    return tuple(
        FileExpectation(target=path, expected=source)
        for path, source in sources
        if path.absolute() not in written_paths
    )


def _read_optional_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _mode_matches(path: Path, expected: int) -> bool:
    return path.exists() and stat.S_IMODE(path.stat().st_mode) == expected
