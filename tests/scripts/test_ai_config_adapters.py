from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ai_config import (
    ChangeKind,
    ConfigurationFormat,
    EngineAdapterSpec,
    EngineKind,
    EnginePaths,
    FieldScope,
    MissingValue,
    ReconciliationPlan,
    SnapshotError,
    load_engine_plan,
    resolve_engine_paths,
    to_plain_value,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class EngineTestTree:
    repo_root: Path
    home: Path
    base_path: Path | None
    paths: EnginePaths


def build_engine_tree(
    tmp_path: Path,
    engine: EngineKind,
    repository_source: str,
    live_source: str,
    base_source: str | None,
) -> EngineTestTree:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)
    source_paths = resolve_engine_paths(engine, repo_root=REPO_ROOT, home=home)
    paths.repository.parent.mkdir(parents=True, exist_ok=True)
    paths.live.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.repository.write_text(repository_source, encoding="utf-8")
    paths.live.write_text(live_source, encoding="utf-8")
    shutil.copyfile(source_paths.manifest, paths.manifest)
    if base_source is None:
        base_path = None
    else:
        base_path = tmp_path / "base.json"
        base_path.write_text(base_source, encoding="utf-8")
    return EngineTestTree(repo_root=repo_root, home=home, base_path=base_path, paths=paths)


def file_state(roots: tuple[Path, ...]) -> Mapping[Path, tuple[bytes, int]]:
    return {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for root in roots
        for path in root.rglob("*")
        if path.is_file()
    }


class TestEnginePathResolution:
    @pytest.mark.parametrize(
        ("engine", "repository", "live", "manifest"),
        [
            (
                EngineKind.CLAUDE,
                "roles/devbox/files/dot_claude/settings.json",
                ".claude/settings.json",
                "roles/devbox/files/dot_claude/settings.ai-config.json",
            ),
            (
                EngineKind.AGY,
                "roles/devbox/files/dot_agy/cli/settings.json.j2",
                ".gemini/antigravity-cli/settings.json",
                "roles/devbox/files/dot_agy/cli/settings.ai-config.json",
            ),
            (
                EngineKind.CODEX,
                "roles/devbox/files/dot_codex/config.toml.j2",
                ".codex/config.toml",
                "roles/devbox/files/dot_codex/config.ai-config.json",
            ),
        ],
    )
    def test_resolves_from_explicit_roots(
        self,
        tmp_path: Path,
        engine: EngineKind,
        repository: str,
        live: str,
        manifest: str,
    ) -> None:
        repo_root = tmp_path / "explicit-repository"
        home = tmp_path / "explicit-home"

        paths = resolve_engine_paths(engine, repo_root=repo_root, home=home)

        assert paths.repository == repo_root / repository
        assert paths.live == home / live
        assert paths.manifest == repo_root / manifest


