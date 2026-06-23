#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, io_json, proc

IMAGE_NAME: Final[str] = "claude-sandbox"
TARGET_DIR_NAME: Final[str] = ".devcontainer"

USAGE: Final[str] = (
    "Usage: claude_devcontainer.py <command> [options]\n"
    "\n"
    "Commands:\n"
    "  init [--minimal]   Copy devcontainer template to current project\n"
    "  build              Build the devcontainer image\n"
    "  run [options]      Run Claude Code in the container\n"
    "\n"
    "Run options:\n"
    "  --bypass           Add --dangerously-skip-permissions to Claude Code\n"
    "  --shell            Drop into zsh instead of launching Claude Code\n"
)


@dataclass(frozen=True)
class InitArgs:
    minimal: bool


@dataclass(frozen=True)
class RunArgs:
    bypass: bool
    shell: bool


@dataclass(frozen=True)
class ParseFailure:
    message: str


@dataclass
class DetectionReport:
    detected: list[str] = field(default_factory=list)


def template_dir() -> Path:
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "templates" / "devcontainer"


def parse_init(argv: list[str]) -> InitArgs | ParseFailure:
    if not argv:
        return InitArgs(minimal=False)
    if len(argv) == 1 and argv[0] == "--minimal":
        return InitArgs(minimal=True)
    return ParseFailure(f"Unknown option(s) for init: {' '.join(argv)}")


def parse_run(argv: list[str]) -> RunArgs | ParseFailure:
    bypass = False
    shell = False
    for arg in argv:
        if arg == "--bypass":
            bypass = True
        elif arg == "--shell":
            shell = True
        else:
            return ParseFailure(f"Unknown option: {arg}")
    return RunArgs(bypass=bypass, shell=shell)


def detect_languages(cwd: Path) -> DetectionReport:
    report = DetectionReport()
    if (cwd / "go.mod").is_file():
        report.detected.append("Go")
    if (
        (cwd / "pyproject.toml").is_file()
        or (cwd / "setup.py").is_file()
        or (cwd / "requirements.txt").is_file()
    ):
        report.detected.append("Python")
    if (cwd / "Cargo.toml").is_file():
        report.detected.append("Rust")
    if (cwd / "dune-project").is_file() or any(cwd.glob("*.opam")):
        report.detected.append("OCaml")
    return report


def _language_build_arg(language: str) -> str:
    return {
        "Go": "INSTALL_GO",
        "Python": "INSTALL_PYTHON",
        "Rust": "INSTALL_RUST",
        "OCaml": "INSTALL_OCAML",
    }[language]


def update_build_args(json_path: Path, args_to_set: dict[str, str]) -> None:
    data = io_json.load_json(json_path)
    build_raw = data.get("build")
    build: dict[str, object] = dict(build_raw) if isinstance(build_raw, dict) else {}
    args_raw = build.get("args")
    args_dict: dict[str, object] = dict(args_raw) if isinstance(args_raw, dict) else {}
    args_dict.update(args_to_set)
    build["args"] = args_dict
    data["build"] = build
    io_json.dump_json(json_path, data)


def read_build_args(json_path: Path) -> dict[str, str]:
    if not json_path.is_file():
        return {}
    data = io_json.load_json(json_path)
    build = data.get("build")
    if not isinstance(build, dict):
        return {}
    args = build.get("args")
    if not isinstance(args, dict):
        return {}
    return {
        key: value for key, value in args.items() if isinstance(key, str) and isinstance(value, str)
    }


