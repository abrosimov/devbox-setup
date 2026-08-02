from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path

    from .model import FieldPath


class DecisionError(ValueError):
    pass


class DecisionSource(StrEnum):
    REPO = "repo"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class FieldDecision:
    path: FieldPath
    source: DecisionSource


@dataclass(frozen=True, slots=True)
class DecisionSet:
    decisions: tuple[FieldDecision, ...]

    def __post_init__(self) -> None:
        paths = [decision.path for decision in self.decisions]
        if len(paths) != len(set(paths)):
            message = "decision paths must be unique"
            raise DecisionError(message)

    def source_for(self, path: FieldPath) -> DecisionSource | None:
        return next(
            (decision.source for decision in self.decisions if decision.path == path),
            None,
        )


def load_decisions(path: Path) -> DecisionSet:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        message = f"invalid decisions file: {path}"
        raise DecisionError(message) from error
    if not isinstance(loaded, dict):
        message = "decisions root must be an object"
        raise DecisionError(message)
    document = cast("dict[object, object]", loaded)
    if set(document) != {"decisions"}:
        message = "decisions root contains unexpected fields"
        raise DecisionError(message)
    raw_decisions = document.get("decisions")
    if not isinstance(raw_decisions, list):
        message = "decisions must be an array"
        raise DecisionError(message)
    return DecisionSet(
        decisions=tuple(_parse_decision(item) for item in cast("list[object]", raw_decisions))
    )


def _parse_decision(value: object) -> FieldDecision:
    if not isinstance(value, dict):
        message = "each decision must be an object"
        raise DecisionError(message)
    raw = cast("dict[object, object]", value)
    if set(raw) != {"path", "source"}:
        message = "decision contains unexpected fields"
        raise DecisionError(message)
    raw_path = raw.get("path")
    raw_source = raw.get("source")
    if not isinstance(raw_path, list) or not raw_path:
        message = "decision paths must be non-empty arrays"
        raise DecisionError(message)
    path_items = cast("list[object]", raw_path)
    if not all(isinstance(segment, str) and segment for segment in path_items):
        message = "decision path segments must be non-empty strings"
        raise DecisionError(message)
    if not isinstance(raw_source, str):
        message = "decision source must be a string"
        raise DecisionError(message)
    try:
        source = DecisionSource(raw_source)
    except ValueError as error:
        message = f"unknown decision source: {raw_source}"
        raise DecisionError(message) from error
    return FieldDecision(
        path=tuple(cast("str", segment) for segment in path_items),
        source=source,
    )
