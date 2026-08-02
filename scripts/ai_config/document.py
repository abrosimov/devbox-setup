from __future__ import annotations

import hashlib
import json
import re
import tomllib
from typing import cast

from .adapters import ConfigurationFormat
from .core import FieldManifest, FieldScope, MissingValue
from .model import FieldPath, SemanticSnapshot, SnapshotError, to_plain_value

type MutableConfiguration = dict[str, object]

_BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def snapshot_mapping(snapshot: SemanticSnapshot) -> MutableConfiguration:
    value = to_plain_value(snapshot.root)
    return cast("MutableConfiguration", value)


def value_at(configuration: MutableConfiguration, path: FieldPath) -> object | MissingValue:
    current: object = configuration
    for segment in path:
        if not isinstance(current, dict):
            return MissingValue.MISSING
        mapping = cast("dict[object, object]", current)
        if segment not in mapping:
            return MissingValue.MISSING
        current = mapping[segment]
    return current


def assign_value(configuration: MutableConfiguration, path: FieldPath, value: object) -> None:
    current = configuration
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            new_child: MutableConfiguration = {}
            current[segment] = new_child
            current = new_child
        else:
            current = cast("MutableConfiguration", child)
    current[path[-1]] = value


def remove_value(configuration: MutableConfiguration, path: FieldPath) -> None:
    parents: list[tuple[MutableConfiguration, str]] = []
    current = configuration
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            return
        parents.append((current, segment))
        current = cast("MutableConfiguration", child)
    current.pop(path[-1], None)
    for parent, segment in reversed(parents):
        child = parent.get(segment)
        if isinstance(child, dict) and not child:
            parent.pop(segment)
        else:
            break


def copy_path(
    source: MutableConfiguration,
    destination: MutableConfiguration,
    path: FieldPath,
) -> None:
    value = value_at(source, path)
    if value is MissingValue.MISSING:
        remove_value(destination, path)
    else:
        assign_value(destination, path, value)


def portable_projection(
    snapshot: SemanticSnapshot,
    manifest: FieldManifest,
) -> SemanticSnapshot:
    source = snapshot_mapping(snapshot)
    projection: MutableConfiguration = {}
    portable_scopes = {FieldScope.SHARED, FieldScope.ENVIRONMENT}
    for field in snapshot.semantic_fields():
        if manifest.scope_for(field.path) in portable_scopes:
            copy_path(source, projection, field.path)
    return SemanticSnapshot.from_value(projection)


def fingerprint_sensitive_fields(
    snapshot: SemanticSnapshot,
    manifest: FieldManifest,
) -> SemanticSnapshot:
    configuration = snapshot_mapping(snapshot)
    for field in snapshot.semantic_fields():
        rule = manifest.rule_for(field.path)
        if rule is not None and rule.secret:
            canonical = json.dumps(
                to_plain_value(field.value),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
            digest = hashlib.sha256(canonical).hexdigest()
            assign_value(configuration, field.path, f"sha256:{digest}")
    return SemanticSnapshot.from_value(configuration)


def render_document(
    configuration: MutableConfiguration,
    configuration_format: ConfigurationFormat,
) -> bytes:
    if configuration_format is ConfigurationFormat.JSON:
        return (
            json.dumps(configuration, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
    return _render_toml(configuration).encode()


def validate_document(candidate: bytes, configuration_format: ConfigurationFormat) -> None:
    try:
        source = candidate.decode()
    except UnicodeDecodeError as error:
        message = "configuration must be UTF-8"
        raise SnapshotError(message) from error
    if configuration_format is ConfigurationFormat.JSON:
        SemanticSnapshot.from_json(source)
        return
    try:
        value = tomllib.loads(source)
    except tomllib.TOMLDecodeError as error:
        message = "invalid TOML configuration"
        raise SnapshotError(message) from error
    SemanticSnapshot.from_value(value)


def _render_toml(configuration: MutableConfiguration) -> str:
    lines: list[str] = []
    _append_toml_table(lines, (), configuration, emit_header=False)
    return "\n".join(lines).rstrip() + "\n"


def _append_toml_table(
    lines: list[str],
    path: FieldPath,
    table: MutableConfiguration,
    *,
    emit_header: bool,
) -> None:
    scalar_items = [(key, value) for key, value in table.items() if not isinstance(value, dict)]
    child_items = [(key, value) for key, value in table.items() if isinstance(value, dict)]
    if emit_header:
        if lines and lines[-1]:
            lines.append("")
        lines.append(f"[{'.'.join(_toml_key(segment) for segment in path)}]")
    for key, value in sorted(scalar_items):
        lines.append(f"{_toml_key(key)} = {_toml_value(value)}")
    for key, value in sorted(child_items):
        _append_toml_table(
            lines,
            (*path, key),
            cast("MutableConfiguration", value),
            emit_header=True,
        )


def _toml_key(key: str) -> str:
    return key if _BARE_TOML_KEY.fullmatch(key) else json.dumps(key, ensure_ascii=False)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, list):
        values = cast("list[object]", value)
        return f"[{', '.join(_toml_value(item) for item in values)}]"
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        entries: list[str] = []
        for key, item in sorted(mapping.items(), key=lambda pair: str(pair[0])):
            if not isinstance(key, str):
                message = "TOML inline table keys must be strings"
                raise SnapshotError(message)
            entries.append(f"{_toml_key(key)} = {_toml_value(item)}")
        return f"{{ {', '.join(entries)} }}"
    message = f"unsupported TOML value: {type(value).__name__}"
    raise SnapshotError(message)
