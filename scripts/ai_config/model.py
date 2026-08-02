from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path


class SnapshotError(ValueError):
    pass


class ScalarKind(StrEnum):
    NULL = "null"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    STRING = "string"


@dataclass(frozen=True, slots=True)
class SemanticScalar:
    kind: ScalarKind
    value: None | bool | int | float | str


@dataclass(frozen=True, slots=True)
class SemanticArray:
    items: tuple[SemanticValue, ...]


@dataclass(frozen=True, slots=True)
class SemanticObject:
    fields: tuple[tuple[str, SemanticValue], ...]


type SemanticValue = SemanticScalar | SemanticArray | SemanticObject
type FieldPath = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SemanticField:
    path: FieldPath
    value: SemanticValue


@dataclass(frozen=True, slots=True)
class SemanticSnapshot:
    root: SemanticObject

    @classmethod
    def from_value(cls, value: object) -> SemanticSnapshot:
        semantic_value = to_semantic_value(value)
        if not isinstance(semantic_value, SemanticObject):
            message = "configuration root must be a JSON object"
            raise SnapshotError(message)
        return cls(root=semantic_value)

    @classmethod
    def from_json(cls, source: str) -> SemanticSnapshot:
        try:
            value: object = json.loads(source)
        except json.JSONDecodeError as error:
            message = "invalid JSON configuration"
            raise SnapshotError(message) from error
        return cls.from_value(value)

    @classmethod
    def from_json_file(cls, path: Path) -> SemanticSnapshot:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as error:
            message = f"cannot read configuration: {path}"
            raise SnapshotError(message) from error
        return cls.from_json(source)

    def semantic_fields(self) -> tuple[SemanticField, ...]:
        fields: list[SemanticField] = []
        _collect_fields(self.root, (), fields)
        return tuple(fields)


def to_semantic_value(value: object) -> SemanticValue:
    if value is None:
        return SemanticScalar(kind=ScalarKind.NULL, value=None)
    if isinstance(value, bool):
        return SemanticScalar(kind=ScalarKind.BOOLEAN, value=value)
    if isinstance(value, int):
        return SemanticScalar(kind=ScalarKind.INTEGER, value=value)
    if isinstance(value, float):
        if not math.isfinite(value):
            message = "JSON numbers must be finite"
            raise SnapshotError(message)
        return SemanticScalar(kind=ScalarKind.NUMBER, value=value)
    if isinstance(value, str):
        return SemanticScalar(kind=ScalarKind.STRING, value=value)
    return _to_semantic_collection(value)


def _to_semantic_collection(value: object) -> SemanticArray | SemanticObject:
    if isinstance(value, list):
        items = cast("list[object]", value)
        return SemanticArray(items=tuple(to_semantic_value(item) for item in items))
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        fields: list[tuple[str, SemanticValue]] = []
        for key, item in mapping.items():
            if not isinstance(key, str):
                message = "JSON object keys must be strings"
                raise SnapshotError(message)
            fields.append((key, to_semantic_value(item)))
        return SemanticObject(fields=tuple(sorted(fields, key=lambda field: field[0])))
    message = f"unsupported configuration value: {type(value).__name__}"
    raise SnapshotError(message)


def to_plain_value(value: SemanticValue) -> object:
    if isinstance(value, SemanticScalar):
        return value.value
    if isinstance(value, SemanticArray):
        return [to_plain_value(item) for item in value.items]
    return {key: to_plain_value(item) for key, item in value.fields}


def _collect_fields(
    value: SemanticValue,
    path: FieldPath,
    fields: list[SemanticField],
) -> None:
    if isinstance(value, SemanticObject) and value.fields:
        for key, item in value.fields:
            _collect_fields(item, (*path, key), fields)
        return
    if path:
        fields.append(SemanticField(path=path, value=value))
