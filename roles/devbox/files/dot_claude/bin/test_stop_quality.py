from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_quality
from _claude_lib.proc import CmdResult


def _ok(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


class TestCollectGitChanges:
    def test_collects_tracked_and_untracked_from_repository_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "--quiet")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "Test User")

        baseline = {
            ".gitignore": "*.ignored\n",
            "staged.py": "old\n",
            "unstaged.py": "old\n",
            "deleted.py": "old\n",
        }
        for name, content in baseline.items():
            (repo / name).write_text(content, encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", "baseline")

        (repo / "staged.py").write_text("staged\n", encoding="utf-8")
        _git(repo, "add", "staged.py")
        (repo / "staged.py").write_text("staged and unstaged\n", encoding="utf-8")
        (repo / "unstaged.py").write_text("changed\n", encoding="utf-8")
        (repo / "deleted.py").unlink()
        (repo / "new.py").write_text("new\n", encoding="utf-8")
        (repo / "white space.py").write_text("space\n", encoding="utf-8")
        (repo / "line\nbreak.py").write_text("newline\n", encoding="utf-8")
        (repo / "skip.ignored").write_text("ignored\n", encoding="utf-8")
        nested = repo / "nested"
        nested.mkdir()

        changes = stop_quality.collect_git_changes(nested)

        assert changes is not None
        assert changes.root.resolve() == repo.resolve()
        assert {path.relative_to(changes.root).as_posix() for path in changes.files} == {
            "line\nbreak.py",
            "new.py",
            "staged.py",
            "unstaged.py",
            "white space.py",
        }
        assert len(changes.files) == 5

    def test_returns_none_outside_git_repository(self, tmp_path: Path) -> None:
        assert stop_quality.collect_git_changes(tmp_path) is None

    def test_rejects_external_target_symlink(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "--quiet")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "Test User")
        (repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", "baseline")
        external = tmp_path / "external.py"
        external.write_text("external\n", encoding="utf-8")
        link = repo / "external.py"
        try:
            link.symlink_to(external)
        except OSError:
            pytest.skip("symlinks are unavailable on this platform")

        changes = stop_quality.collect_git_changes(repo)

        assert changes is not None
        assert changes.files == ()


class TestBatching:
    def test_formatters_receive_one_batch_per_project(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "go.mod").write_text("module example.com/project\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
        files = tuple(tmp_path / name for name in ("a.go", "b.go", "a.py", "b.py", "a.ts", "b.tsx"))
        for file_path in files:
            file_path.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        stop_quality.format_changes(stop_quality.ChangeSet(root=tmp_path, files=files))

        goimports = [call for call in calls if call[0] == "goimports"]
        ruff_fix = [call for call in calls if call[:3] == ["ruff", "check", "--fix"]]
        ruff_format = [call for call in calls if call[:2] == ["ruff", "format"]]
        prettier = [call for call in calls if call[:2] == ["npx", "prettier"]]
        assert len(goimports) == 1
        assert len(ruff_fix) == 1
        assert len(ruff_format) == 1
        assert len(prettier) == 1
        assert {str(tmp_path / "a.go"), str(tmp_path / "b.go")} <= set(goimports[0])
        assert {str(tmp_path / "a.py"), str(tmp_path / "b.py")} <= set(ruff_fix[0])
        assert {str(tmp_path / "a.ts"), str(tmp_path / "b.tsx")} <= set(prettier[0])

    @pytest.mark.parametrize(
        ("config_name", "config_text"),
        [
            ("pyproject.toml", "[tool.ruff]\n\n[tool.black]\ntarget-version = ['py310']\n"),
            (
                ".pre-commit-config.yaml",
                "repos:\n  - repo: https://github.com/psf/black-pre-commit-mirror\n"
                "    rev: 26.5.1\n",
            ),
        ],
    )
    def test_black_project_is_formatted_by_its_own_black_not_ruff_format(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        config_name: str,
        config_text: str,
    ) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / config_name).write_text(config_text, encoding="utf-8")
        black = tmp_path / ".venv" / "bin" / "black"
        black.parent.mkdir(parents=True)
        black.touch()
        source = tmp_path / "a.py"
        source.touch()
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        stop_quality.format_changes(stop_quality.ChangeSet(root=tmp_path, files=(source,)))

        assert [call[0] for call in calls] == ["ruff", str(black)]
        assert calls[0][:3] == ["ruff", "check", "--fix"]
        assert str(source) in calls[1]

    def test_black_project_without_project_black_is_left_unformatted(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.black]\n", encoding="utf-8")
        source = tmp_path / "a.py"
        source.touch()
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        pipeline = stop_quality.format_changes(
            stop_quality.ChangeSet(root=tmp_path, files=(source,))
        )

        assert [call[:2] for call in calls] == [["ruff", "check"]]
        assert any("formatting was skipped" in advisory for advisory in pipeline.advisories)

    def test_checkers_receive_one_batch_per_project(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "go.mod").write_text("module example.com/project\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\n[tool.mypy]\n",
            encoding="utf-8",
        )
        (tmp_path / "uv.lock").write_text("", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
        (tmp_path / ".eslintrc.json").write_text("{}\n", encoding="utf-8")
        (tmp_path / "tsconfig.json").write_text("{}\n", encoding="utf-8")
        names = (
            "a.go",
            "b.go",
            "a.py",
            "b.py",
            "a.ts",
            "b.tsx",
            "Dockerfile",
            "worker.Dockerfile",
            "compose.yml",
            "docker-compose.yaml",
        )
        files = tuple(tmp_path / name for name in names)
        for file_path in files:
            file_path.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        issues = stop_quality.lint_changes(stop_quality.ChangeSet(root=tmp_path, files=files))

        assert issues == []
        expected_prefixes = (
            ("hadolint",),
            ("dclint",),
            ("golangci-lint",),
            ("ruff", "check"),
            ("uv", "run", "mypy"),
            ("npx", "eslint"),
            ("npx", "tsc"),
        )
        for prefix in expected_prefixes:
            assert len([call for call in calls if tuple(call[: len(prefix)]) == prefix]) == 1

        hadolint = next(call for call in calls if call[0] == "hadolint")
        dclint = next(call for call in calls if call[0] == "dclint")
        ruff = next(call for call in calls if call[:2] == ["ruff", "check"])
        eslint = next(call for call in calls if call[:2] == ["npx", "eslint"])
        assert {str(tmp_path / "Dockerfile"), str(tmp_path / "worker.Dockerfile")} <= set(
            hadolint,
        )
        assert {str(tmp_path / "compose.yml"), str(tmp_path / "docker-compose.yaml")} <= set(
            dclint,
        )
        assert {str(tmp_path / "a.py"), str(tmp_path / "b.py")} <= set(ruff)
        assert {str(tmp_path / "a.ts"), str(tmp_path / "b.tsx")} <= set(eslint)

    def test_ruff_only_python_project_does_not_activate_mypy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n", encoding="utf-8")
        target = tmp_path / "changed.py"
        target.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        changes = stop_quality.ChangeSet(root=tmp_path, files=(target,))

        assert stop_quality.lint_changes(changes) == []
        assert [call[:2] for call in calls] == [["ruff", "check"]]

    def test_python_without_config_does_not_activate_mypy(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "changed.py"
        target.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        changes = stop_quality.ChangeSet(root=tmp_path, files=(target,))

        assert stop_quality.lint_changes(changes) == []
        assert [call[:2] for call in calls] == [["ruff", "check"]]

    def test_package_json_without_eslint_config_does_not_activate_eslint(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
        target = tmp_path / "changed.js"
        target.write_text("", encoding="utf-8")
        calls: list[list[str]] = []

        def run(command: list[str], **_kwargs: object) -> CmdResult:
            calls.append(command)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        changes = stop_quality.ChangeSet(root=tmp_path, files=(target,))

        assert stop_quality.lint_changes(changes) == []
        assert calls == []


class TestQualityPipeline:
    def test_subprocess_timeout_is_capped_by_remaining_budget(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        now = [100.0]
        pipeline = stop_quality.QualityPipeline.start(timeout=50, clock=lambda: now[0])
        observed_timeouts: list[int] = []

        def run(
            _command: list[str],
            *,
            timeout: int,
            **_kwargs: object,
        ) -> CmdResult:
            observed_timeouts.append(timeout)
            return _ok()

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        now[0] = 125.0

        result = pipeline.run(
            ["quality-check"],
            cwd=tmp_path,
            cap=stop_quality.CHECK_TIMEOUT,
            label="quality-check",
        )

        assert result is not None
        assert observed_timeouts == [25]

    def test_exhausted_budget_skips_later_processes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        now = [100.0]
        pipeline = stop_quality.QualityPipeline.start(timeout=50, clock=lambda: now[0])

        def run(_command: list[str], **_kwargs: object) -> CmdResult:
            message = "process must not start after the deadline"
            raise AssertionError(message)

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)
        now[0] = 150.0

        result = pipeline.run(
            ["later-check"],
            cwd=tmp_path,
            cap=stop_quality.CHECK_TIMEOUT,
            label="later-check",
        )

        assert result is None
        assert pipeline.advisories == [
            "later-check: skipped because the pipeline deadline was exhausted",
        ]

    def test_timed_out_process_is_named_in_advisory(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pipeline = stop_quality.QualityPipeline.start(timeout=50, clock=lambda: 100.0)

        def run(_command: list[str], **_kwargs: object) -> CmdResult:
            return CmdResult(stdout="", stderr="", returncode=-1, timed_out=True)

        monkeypatch.setattr(stop_quality.proc, "run_cmd", run)

        pipeline.run(
            ["slow-check"],
            cwd=tmp_path,
            cap=stop_quality.FORMAT_TIMEOUT,
            label="slow-check",
        )

        message = stop_quality.render_message([], pipeline.advisories)
        assert "slow-check: timed out after 15s" in message


class TestMain:
    def test_empty_input_skips_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        monkeypatch.setattr(
            stop_quality,
            "collect_git_changes",
            lambda _cwd: (_ for _ in ()).throw(AssertionError),
        )
        assert stop_quality.main() == 0

    def test_active_stop_hook_skips_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": True})))
        monkeypatch.setattr(
            stop_quality,
            "collect_git_changes",
            lambda _cwd: (_ for _ in ()).throw(AssertionError),
        )
        assert stop_quality.main() == 0

    def test_formats_before_linting_and_writes_advisory_context(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "changed.py"
        target.write_text("", encoding="utf-8")
        changes = stop_quality.ChangeSet(root=tmp_path, files=(target,))
        events: list[str] = []
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))
        monkeypatch.setattr(
            stop_quality,
            "collect_git_changes",
            lambda _cwd, _pipeline: changes,
        )
        monkeypatch.setattr(
            stop_quality,
            "format_changes",
            lambda _changes, _pipeline: events.append("format"),
        )

        def lint(
            _changes: stop_quality.ChangeSet,
            _pipeline: stop_quality.QualityPipeline,
        ) -> list[str]:
            events.append("lint")
            return ["ruff:\nchanged.py:1:1: F401"]

        monkeypatch.setattr(stop_quality, "lint_changes", lint)
        stdout = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout)

        assert stop_quality.main() == 0
        assert events == ["format", "lint"]
        payload = json.loads(stdout.getvalue())
        assert "stop-quality" in payload["additionalContext"]
        assert "F401" in payload["additionalContext"]

    def test_no_changed_files_is_silent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))
        monkeypatch.setattr(
            stop_quality,
            "collect_git_changes",
            lambda _cwd, _pipeline: stop_quality.ChangeSet(root=tmp_path, files=()),
        )
        stdout = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout)
        assert stop_quality.main() == 0
        assert stdout.getvalue() == ""

    def test_incomplete_change_discovery_writes_advisory_context(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"stop_hook_active": False})))

        def collect(
            _cwd: Path,
            pipeline: stop_quality.QualityPipeline,
        ) -> stop_quality.ChangeSet | None:
            pipeline.advisories.append(
                "Git tracked-change discovery: skipped because the pipeline deadline was exhausted",
            )
            return None

        monkeypatch.setattr(stop_quality, "collect_git_changes", collect)
        stdout = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout)

        assert stop_quality.main() == 0
        payload = json.loads(stdout.getvalue())
        assert "Git tracked-change discovery" in payload["additionalContext"]
