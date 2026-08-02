from __future__ import annotations

import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .adapters import (
    EngineAdapterSpec,
    EngineKind,
    EnginePaths,
    engine_adapter,
    parse_snapshot,
    resolve_engine_paths,
)
from .bindings import BindingProviders, resolve_snapshot_bindings
from .core import ChangeKind, FieldManifest, ReconciliationPlan, plan_reconciliation
from .document import (
    fingerprint_sensitive_fields,
    portable_projection,
    render_document,
    snapshot_mapping,
    validate_document,
)
from .manifest import parse_manifest
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
    manifest = parse_manifest(manifest_source)
    if manifest.engine != engine.value:
        message = f"manifest engine does not match requested engine: {engine.value}"
        raise OperationError(message)
    current_manifest_digest = digest_manifest_source(manifest_source)
    repository_source = paths.repository.read_bytes()
    repository = parse_snapshot(repository_source, adapter.configuration_format)
    active_providers = providers or BindingProviders.system(profile)
    resolved_repository = resolve_snapshot_bindings(repository, manifest, active_providers)
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
    active_providers = providers or BindingProviders.system(profile)
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
        engine=engine,
        profile=profile,
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
            engine=engine.value,
            state_directory=inspection.state_paths.root,
            writes=writes,
            expectations=expectations,
        )
        written_paths = tuple(file.target for file in result.files if file.changed)
    else:
        written_paths = ()
    return OperationResult(
        engine=engine,
        profile=profile,
        plan=inspection.plan,
        changed=bool(writes),
        check_mode=check,
        applied=len(resolved.applied_paths),
        captured=len(resolved.captured_paths),
        preserved=inspection.plan.count(ChangeKind.PRESERVE_LOCAL),
        state_initialised=inspection.base_state is None,
        written_paths=written_paths,
    )


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
