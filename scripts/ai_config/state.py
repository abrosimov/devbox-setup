from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from .document import snapshot_mapping
from .model import SemanticSnapshot, SnapshotError

if TYPE_CHECKING:
    from pathlib import Path

    from .adapters import EngineKind

STATE_SCHEMA_VERSION = 1
_PROFILE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


class StateError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EngineStatePaths:
    root: Path
    base: Path
    lock: Path
    journal: Path
    backups: Path


@dataclass(frozen=True, slots=True)
class BaseState:
    engine: EngineKind
    profile: str
    manifest_digest: str
    snapshot: SemanticSnapshot


def resolve_state_paths(
    engine: EngineKind,
    *,
    profile: str,
    home: Path,
    state_root: Path | None,
) -> EngineStatePaths:
    if not _PROFILE_NAME.fullmatch(profile):
        message = "profile names may contain only letters, digits, underscore, and hyphen"
        raise StateError(message)
    root = (
        (state_root if state_root is not None else home / ".local/state/devbox-setup/ai-config")
        / engine.value
        / profile
    )
    return EngineStatePaths(
        root=root,
        base=root / "base.json",
        lock=root / f"{engine.value}.lock",
        journal=root / f"{engine.value}.journal.json",
        backups=root / "backups",
    )


def digest_manifest(path: Path) -> str:
    try:
        source = path.read_bytes()
    except OSError as error:
        message = f"cannot read manifest: {path}"
        raise StateError(message) from error
    return digest_manifest_source(source)


def digest_manifest_source(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def load_base_state(
    path: Path,
    *,
    engine: EngineKind,
    profile: str,
    manifest_digest: str,
) -> BaseState | None:
    if not path.exists():
        return None
    try:
        source = path.read_bytes()
    except OSError as error:
        message = f"invalid base state: {path}"
        raise StateError(message) from error
    return parse_base_state(
        source,
        engine=engine,
        profile=profile,
        manifest_digest=manifest_digest,
    )


def parse_base_state(
    source: bytes,
    *,
    engine: EngineKind,
    profile: str,
    manifest_digest: str,
) -> BaseState | None:
    try:
        loaded: object = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        message = "invalid base state"
        raise StateError(message) from error
    if not isinstance(loaded, dict):
        message = "base state root must be an object"
        raise StateError(message)
    record = cast("dict[object, object]", loaded)
    if not _metadata_matches(
        record,
        engine=engine,
        profile=profile,
        manifest_digest=manifest_digest,
    ):
        return None
    snapshot_value = record.get("snapshot")
    try:
        snapshot = SemanticSnapshot.from_value(snapshot_value)
    except SnapshotError as error:
        message = "base state snapshot is invalid"
        raise StateError(message) from error
    return BaseState(
        engine=engine,
        profile=profile,
        manifest_digest=manifest_digest,
        snapshot=snapshot,
    )


def render_base_state(state: BaseState) -> bytes:
    value = {
        "schema_version": STATE_SCHEMA_VERSION,
        "engine": state.engine.value,
        "profile": state.profile,
        "manifest_digest": state.manifest_digest,
        "snapshot": snapshot_mapping(state.snapshot),
    }
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def validate_base_state(candidate: bytes) -> None:
    try:
        loaded: object = json.loads(candidate)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        message = "base state must be valid UTF-8 JSON"
        raise StateError(message) from error
    if not isinstance(loaded, dict):
        message = "base state root must be an object"
        raise StateError(message)
    record = cast("dict[object, object]", loaded)
    if not _supported_schema(record.get("schema_version")):
        message = "unsupported base state schema"
        raise StateError(message)
    SemanticSnapshot.from_value(record.get("snapshot"))


def _metadata_matches(
    record: dict[object, object],
    *,
    engine: EngineKind,
    profile: str,
    manifest_digest: str,
) -> bool:
    if not _supported_schema(record.get("schema_version")):
        message = "unsupported base state schema"
        raise StateError(message)
    if record.get("engine") != engine.value:
        message = "base state belongs to another engine"
        raise StateError(message)
    if record.get("profile") != profile:
        message = "base state belongs to another profile"
        raise StateError(message)
    return record.get("manifest_digest") == manifest_digest


def _supported_schema(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == STATE_SCHEMA_VERSION
