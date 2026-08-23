from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .core import FieldManifest, FieldRule, FieldScope, ReconciliationPlan, plan_reconciliation
from .manifest import parse_manifest
from .model import SemanticSnapshot, SnapshotError

type RuntimeRuleBuilder = Callable[
    [tuple[SemanticSnapshot, ...]],
    tuple[FieldRule, ...],
]


class EngineKind(StrEnum):
    CLAUDE = "claude"
    AGY = "agy"
    CODEX = "codex"


class ConfigurationFormat(StrEnum):
    JSON = "json"
    TOML = "toml"


@dataclass(frozen=True, slots=True)
class EnginePaths:
    repository: Path
    live: Path
    manifest: Path


@dataclass(frozen=True, slots=True)
class EngineAdapterSpec:
    engine: EngineKind
    configuration_format: ConfigurationFormat
    repository_relative_path: Path
    live_relative_path: Path
    manifest_relative_path: Path
    repository_mode: int = 0o644
    live_mode: int = 0o600
    blocked_prefixes: tuple[tuple[str, ...], ...] = ()
    runtime_rule_builder: RuntimeRuleBuilder | None = None


def _codex_hook_state_rules(
    snapshots: tuple[SemanticSnapshot, ...],
) -> tuple[FieldRule, ...]:
    paths = {
        field.path
        for snapshot in snapshots
        for field in snapshot.semantic_fields()
        if len(field.path) == 4
        and field.path[:2] == ("hooks", "state")
        and field.path[-1] in {"enabled", "trusted_hash"}
    }
    return tuple(FieldRule(path=path, scope=FieldScope.RUNTIME) for path in sorted(paths))


_CLAUDE_ADAPTER = EngineAdapterSpec(
    engine=EngineKind.CLAUDE,
    configuration_format=ConfigurationFormat.JSON,
    repository_relative_path=Path("roles/devbox/files/dot_claude/settings.json"),
    live_relative_path=Path(".claude/settings.json"),
    manifest_relative_path=Path("roles/devbox/files/dot_claude/settings.ai-config.json"),
)

_AGY_ADAPTER = EngineAdapterSpec(
    engine=EngineKind.AGY,
    configuration_format=ConfigurationFormat.JSON,
    repository_relative_path=Path("roles/devbox/files/dot_agy/cli/settings.json.j2"),
    live_relative_path=Path(".gemini/antigravity-cli/settings.json"),
    manifest_relative_path=Path("roles/devbox/files/dot_agy/cli/settings.ai-config.json"),
)

_CODEX_ADAPTER = EngineAdapterSpec(
    engine=EngineKind.CODEX,
    configuration_format=ConfigurationFormat.TOML,
    repository_relative_path=Path("roles/devbox/files/dot_codex/config.toml.j2"),
    live_relative_path=Path(".codex/config.toml"),
    manifest_relative_path=Path("roles/devbox/files/dot_codex/config.ai-config.json"),
    blocked_prefixes=(("hooks", "state"),),
    runtime_rule_builder=_codex_hook_state_rules,
)


def engine_adapter(engine: EngineKind) -> EngineAdapterSpec:
    match engine:
        case EngineKind.CLAUDE:
            return _CLAUDE_ADAPTER
        case EngineKind.AGY:
            return _AGY_ADAPTER
        case EngineKind.CODEX:
            return _CODEX_ADAPTER


def resolve_engine_paths(
    engine: EngineKind,
    *,
    repo_root: Path,
    home: Path,
) -> EnginePaths:
    adapter = engine_adapter(engine)
    return EnginePaths(
        repository=repo_root / adapter.repository_relative_path,
        live=home / adapter.live_relative_path,
        manifest=repo_root / adapter.manifest_relative_path,
    )


def load_engine_plan(
    engine: EngineKind,
    *,
    repo_root: Path,
    home: Path,
    base_path: Path | None,
) -> ReconciliationPlan:
    adapter = engine_adapter(engine)
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    base = SemanticSnapshot.from_json_file(base_path) if base_path is not None else None
    repository = load_snapshot(paths.repository, adapter.configuration_format)
    live = load_snapshot(paths.live, adapter.configuration_format)
    runtime_snapshots = (live,) if base is None else (base, live)
    manifest = parse_engine_manifest(
        engine,
        paths.manifest.read_bytes(),
        runtime_snapshots=runtime_snapshots,
    )
    return plan_reconciliation(base=base, repo=repository, live=live, manifest=manifest)


def parse_engine_manifest(
    engine: EngineKind,
    source: bytes,
    *,
    runtime_snapshots: tuple[SemanticSnapshot, ...] = (),
) -> FieldManifest:
    manifest = parse_manifest(source)
    adapter = engine_adapter(engine)
    runtime_rules = (
        adapter.runtime_rule_builder(runtime_snapshots)
        if adapter.runtime_rule_builder is not None
        else ()
    )
    return FieldManifest(
        rules=(*manifest.rules, *runtime_rules),
        schema_version=manifest.schema_version,
        engine=manifest.engine,
        blocked_prefixes=(*manifest.blocked_prefixes, *adapter.blocked_prefixes),
    )


def load_snapshot(
    path: Path,
    configuration_format: ConfigurationFormat,
    *,
    missing_as_empty: bool = False,
) -> SemanticSnapshot:
    if missing_as_empty and not path.exists():
        return SemanticSnapshot.from_value({})
    try:
        source = path.read_bytes()
    except OSError as error:
        message = f"cannot read configuration: {path}"
        raise SnapshotError(message) from error
    return parse_snapshot(source, configuration_format)


def parse_snapshot(
    source: bytes,
    configuration_format: ConfigurationFormat,
) -> SemanticSnapshot:
    try:
        text = source.decode()
    except UnicodeDecodeError as error:
        message = "configuration must be UTF-8"
        raise SnapshotError(message) from error
    if configuration_format is ConfigurationFormat.JSON:
        return SemanticSnapshot.from_json(text)
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        message = "invalid TOML configuration"
        raise SnapshotError(message) from error
    return SemanticSnapshot.from_value(value)