def _copy_template(template: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(template, target)


@dataclass
class CmdOutcome:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def cmd_init(args: InitArgs, cwd: Path) -> CmdOutcome:
    template = template_dir()
    if not template.is_dir():
        return CmdOutcome(
            exit_code=1,
            stderr=(
                f"ERROR: Template not found at {template}\n"
                "Run your devbox Ansible playbook to deploy templates.\n"
            ),
        )

    target = cwd / TARGET_DIR_NAME
    warning = ""
    if target.exists():
        warning = f"WARNING: {target.name} already exists. Overwriting.\n"

    _copy_template(template, target)

    devcontainer_json = target / "devcontainer.json"
    if args.minimal:
        body = "Minimal mode: all optional languages disabled.\n"
    else:
        detection = detect_languages(cwd)
        if detection.detected and devcontainer_json.is_file():
            build_args = {_language_build_arg(lang): "true" for lang in detection.detected}
            update_build_args(devcontainer_json, build_args)
        if detection.detected:
            body = f"Detected: {' '.join(detection.detected)}\n"
        else:
            body = "No language-specific files detected. Node.js available by default.\n"

    msg = (
        warning
        + body
        + f"Devcontainer template copied to {target.name}\n"
        + "\n"
        + "Next steps:\n"
        + "  claude-devcontainer build\n"
        + "  claude-devcontainer run\n"
    )
    return CmdOutcome(exit_code=0, stdout=msg)


def cmd_build(cwd: Path) -> CmdOutcome:
    target = cwd / TARGET_DIR_NAME
    if not (target / "Dockerfile").is_file():
        return CmdOutcome(
            exit_code=1,
            stderr=(
                f"ERROR: No Dockerfile found in {target.name}."
                " Run 'claude_devcontainer.py init' first.\n"
            ),
        )

    build_args = read_build_args(target / "devcontainer.json")
    docker_cmd: list[str] = ["docker", "build"]
    for k, v in build_args.items():
        docker_cmd.extend(["--build-arg", f"{k}={v}"])
    docker_cmd.extend(["-t", IMAGE_NAME, str(target)])

    result = proc.run_cmd(docker_cmd, timeout=600)
    if not result.success:
        return CmdOutcome(
            exit_code=result.returncode if result.returncode != 0 else 1,
            stderr=f"docker build failed: {result.stderr}",
            stdout=f"Building image: {IMAGE_NAME}\n",
        )
    return CmdOutcome(
        exit_code=0,
        stdout=f"Building image: {IMAGE_NAME}\nImage built: {IMAGE_NAME}\n",
    )


def _image_exists(image: str) -> bool:
    result = proc.run_cmd(["docker", "image", "inspect", image], timeout=30)
    return result.success


def _run_args(cwd: Path) -> list[str]:
    home = os.environ.get("HOME") or str(Path.home())
    settings = Path(home) / ".claude" / "settings.json"
    return [
        "--rm",
        "-it",
        "--cap-add",
        "NET_ADMIN",
        "--cap-add",
        "NET_RAW",
        "--hostname",
        "claude-sandbox",
        "-v",
        f"{cwd}:/home/node/workspace",
        "-v",
        f"{settings}:/home/node/.claude/settings.json:ro",
        "-v",
        "claude-shell-history:/home/node/.shell_history",
        "-w",
        "/home/node/workspace",
    ]


def cmd_run(args: RunArgs, cwd: Path) -> CmdOutcome:
    if not _image_exists(IMAGE_NAME):
        return CmdOutcome(
            exit_code=1,
            stderr=(
                f"ERROR: Image {IMAGE_NAME} not found. Run 'claude_devcontainer.py build' first.\n"
            ),
        )

    docker_cmd: list[str] = ["docker", "run", *_run_args(cwd)]
    if os.environ.get("ANTHROPIC_API_KEY"):
        docker_cmd.extend(["-e", "ANTHROPIC_API_KEY"])

    if args.shell:
        docker_cmd.append(IMAGE_NAME)
        docker_cmd.append("zsh")
        stdout = "Dropping into zsh...\n"
    else:
        docker_cmd.append(IMAGE_NAME)
        docker_cmd.append("claude")
        stdout = ""
        if args.bypass:
            docker_cmd.append("--dangerously-skip-permissions")
            stdout = "WARNING: Running with --dangerously-skip-permissions\n"

    result = proc.run_cmd(docker_cmd, timeout=86_400)
    return CmdOutcome(
        exit_code=result.returncode,
        stdout=stdout + result.stdout,
        stderr=result.stderr,
    )


def _dispatch_init(rest: list[str], cwd: Path) -> CmdOutcome:
    init = parse_init(rest)
    if isinstance(init, ParseFailure):
        return CmdOutcome(exit_code=1, stderr=init.message + "\n" + USAGE)
    return cmd_init(init, cwd)


def _dispatch_build(rest: list[str], cwd: Path) -> CmdOutcome:
    if rest:
        return CmdOutcome(
            exit_code=1,
            stderr=f"build takes no options, got: {' '.join(rest)}\n",
        )
    return cmd_build(cwd)


def _dispatch_run(rest: list[str], cwd: Path) -> CmdOutcome:
    run = parse_run(rest)
    if isinstance(run, ParseFailure):
        return CmdOutcome(exit_code=1, stderr=run.message + "\n" + USAGE)
    return cmd_run(run, cwd)


CommandHandler = Callable[[list[str], Path], CmdOutcome]

_DISPATCH_TABLE: Final[dict[str, CommandHandler]] = {
    "init": _dispatch_init,
    "build": _dispatch_build,
    "run": _dispatch_run,
}


def dispatch(argv: list[str], cwd: Path) -> CmdOutcome:
    if not argv or argv[0] in ("-h", "--help", "help"):
        return CmdOutcome(exit_code=0 if argv else 1, stdout=USAGE)
    handler = _DISPATCH_TABLE.get(argv[0])
    if handler is None:
        return CmdOutcome(exit_code=1, stderr=f"Unknown command: {argv[0]}\n" + USAGE)
    return handler(argv[1:], cwd)


def main(argv: list[str] | None = None) -> int:
    env.setup()
    args = argv if argv is not None else sys.argv[1:]
    outcome = dispatch(args, Path.cwd())
    if outcome.stdout:
        sys.stdout.write(outcome.stdout)
    if outcome.stderr:
        sys.stderr.write(outcome.stderr)
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())
