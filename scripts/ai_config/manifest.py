from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from .core import (
    BindingProvider,
    FieldBinding,
    FieldManifest,
    FieldRule,
    FieldScope,
    FieldStrategy,
    ManifestDefinitionError,
)

if TYPE_CHECKING:
    from pathlib import Path


class ManifestError(ValueError):
    pass


def load_manifest(path: Path) -> FieldManifest:
    try:
        source = path.read_bytes()
    except OSError as error:
        message = f"cannot read manifest: {path}"
        raise ManifestError(message) from error
    return parse_manifest(source)


def parse_manifest(source: bytes) -> FieldManifest:
    try:
        loaded: object = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        message = "invalid JSON manifest"
        raise ManifestError(message) from error
    if not isinstance(loaded, dict):
        message = "manifest root must be a JSON object"
        raise ManifestError(message)
    manifest_object = cast("dict[object, object]", loaded)
    allowed_keys = {"engine", "fields", "schema_version"}
    if not set(manifest_object).issubset(allowed_keys):
        message = "manifest root contains unexpected fields"
        raise ManifestError(message)
    schema_version = manifest_object.get("schema_version", 1)
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        message = "unsupported manifest schema version"
        raise ManifestError(message)
    engine = manifest_object.get("engine")
    if engine is not None and (not isinstance(engine, str) or not engine):
        message = "manifest engine must be a non-empty string"
        raise ManifestError(message)
    raw_fields = manifest_object.get("fields")
    if not isinstance(raw_fields, list):
        message = "manifest fields must be an array"
        raise ManifestError(message)
    try:
        rules = tuple(_parse_rule(raw_rule) for raw_rule in cast("list[object]", raw_fields))
        return FieldManifest(rules=rules, schema_version=1, engine=engine)
    except ManifestDefinitionError as error:
        raise ManifestError(str(error)) from error


def _parse_rule(raw_rule: object) -> FieldRule:
    if not isinstance(raw_rule, dict):
        message = "manifest field rules must be objects"
        raise ManifestError(message)
    rule = cast("dict[object, object]", raw_rule)
    allowed_keys = {"binding", "path", "scope", "secret", "strategy"}
    if not set(rule).issubset(allowed_keys):
        message = "manifest field rule contains unexpected fields"
        raise ManifestError(message)
    raw_path = rule.get("path")
    raw_scope = rule.get("scope")
    raw_binding = rule.get("binding")
    raw_secret = rule.get("secret", False)
    raw_strategy = rule.get("strategy", FieldStrategy.ATOMIC.value)
    path = _parse_path(raw_path)
    if not isinstance(raw_scope, str):
        message = "manifest field scope must be a string"
        raise ManifestError(message)
    try:
        scope = FieldScope(raw_scope)
    except ValueError as error:
        message = f"unknown field scope: {raw_scope}"
        raise ManifestError(message) from error
    if not isinstance(raw_secret, bool):
        message = "manifest field secret flag must be a boolean"
        raise ManifestError(message)
    binding = _parse_binding(raw_binding)
    if not isinstance(raw_strategy, str):
        message = "manifest field strategy must be a string"
        raise ManifestError(message)
    try:
        strategy = FieldStrategy(raw_strategy)
    except ValueError as error:
        message = f"unknown field strategy: {raw_strategy}"
        raise ManifestError(message) from error
    return FieldRule(
        path=path,
        scope=scope,
        binding=binding,
        secret=raw_secret,
        strategy=strategy,
    )


def _parse_binding(raw_binding: object) -> FieldBinding | None:
    if raw_binding is None:
        return None
    if not isinstance(raw_binding, str):
        message = "manifest field binding must be a string"
        raise ManifestError(message)
    provider_name, separator, key = raw_binding.partition(":")
    if not separator:
        message = "manifest field binding must include a provider prefix"
        raise ManifestError(message)
    try:
        provider = BindingProvider(provider_name)
    except ValueError as error:
        message = f"unknown binding provider: {provider_name}"
        raise ManifestError(message) from error
    try:
        return FieldBinding(provider=provider, key=key)
    except ManifestDefinitionError as error:
        raise ManifestError(str(error)) from error


def _parse_path(raw_path: object) -> tuple[str, ...]:
    if isinstance(raw_path, str):
        return tuple(raw_path.split("."))
    if not isinstance(raw_path, list):
        message = "manifest field path must be a dotted string or string array"
        raise ManifestError(message)
    segments = cast("list[object]", raw_path)
    if not all(isinstance(segment, str) for segment in segments):
        message = "manifest field path segments must be strings"
        raise ManifestError(message)
    return tuple(cast("str", segment) for segment in segments)
