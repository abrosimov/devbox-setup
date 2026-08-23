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
    *,
    source: bytes | None = None,
) -> bytes:
    source_configuration = (
        _load_source_configuration(source, configuration_format) if source is not None else None
    )
    if source is not None and source_configuration == configuration:
        return source
    if configuration_format is ConfigurationFormat.JSON:
        if source_configuration is not None:
            configuration = _preserve_mapping_order(source_configuration, configuration)
        return (json.dumps(configuration, ensure_ascii=False, indent=2) + "\n").encode()
    if source is not None and source_configuration is not None:
        preserved = _render_toml_preserving_roots(
            configuration,
            source=source,
            source_configuration=source_configuration,
        )
        if preserved is not None:
            return preserved
    return _render_toml(configuration).encode()


def _load_source_configuration(
    source: bytes,
    configuration_format: ConfigurationFormat,
) -> MutableConfiguration | None:
    try:
        text = source.decode()
    except UnicodeDecodeError:
        return None
    try:
        loaded = (
            json.loads(text)
            if configuration_format is ConfigurationFormat.JSON
            else tomllib.loads(text)
        )
    except (json.JSONDecodeError, tomllib.TOMLDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return cast("MutableConfiguration", loaded)


def _preserve_mapping_order(
    source: MutableConfiguration,
    desired: MutableConfiguration,
) -> MutableConfiguration:
    result: MutableConfiguration = {}
    for key, source_value in source.items():
        if key not in desired:
            continue
        desired_value = desired[key]
        if isinstance(source_value, dict) and isinstance(desired_value, dict):
            result[key] = _preserve_mapping_order(
                cast("MutableConfiguration", source_value),
                cast("MutableConfiguration", desired_value),
            )
        else:
            result[key] = desired_value
    for key, desired_value in desired.items():
        if key not in source:
            result[key] = desired_value
    return result


def _render_toml_preserving_roots(
    configuration: MutableConfiguration,
    *,
    source: bytes,
    source_configuration: MutableConfiguration,
) -> bytes | None:
    changed_roots = _changed_toml_roots(source_configuration, configuration)
    try:
        lines = source.decode().splitlines(keepends=True)
    except UnicodeDecodeError:
        return None
    kept, replaced_roots = _toml_lines_without_roots(
        lines,
        changed_roots,
        configuration,
    )
    scalar_fragments, table_fragments = _toml_replacement_fragments(
        configuration,
        changed_roots - replaced_roots,
    )
    candidate_bytes = _assemble_toml(kept, scalar_fragments, table_fragments)
    rendered_configuration = _load_source_configuration(
        candidate_bytes,
        ConfigurationFormat.TOML,
    )
    return candidate_bytes if rendered_configuration == configuration else None


def _changed_toml_roots(
    source: MutableConfiguration,
    desired: MutableConfiguration,
) -> set[str]:
    return {
        key
        for key in source.keys() | desired.keys()
        if source.get(key, MissingValue.MISSING) != desired.get(key, MissingValue.MISSING)
    }


def _toml_lines_without_roots(
    lines: list[str],
    changed_roots: set[str],
    configuration: MutableConfiguration,
) -> tuple[list[str], set[str]]:
    kept: list[str] = []
    replaced_roots: set[str] = set()
    current_root: str | None = None
    trailing_trivia: list[str] = []
    skipped_assignment_lines = 0
    for index, line in enumerate(lines):
        if skipped_assignment_lines:
            skipped_assignment_lines -= 1
            continue
        header_root = _toml_header_root(line)
        if header_root is not None:
            if current_root in changed_roots and header_root not in changed_roots:
                kept.extend(trailing_trivia)
            trailing_trivia.clear()
            current_root = header_root
        assignment_root = _toml_assignment_root(line) if current_root is None else None
        if assignment_root is not None and assignment_root in changed_roots:
            skipped_assignment_lines = (
                _toml_assignment_span_length(lines[index:], assignment_root) - 1
            )
            if (
                assignment_root in configuration
                and not isinstance(configuration[assignment_root], dict)
                and assignment_root not in replaced_roots
            ):
                replacement = _render_toml(
                    {assignment_root: configuration[assignment_root]}
                ).rstrip()
                kept.append(f"{replacement}\n")
                replaced_roots.add(assignment_root)
            continue
        if current_root in changed_roots:
            if _is_toml_trivia(line):
                trailing_trivia.append(line)
            else:
                trailing_trivia.clear()
            continue
        kept.append(line)
    return kept, replaced_roots


def _is_toml_trivia(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _toml_assignment_span_length(lines: list[str], root: str) -> int:
    for length in range(1, len(lines) + 1):
        try:
            parsed = tomllib.loads("".join(lines[:length]))
        except tomllib.TOMLDecodeError:
            continue
        if root in parsed:
            return length
    return 1


def _toml_replacement_fragments(
    configuration: MutableConfiguration,
    changed_roots: set[str],
) -> tuple[list[str], list[str]]:
    scalar_fragments: list[str] = []
    table_fragments: list[str] = []
    for root in configuration:
        if root not in changed_roots:
            continue
        fragment = _render_toml({root: configuration[root]}).rstrip()
        if isinstance(configuration[root], dict):
            table_fragments.append(fragment)
        else:
            scalar_fragments.append(fragment)
    return scalar_fragments, table_fragments


def _assemble_toml(
    kept: list[str],
    scalar_fragments: list[str],
    table_fragments: list[str],
) -> bytes:
    first_table = next(
        (index for index, line in enumerate(kept) if _toml_header_root(line) is not None),
        len(kept),
    )
    if scalar_fragments:
        while first_table > 0 and not kept[first_table - 1].strip():
            kept.pop(first_table - 1)
            first_table -= 1
        insertion = [f"{fragment}\n" for fragment in scalar_fragments]
        if first_table < len(kept):
            insertion.append("\n")
        kept[first_table:first_table] = insertion
    candidate = "".join(kept).rstrip()
    if table_fragments:
        suffix = "\n\n".join(table_fragments)
        candidate = f"{candidate}\n\n{suffix}" if candidate else suffix
    return f"{candidate.rstrip()}\n".encode()


def _toml_header_root(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith("["):
        return None
    array_table = stripped.startswith("[[")
    closing = "]]" if array_table else "]"
    start = 2 if array_table else 1
    end = stripped.find(closing, start)
    if end < 0:
        return None
    header = stripped[start:end].strip()
    try:
        parsed = tomllib.loads(f"[{header}]\n")
    except tomllib.TOMLDecodeError:
        return None
    return next(iter(parsed), None)


def _toml_assignment_root(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.partition("=")[0].strip()
    try:
        parsed = tomllib.loads(f"{key} = 0\n")
    except tomllib.TOMLDecodeError:
        return None
    return next(iter(parsed), None)


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
