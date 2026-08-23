from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

from ai_config.adapters import EngineKind, resolve_engine_paths
from ai_config.state import resolve_state_paths

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ai-config"
MANIFEST = """{
  "schema_version": 1,
  "engine": "claude",
  "fields": [{"path": "setting", "scope": "shared"}]
}
"""


def create_cli_tree(
    tmp_path: Path,
    *,
    live_value: str | None = None,
) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    state_root = tmp_path / "state"
    paths = resolve_engine_paths(EngineKind.CLAUDE, repo_root=repo_root, home=home)
    paths.repository.parent.mkdir(parents=True)
    paths.repository.write_text('{"setting": "repository"}\n', encoding="utf-8")
    paths.manifest.write_text(MANIFEST, encoding="utf-8")
    if live_value is not None:
        paths.live.parent.mkdir(parents=True)
        paths.live.write_text(json.dumps({"setting": live_value}) + "\n", encoding="utf-8")
    return repo_root, home, state_root


def run_cli(
    command: str,
    repo_root: Path,
    home: Path,
    state_root: Path,
    *extra: str | Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            SCRIPT,
            command,
            "claude",
            "--repo-root",
            repo_root,
            "--home",
            home,
            "--state-root",
            state_root,
            "--profile",
            "work",
            "--json",
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def json_output(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    loaded: object = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return cast("dict[str, object]", loaded)


class TestOperationCli:
    def test_apply_creates_configuration_then_is_idempotent(self, tmp_path: Path) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path)

        first = run_cli("apply", repo_root, home, state_root)
        second = run_cli("apply", repo_root, home, state_root)

        assert first.returncode == 0
        assert json_output(first)["changed"] is True
        assert json_output(first)["converged"] is True
        assert second.returncode == 0
        assert json_output(second)["changed"] is False
        live = resolve_engine_paths(
            EngineKind.CLAUDE,
            repo_root=repo_root,
            home=home,
        ).live
        assert json.loads(live.read_text(encoding="utf-8")) == {"setting": "repository"}

    def test_check_reports_prospective_change_without_claiming_convergence(
        self,
        tmp_path: Path,
    ) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path)

        result = run_cli("apply", repo_root, home, state_root, "--check")

        output = json_output(result)
        assert result.returncode == 0
        assert output["changed"] is True
        assert output["check_mode"] is True
        assert output["converged"] is False
        assert not home.joinpath(".claude", "settings.json").exists()
        assert not state_root.exists()

    def test_reconcile_requires_and_consumes_an_explicit_live_decision(
        self,
        tmp_path: Path,
    ) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path)
        assert run_cli("apply", repo_root, home, state_root).returncode == 0
        live = resolve_engine_paths(
            EngineKind.CLAUDE,
            repo_root=repo_root,
            home=home,
        ).live
        live.write_text('{"setting": "live"}\n', encoding="utf-8")

        refused = run_cli("apply", repo_root, home, state_root)
        assert refused.returncode == 1
        assert json_output(refused)["requires_decisions"] is True

        decisions = tmp_path / "decisions.json"
        decisions.write_text(
            '{"decisions": [{"path": ["setting"], "source": "live"}]}\n',
            encoding="utf-8",
        )
        reconciled = run_cli(
            "reconcile",
            repo_root,
            home,
            state_root,
            "--decisions",
            decisions,
        )

        assert reconciled.returncode == 0
        assert json_output(reconciled)["captured"] == 1
        repository = resolve_engine_paths(
            EngineKind.CLAUDE,
            repo_root=repo_root,
            home=home,
        ).repository
        assert json.loads(repository.read_text(encoding="utf-8")) == {"setting": "live"}
        base = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=home,
            state_root=state_root,
        ).base
        assert base.exists()


class TestBootstrapCli:
    def test_default_is_a_read_only_plan_then_write_initialises_state(
        self,
        tmp_path: Path,
    ) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path, live_value="live")
        repository = resolve_engine_paths(
            EngineKind.CLAUDE,
            repo_root=repo_root,
            home=home,
        ).repository
        repository_before = repository.read_bytes()

        preview = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
        )

        preview_output = json_output(preview)
        assert preview.returncode == 0
        assert preview_output["write"] is False
        assert preview_output["check_mode"] is True
        assert preview_output["counts"] == {
            "capture": 1,
            "ignore-runtime": 0,
            "keep-repo": 0,
            "preserve-local": 0,
        }
        preview_token = preview_output["preview_token"]
        assert isinstance(preview_token, str)
        assert preview_token.startswith("sha256:")
        assert repository.read_bytes() == repository_before
        assert not state_root.exists()

        written = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
            "--write",
            "--preview-token",
            preview_token,
        )

        written_output = json_output(written)
        assert written.returncode == 0
        assert written_output["write"] is True
        assert written_output["check_mode"] is False
        assert json.loads(repository.read_text(encoding="utf-8")) == {"setting": "live"}
        base = resolve_state_paths(
            EngineKind.CLAUDE,
            profile="work",
            home=home,
            state_root=state_root,
        ).base
        assert base.exists()

    def test_refuses_a_second_bootstrap(self, tmp_path: Path) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path, live_value="live")
        preview = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
        )
        preview_token = json_output(preview)["preview_token"]
        assert isinstance(preview_token, str)
        first = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
            "--write",
            "--preview-token",
            preview_token,
        )

        second = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
        )

        assert first.returncode == 0
        assert second.returncode == 2
        assert json_output(second)["error"] == "BootstrapError"

    def test_write_without_preview_token_is_rejected(self, tmp_path: Path) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path, live_value="live")

        result = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
            "--write",
        )

        assert result.returncode == 2
        assert json_output(result)["error"] == "BootstrapError"
        assert not state_root.exists()

    def test_write_rejects_live_changed_after_preview(self, tmp_path: Path) -> None:
        repo_root, home, state_root = create_cli_tree(tmp_path, live_value="live")
        preview = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
        )
        preview_token = json_output(preview)["preview_token"]
        assert isinstance(preview_token, str)
        live = resolve_engine_paths(
            EngineKind.CLAUDE,
            repo_root=repo_root,
            home=home,
        ).live
        live.write_text('{"setting": "changed"}\n', encoding="utf-8")

        result = run_cli(
            "bootstrap",
            repo_root,
            home,
            state_root,
            "--from-live",
            "--write",
            "--preview-token",
            preview_token,
        )

        assert result.returncode == 2
        assert json_output(result)["error"] == "BootstrapError"
        assert not state_root.exists()