class TestEngineAdapterParsing:
    def test_adapter_positional_modes_remain_backwards_compatible(self) -> None:
        adapter = EngineAdapterSpec(
            EngineKind.CLAUDE,
            ConfigurationFormat.JSON,
            Path("repository.json"),
            Path("live.json"),
            Path("manifest.json"),
            0o640,
            0o660,
        )

        assert adapter.repository_mode == 0o640
        assert adapter.live_mode == 0o660
        assert adapter.blocked_prefixes == ()
        assert adapter.runtime_rule_builder is None

    @pytest.mark.parametrize(
        ("engine", "repository_source", "live_source"),
        [
            (
                EngineKind.CLAUDE,
                json.dumps({"model": "repository"}),
                json.dumps({"model": "base"}),
            ),
            (
                EngineKind.AGY,
                json.dumps({"model": "repository"}),
                json.dumps({"model": "base"}),
            ),
            (
                EngineKind.CODEX,
                'model = "repository"\n',
                'model = "base"\n',
            ),
        ],
    )
    def test_loads_all_engine_formats_into_existing_plan(
        self,
        tmp_path: Path,
        engine: EngineKind,
        repository_source: str,
        live_source: str,
    ) -> None:
        tree = build_engine_tree(
            tmp_path,
            engine,
            repository_source,
            live_source,
            json.dumps({"model": "base"}),
        )

        plan = load_engine_plan(
            engine,
            repo_root=tree.repo_root,
            home=tree.home,
            base_path=tree.base_path,
        )
        model_change = next(change for change in plan.changes if change.path == ("model",))

        assert model_change.kind is ChangeKind.APPLY_REPO

    def test_codex_keeps_quoted_jinja_as_environment_value(self, tmp_path: Path) -> None:
        source_path = REPO_ROOT / "roles/devbox/files/dot_codex/config.toml.j2"
        source = source_path.read_text(encoding="utf-8")
        tree = build_engine_tree(tmp_path, EngineKind.CODEX, source, source, None)

        plan = load_engine_plan(
            EngineKind.CODEX,
            repo_root=tree.repo_root,
            home=tree.home,
            base_path=None,
        )
        environment = next(
            change for change in plan.changes if change.path == ("otel", "environment")
        )

        assert environment.kind is ChangeKind.UNCHANGED
        assert environment.scope is FieldScope.ENVIRONMENT
        assert environment.repo is not MissingValue.MISSING
        assert to_plain_value(environment.repo) == "{{ devbox_active_profile }}"

    @pytest.mark.parametrize(
        ("engine", "repository_source", "live_source"),
        [
            (EngineKind.CLAUDE, "{", json.dumps({"model": "base"})),
            (EngineKind.AGY, json.dumps({"model": "base"}), "["),
            (EngineKind.CODEX, 'model = ["broken"\n', 'model = "base"\n'),
            (EngineKind.CODEX, 'model = "base"\n', "[model\n"),
        ],
    )
    def test_rejects_invalid_engine_documents(
        self,
        tmp_path: Path,
        engine: EngineKind,
        repository_source: str,
        live_source: str,
    ) -> None:
        tree = build_engine_tree(
            tmp_path,
            engine,
            repository_source,
            live_source,
            json.dumps({"model": "base"}),
        )

        with pytest.raises(SnapshotError):
            load_engine_plan(
                engine,
                repo_root=tree.repo_root,
                home=tree.home,
                base_path=tree.base_path,
            )

    def test_codex_base_remains_canonical_json(self, tmp_path: Path) -> None:
        tree = build_engine_tree(
            tmp_path,
            EngineKind.CODEX,
            'model = "repository"\n',
            'model = "live"\n',
            'model = "not-json"\n',
        )

        with pytest.raises(SnapshotError):
            load_engine_plan(
                EngineKind.CODEX,
                repo_root=tree.repo_root,
                home=tree.home,
                base_path=tree.base_path,
            )


class TestEngineAdapterReadOnlyContract:
    @pytest.mark.parametrize(
        ("engine", "repository_source", "live_source"),
        [
            (
                EngineKind.CLAUDE,
                json.dumps({"model": "repository"}),
                json.dumps({"model": "live"}),
            ),
            (
                EngineKind.AGY,
                json.dumps({"model": "repository"}),
                json.dumps({"model": "live"}),
            ),
            (
                EngineKind.CODEX,
                'model = "repository"\n',
                'model = "live"\n',
            ),
        ],
    )
    def test_plan_loading_does_not_write_files(
        self,
        tmp_path: Path,
        engine: EngineKind,
        repository_source: str,
        live_source: str,
    ) -> None:
        tree = build_engine_tree(
            tmp_path,
            engine,
            repository_source,
            live_source,
            json.dumps({"model": "base"}),
        )
        roots = (tree.repo_root, tree.home, tmp_path)
        before = file_state(roots)

        plan = load_engine_plan(
            engine,
            repo_root=tree.repo_root,
            home=tree.home,
            base_path=tree.base_path,
        )

        assert isinstance(plan, ReconciliationPlan)
        assert file_state(roots) == before
