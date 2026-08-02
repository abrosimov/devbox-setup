from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_devcontainer as cdc
from _claude_lib import proc

if TYPE_CHECKING:
    import pytest


def _ok(stdout: str = "") -> proc.CmdResult:
    return proc.CmdResult(stdout=stdout, stderr="", returncode=0, timed_out=False)


def _err(returncode: int = 1, stderr: str = "boom") -> proc.CmdResult:
    return proc.CmdResult(stdout="", stderr=stderr, returncode=returncode, timed_out=False)


def _make_template(template_root: Path) -> Path:
    template_root.mkdir(parents=True)
    (template_root / "Dockerfile").write_text("FROM node:20-bookworm\n", encoding="utf-8")
    (template_root / "devcontainer.json").write_text(
        json.dumps(
            {
                "name": "claude",
                "build": {
                    "args": {
                        "INSTALL_GO": "false",
                        "INSTALL_PYTHON": "false",
                        "INSTALL_RUST": "false",
                        "INSTALL_OCAML": "false",
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (template_root / "init-firewall.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    return template_root


def test_parse_init_default() -> None:
    parsed = cdc.parse_init([])
    assert isinstance(parsed, cdc.InitArgs)
    assert not parsed.minimal


def test_parse_init_minimal() -> None:
    parsed = cdc.parse_init(["--minimal"])
    assert isinstance(parsed, cdc.InitArgs)
    assert parsed.minimal


def test_parse_init_unknown() -> None:
    parsed = cdc.parse_init(["--bogus"])
    assert isinstance(parsed, cdc.ParseFailure)


def test_parse_run_default() -> None:
    parsed = cdc.parse_run([])
    assert isinstance(parsed, cdc.RunArgs)
    assert not parsed.bypass
    assert not parsed.shell


def test_parse_run_both_flags() -> None:
    parsed = cdc.parse_run(["--bypass", "--shell"])
    assert isinstance(parsed, cdc.RunArgs)
    assert parsed.bypass
    assert parsed.shell


def test_parse_run_unknown() -> None:
    parsed = cdc.parse_run(["--unknown"])
    assert isinstance(parsed, cdc.ParseFailure)


def test_detect_languages_empty(tmp_path: Path) -> None:
    report = cdc.detect_languages(tmp_path)
    assert report.detected == []


def test_detect_languages_go(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    assert report.detected == ["Go"]


def test_detect_languages_python_multiple_markers(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "setup.py").write_text("", encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    # Single 'Python' regardless of how many python markers exist.
    assert report.detected == ["Python"]


def test_detect_languages_rust(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    assert report.detected == ["Rust"]


def test_detect_languages_ocaml_dune(tmp_path: Path) -> None:
    (tmp_path / "dune-project").write_text("(lang dune 3.0)\n", encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    assert report.detected == ["OCaml"]


def test_detect_languages_ocaml_opam(tmp_path: Path) -> None:
    (tmp_path / "my-pkg.opam").write_text('opam-version: "2.0"\n', encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    assert report.detected == ["OCaml"]


def test_detect_languages_polyglot(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
    report = cdc.detect_languages(tmp_path)
    assert set(report.detected) == {"Go", "Python", "Rust"}


def test_update_build_args_adds_keys(tmp_path: Path) -> None:
    path = tmp_path / "devcontainer.json"
    path.write_text(json.dumps({"name": "x", "build": {"args": {"FOO": "bar"}}}), encoding="utf-8")
    cdc.update_build_args(path, {"INSTALL_GO": "true"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["build"]["args"]["FOO"] == "bar"
    assert data["build"]["args"]["INSTALL_GO"] == "true"
    assert data["name"] == "x"


def test_update_build_args_creates_build_section(tmp_path: Path) -> None:
    path = tmp_path / "devcontainer.json"
    path.write_text(json.dumps({"name": "x"}), encoding="utf-8")
    cdc.update_build_args(path, {"INSTALL_PYTHON": "true"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["build"]["args"]["INSTALL_PYTHON"] == "true"


def test_update_build_args_overrides_existing(tmp_path: Path) -> None:
    path = tmp_path / "devcontainer.json"
    path.write_text(json.dumps({"build": {"args": {"INSTALL_GO": "false"}}}), encoding="utf-8")
    cdc.update_build_args(path, {"INSTALL_GO": "true"})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["build"]["args"]["INSTALL_GO"] == "true"


def test_read_build_args_missing_file(tmp_path: Path) -> None:
    assert cdc.read_build_args(tmp_path / "absent.json") == {}


def test_read_build_args_filters_non_strings(tmp_path: Path) -> None:
    path = tmp_path / "devcontainer.json"
    path.write_text(
        json.dumps({"build": {"args": {"FOO": "bar", "X": 42, "Y": None}}}),
        encoding="utf-8",
    )
    assert cdc.read_build_args(path) == {"FOO": "bar"}


def test_read_build_args_corrupt_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "devcontainer.json"
    path.write_text(json.dumps({"build": "not-a-dict"}), encoding="utf-8")
    assert cdc.read_build_args(path) == {}


def test_cmd_init_missing_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    outcome = cdc.cmd_init(cdc.InitArgs(minimal=False), tmp_path)
    assert outcome.exit_code == 1
    assert "Template not found" in outcome.stderr


def test_cmd_init_copies_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_template(home / ".claude" / "templates" / "devcontainer")

    project = tmp_path / "project"
    project.mkdir()
    outcome = cdc.cmd_init(cdc.InitArgs(minimal=False), project)
    assert outcome.exit_code == 0

    target = project / cdc.TARGET_DIR_NAME
    assert (target / "Dockerfile").is_file()
    assert (target / "devcontainer.json").is_file()


def test_cmd_init_detects_python(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_template(home / ".claude" / "templates" / "devcontainer")

    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    outcome = cdc.cmd_init(cdc.InitArgs(minimal=False), project)
    assert outcome.exit_code == 0
    assert "Python" in outcome.stdout

    data = json.loads((project / cdc.TARGET_DIR_NAME / "devcontainer.json").read_text())
    assert data["build"]["args"]["INSTALL_PYTHON"] == "true"
    assert data["build"]["args"]["INSTALL_GO"] == "false"


def test_cmd_init_minimal_skips_detection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_template(home / ".claude" / "templates" / "devcontainer")

    project = tmp_path / "project"
    project.mkdir()
    (project / "go.mod").write_text("", encoding="utf-8")

    outcome = cdc.cmd_init(cdc.InitArgs(minimal=True), project)
    assert outcome.exit_code == 0
    assert "Minimal mode" in outcome.stdout

    data = json.loads((project / cdc.TARGET_DIR_NAME / "devcontainer.json").read_text())
    # Minimal: build args remain at template defaults (all 'false').
    assert data["build"]["args"]["INSTALL_GO"] == "false"


def test_cmd_init_overwrites_existing_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _make_template(home / ".claude" / "templates" / "devcontainer")

    project = tmp_path / "project"
    project.mkdir()
    (project / cdc.TARGET_DIR_NAME).mkdir()
    (project / cdc.TARGET_DIR_NAME / "stale.txt").write_text("old", encoding="utf-8")

    outcome = cdc.cmd_init(cdc.InitArgs(minimal=False), project)
    assert outcome.exit_code == 0
    assert "WARNING" in outcome.stdout
    assert not (project / cdc.TARGET_DIR_NAME / "stale.txt").exists()


def test_cmd_build_no_dockerfile(tmp_path: Path) -> None:
    (tmp_path / cdc.TARGET_DIR_NAME).mkdir()
    outcome = cdc.cmd_build(tmp_path)
    assert outcome.exit_code == 1
    assert "No Dockerfile" in outcome.stderr


def test_cmd_build_invokes_docker(tmp_path: Path) -> None:
    target = tmp_path / cdc.TARGET_DIR_NAME
    target.mkdir()
    (target / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (target / "devcontainer.json").write_text(
        json.dumps({"build": {"args": {"INSTALL_GO": "true"}}}), encoding="utf-8"
    )

    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> proc.CmdResult:
        captured.append(cmd)
        return _ok()

    with mock.patch.object(proc, "run_cmd", side_effect=fake_run):
        outcome = cdc.cmd_build(tmp_path)

    assert outcome.exit_code == 0
    assert "Image built" in outcome.stdout
    assert captured, "docker build was not invoked"
    cmd = captured[0]
    assert cmd[:2] == ["docker", "build"]
    assert "--build-arg" in cmd
    assert "INSTALL_GO=true" in cmd
    assert "-t" in cmd
    assert cdc.IMAGE_NAME in cmd
    assert str(target) in cmd


def test_cmd_build_propagates_docker_failure(tmp_path: Path) -> None:
    target = tmp_path / cdc.TARGET_DIR_NAME
    target.mkdir()
    (target / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    with mock.patch.object(proc, "run_cmd", return_value=_err(stderr="docker error")):
        outcome = cdc.cmd_build(tmp_path)

    assert outcome.exit_code != 0
    assert "docker build failed" in outcome.stderr


def test_cmd_run_image_missing(tmp_path: Path) -> None:
    with mock.patch.object(proc, "run_cmd", return_value=_err()):
        outcome = cdc.cmd_run(cdc.RunArgs(bypass=False, shell=False), tmp_path)
    assert outcome.exit_code == 1
    assert "not found" in outcome.stderr


def test_cmd_run_default_invokes_claude(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> proc.CmdResult:
        captured.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _ok()
        return _ok(stdout="claude output")

    with mock.patch.object(proc, "run_cmd", side_effect=fake_run):
        outcome = cdc.cmd_run(cdc.RunArgs(bypass=False, shell=False), tmp_path)

    assert outcome.exit_code == 0
    # Second invocation = docker run
    run_cmd = captured[1]
    assert run_cmd[:2] == ["docker", "run"]
    assert cdc.IMAGE_NAME in run_cmd
    assert "claude" in run_cmd
    assert "--dangerously-skip-permissions" not in run_cmd
    assert "zsh" not in run_cmd


def test_cmd_run_bypass_adds_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> proc.CmdResult:
        captured.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _ok()
        return _ok()

    with mock.patch.object(proc, "run_cmd", side_effect=fake_run):
        outcome = cdc.cmd_run(cdc.RunArgs(bypass=True, shell=False), tmp_path)

    assert outcome.exit_code == 0
    assert "WARNING" in outcome.stdout
    run_cmd = captured[1]
    assert "--dangerously-skip-permissions" in run_cmd


def test_cmd_run_shell_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> proc.CmdResult:
        captured.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _ok()
        return _ok()

    args = cdc.RunArgs(bypass=False, shell=True)  # noqa: S604 — dataclass field, not subprocess kwarg
    with mock.patch.object(proc, "run_cmd", side_effect=fake_run):
        outcome = cdc.cmd_run(args, tmp_path)

    assert outcome.exit_code == 0
    assert "zsh" in outcome.stdout.lower()
    run_cmd = captured[1]
    assert "zsh" in run_cmd
    assert "claude" not in run_cmd


def test_cmd_run_passes_api_key_when_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kw: object) -> proc.CmdResult:
        captured.append(cmd)
        if cmd[:3] == ["docker", "image", "inspect"]:
            return _ok()
        return _ok()

    with mock.patch.object(proc, "run_cmd", side_effect=fake_run):
        cdc.cmd_run(cdc.RunArgs(bypass=False, shell=False), tmp_path)

    run_cmd = captured[1]
    assert "ANTHROPIC_API_KEY" in run_cmd
    # The secret value itself is never put on the command line.
    assert "secret" not in run_cmd


def test_dispatch_help_no_args(tmp_path: Path) -> None:
    outcome = cdc.dispatch([], tmp_path)
    assert outcome.exit_code == 1
    assert "Usage:" in outcome.stdout


def test_dispatch_help_explicit(tmp_path: Path) -> None:
    outcome = cdc.dispatch(["--help"], tmp_path)
    assert outcome.exit_code == 0
    assert "Usage:" in outcome.stdout


def test_dispatch_unknown_command(tmp_path: Path) -> None:
    outcome = cdc.dispatch(["frobnicate"], tmp_path)
    assert outcome.exit_code == 1
    assert "Unknown command" in outcome.stderr


def test_dispatch_init_with_bad_args(tmp_path: Path) -> None:
    outcome = cdc.dispatch(["init", "--bogus"], tmp_path)
    assert outcome.exit_code == 1
    assert "Unknown" in outcome.stderr


def test_dispatch_build_rejects_args(tmp_path: Path) -> None:
    outcome = cdc.dispatch(["build", "--bogus"], tmp_path)
    assert outcome.exit_code == 1
    assert "no options" in outcome.stderr


def test_dispatch_run_with_bad_args(tmp_path: Path) -> None:
    outcome = cdc.dispatch(["run", "--bogus"], tmp_path)
    assert outcome.exit_code == 1
    assert "Unknown option" in outcome.stderr


def test_main_help_to_stdout(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(Path.cwd())
    code = cdc.main(["--help"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Usage:" in out


def test_main_unknown_to_stderr(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(Path.cwd())
    code = cdc.main(["nope"])
    assert code == 1
    err = capsys.readouterr().err
    assert "Unknown command" in err
