from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stop_quality
from _claude_lib import paths, session_state
from _claude_lib.proc import CmdResult


def _ok(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _fail(stdout: str = "") -> CmdResult:
    return CmdResult(stdout=stdout, stderr="", returncode=1, timed_out=False)


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> session_state.SessionState:
    monkeypatch.setattr(paths, "temp_roots", lambda: (tmp_path / "scratch",))
    return session_state.SessionState(tmp_path / "state" / "sess-1")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


class TestCollectSessionChanges:
    def test_only_files_the_session_edited_are_collected(
        self,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        repo = _repo(tmp_path)
        edited = repo / "pkg" / "edited.py"
        edited.parent.mkdir()
        edited.write_text("x = 1\n", encoding="utf-8")
        (repo / "users_own_dirty_work.py").write_text("y = 2\n", encoding="utf-8")
        state.record_edit(edited)

        changes = stop_quality.collect_session_changes(state, repo / "pkg")

        assert changes.root == repo.resolve()
        assert changes.files == (edited.resolve(),)

    def test_deleted_temp_and_out_of_project_files_are_dropped(
        self,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        repo = _repo(tmp_path)
        deleted = repo / "deleted.py"
        deleted.write_text("", encoding="utf-8")
        scratch = tmp_path / "scratch" / "probe.py"
        scratch.parent.mkdir()
        scratch.write_text("", encoding="utf-8")
        neighbour = tmp_path / "other-repo" / "x.py"
        neighbour.parent.mkdir()
        neighbour.write_text("", encoding="utf-8")
        for file_path in (deleted, scratch, neighbour):
            state.record_edit(file_path)
        deleted.unlink()

        assert stop_quality.collect_session_changes(state, repo).files == ()

    def test_cwd_outside_a_repository_is_its_own_project(
        self,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        workdir = tmp_path / "plain"
        workdir.mkdir()
        target = workdir / "a.py"
        target.write_text("", encoding="utf-8")
        state.record_edit(target)

        changes = stop_quality.collect_session_changes(state, workdir)

        assert changes.root == workdir.resolve()
        assert changes.files == (target.resolve(),)


class TestBatching:
    def test_only_go_files_are_formatted_and_with_goimports_local(
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

        writers = [call for call in calls if call[:3] != ["go", "env", "GOPATH"]]
        assert len(writers) == 1
        assert writers[0][0].endswith("goimports")
        assert writers[0][1:3] == ["-local", "example.com/project"]
        assert set(writers[0][4:]) == {str(tmp_path / "a.go"), str(tmp_path / "b.go")}

    def test_checkers_receive_one_batch_per_project(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "go.mod").write_text("module example.com/project\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\n[tool.pyrefly]\n",
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
            ("uv", "run", "pyrefly", "check"),
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

    def test_ruff_only_python_project_does_not_activate_pyrefly(
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

    def test_python_without_config_does_not_activate_pyrefly(
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
    @staticmethod
    def _run(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> str:
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        stdout = io.StringIO()
        monkeypatch.setattr(sys, "stdout", stdout)
        assert stop_quality.main() == 0
        return stdout.getvalue()

    @staticmethod
    def _session(
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> tuple[Path, Path, dict[str, object]]:
        monkeypatch.setattr(session_state, "state_root", lambda: state.directory.parent)
        repo = _repo(tmp_path)
        target = repo / "changed.py"
        target.write_text("x = 1\n", encoding="utf-8")
        state.record_edit(target)
        payload: dict[str, object] = {
            "session_id": "sess-1",
            "cwd": str(repo),
            "stop_hook_active": False,
        }
        return repo, target, payload

    @staticmethod
    def _counting_lint(
        monkeypatch: pytest.MonkeyPatch,
        issues: list[str],
    ) -> list[stop_quality.ChangeSet]:
        runs: list[stop_quality.ChangeSet] = []

        def lint(
            changes: stop_quality.ChangeSet,
            _pipeline: stop_quality.QualityPipeline,
        ) -> list[str]:
            runs.append(changes)
            return list(issues)

        monkeypatch.setattr(stop_quality, "lint_changes", lint)
        monkeypatch.setattr(
            stop_quality, "format_changes", lambda _c: stop_quality.QualityPipeline.start()
        )
        return runs

    def test_empty_input_skips_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            stop_quality,
            "collect_session_changes",
            lambda *_a: (_ for _ in ()).throw(AssertionError),
        )
        assert self._run(monkeypatch, {}) == ""

    def test_active_stop_hook_skips_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            stop_quality,
            "collect_session_changes",
            lambda *_a: (_ for _ in ()).throw(AssertionError),
        )
        assert self._run(monkeypatch, {"session_id": "s", "stop_hook_active": True}) == ""

    def test_missing_session_id_is_silent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            stop_quality,
            "collect_session_changes",
            lambda *_a: (_ for _ in ()).throw(AssertionError),
        )
        assert self._run(monkeypatch, {"stop_hook_active": False}) == ""

    def test_reports_issues_and_asks_to_fix_only_introduced_ones(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        _repo_root, target, payload = self._session(monkeypatch, tmp_path, state)
        runs = self._counting_lint(monkeypatch, ["ruff:\nchanged.py:1:1: F401"])

        context = json.loads(self._run(monkeypatch, payload))["additionalContext"]

        assert runs[0].files == (target.resolve(),)
        assert "files this session edited" in context
        assert "F401" in context
        assert "Fix only the issues your change introduced" in context
        assert "list them in your report" in context

    def test_unchanged_files_are_not_rechecked_on_the_next_stop(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        _repo_root, _target, payload = self._session(monkeypatch, tmp_path, state)
        runs = self._counting_lint(monkeypatch, ["ruff:\nchanged.py:1:1: F401"])

        first = self._run(monkeypatch, payload)
        second = self._run(monkeypatch, payload)

        assert first
        assert second == ""
        assert len(runs) == 1

    def test_identical_report_after_a_new_edit_is_not_reinjected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        repo, target, payload = self._session(monkeypatch, tmp_path, state)
        runs = self._counting_lint(monkeypatch, ["ruff:\nchanged.py:1:1: F401"])

        first = self._run(monkeypatch, payload)
        other = repo / "other.md"
        other.write_text("notes\n", encoding="utf-8")
        state.record_edit(other)
        target.write_text("x = 1\ny = 2\n", encoding="utf-8")
        second = self._run(monkeypatch, payload)

        assert first
        assert second == ""
        assert len(runs) == 2

    def test_clean_session_files_are_silent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        _repo_root, _target, payload = self._session(monkeypatch, tmp_path, state)
        self._counting_lint(monkeypatch, [])
        assert self._run(monkeypatch, payload) == ""

    def test_session_without_edits_runs_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        state: session_state.SessionState,
    ) -> None:
        monkeypatch.setattr(session_state, "state_root", lambda: state.directory.parent)
        repo = _repo(tmp_path)
        (repo / "users_own_dirty_work.py").write_text("import os\n", encoding="utf-8")
        runs = self._counting_lint(monkeypatch, ["should not run"])

        assert self._run(monkeypatch, {"session_id": "sess-1", "cwd": str(repo)}) == ""
        assert runs == []


class TestContainers:
    def test_hadolint_info_and_style_findings_are_dropped(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM ubuntu\n", encoding="utf-8")
        output = (
            "Dockerfile:1 DL3006 warning: Always tag the version\n"
            "Dockerfile:2 DL3015 info: Avoid additional packages\n"
            "Dockerfile:3 DL3048 style: Invalid label key\n"
        )
        monkeypatch.setattr(stop_quality.proc, "run_cmd", lambda *_a, **_k: _fail(output))
        changes = stop_quality.ChangeSet(root=tmp_path, files=(dockerfile,))

        issues = stop_quality.lint_changes(changes)

        assert issues == ["hadolint:\nDockerfile:1 DL3006 warning: Always tag the version"]

    def test_hadolint_with_only_info_findings_reports_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM ubuntu\n", encoding="utf-8")
        output = "Dockerfile:2 DL3015 info: Avoid additional packages\n"
        monkeypatch.setattr(stop_quality.proc, "run_cmd", lambda *_a, **_k: _fail(output))
        changes = stop_quality.ChangeSet(root=tmp_path, files=(dockerfile,))

        assert stop_quality.lint_changes(changes) == []
