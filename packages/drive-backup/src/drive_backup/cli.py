"""Command line entry point: ``drive-backup run`` and ``drive-backup check-config``."""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
from pathlib import Path

from . import __version__, config
from .gitrepo import GitRepo
from .notify import notify
from .runner import Backup, LockedError, RunOptions, run_lock

EXIT_OK, EXIT_FAILED, EXIT_CONFIG, EXIT_LOCKED = 0, 1, 2, 75  # 75 = EX_TEMPFAIL


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drive-backup", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="config file (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="archive, commit and push")
    run.add_argument("--profile", help=f"archive name prefix (default: ${config.PROFILE_ENV})")
    run.add_argument(
        "--no-defer", action="store_true", help="do not wait for live sessions to exit"
    )
    run.add_argument("--no-push", action="store_true", help="commit locally, do not push")

    sub.add_parser("check-config", help="validate the config and print the resolved plan")
    return parser


def _lock_path(env: dict[str, str]) -> Path:
    base = env.get("XDG_STATE_HOME") or str(Path(env.get("HOME", "~")) / ".local/state")
    return Path(base) / "drive-backup" / "run.lock"


def _setup_logging() -> io.StringIO:
    buffer = io.StringIO()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%dT%H:%M:%S%z")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for stream in (sys.stderr, buffer):
        handler = logging.StreamHandler(stream)
        handler.setFormatter(fmt)
        root.addHandler(handler)
    return buffer


def _check_config(cfg: config.Config) -> int:
    def mark(path: Path) -> str:
        return "" if path.exists() else "  (missing)"

    print(f"repo_dir: {cfg.repo_dir}{mark(cfg.repo_dir)}")
    print(f"zstd_level: {cfg.zstd_level}")
    print(f"defer: every {cfg.defer.interval_minutes}m, up to {cfg.defer.max_wait_minutes}m")
    for spec in cfg.dirs:
        print(f"- {spec.name}: {spec.path}{mark(spec.path)}")
        if spec.busy:
            print(f"    busy: {', '.join(spec.busy)}")
        for pattern in spec.exclude:
            print(f"    exclude: {pattern}")
    return EXIT_OK


def _run(cfg: config.Config, args: argparse.Namespace, env: dict[str, str]) -> int:
    profile = args.profile or env.get(config.PROFILE_ENV, "")
    try:
        config.validate_token("profile", profile)
    except config.ConfigError as exc:
        print(f"drive-backup: {exc} (set ${config.PROFILE_ENV} or --profile)", file=sys.stderr)
        return EXIT_CONFIG

    buffer = _setup_logging()
    try:
        with run_lock(_lock_path(env)):
            options = RunOptions(profile=profile, defer=not args.no_defer, push=not args.no_push)
            report = Backup(cfg, options, GitRepo(cfg.repo_dir)).run(buffer)
    except LockedError as exc:
        logging.getLogger("drive_backup").warning("%s", exc)
        return EXIT_LOCKED
    if not report.ok:
        notify("drive-backup failed", str(report.error))
        return EXIT_FAILED
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    env = dict(os.environ)
    path = args.config or config.default_config_path(env)
    try:
        cfg = config.load(path, env)
    except config.ConfigError as exc:
        print(f"drive-backup: {exc}", file=sys.stderr)
        if args.command == "run":
            notify("drive-backup: bad config", str(exc))
        return EXIT_CONFIG
    if args.command == "check-config":
        return _check_config(cfg)
    return _run(cfg, args, env)


if __name__ == "__main__":
    sys.exit(main())
