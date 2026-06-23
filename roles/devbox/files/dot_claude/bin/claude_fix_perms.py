#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env, io_json

SETTINGS_RELATIVE: Final[str] = ".claude/settings.local.json"

BASE_DENY: Final[list[str]] = [
    "Bash(rm *)",
    "Bash(rm -*)",
    "Bash(curl *)",
    "Bash(wget *)",
    "Bash(sudo *)",
    "Bash(git push *)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
    "Bash(git rebase *)",
    "Bash(git reset *)",
    "Bash(git reset --hard *)",
    "Bash(git commit --amend *)",
    "Bash(git tag *)",
    "Bash(git rm *)",
    "Bash(git mv *)",
    "Bash(git clean *)",
    "Bash(git checkout -- *)",
    "Bash(cat *>*)",
    "Bash(echo *>*)",
    "Bash(kill *)",
    "Bash(killall *)",
    "Bash(docker rm *)",
    "Bash(docker rmi *)",
    "Bash(pip uninstall *)",
    "Bash(gh pr close *)",
    "Bash(gh pr merge *)",
    "Bash(gh issue close *)",
    "Edit(.env)",
    "Edit(.env.*)",
    "Edit(**/.env)",
    "Edit(**/.env.*)",
    "Edit(**/secrets/**)",
    "Edit(**/*.pem)",
    "Edit(**/*.key)",
    "Edit(**/credentials*)",
    "Write(.env)",
    "Write(.env.*)",
    "Write(**/.env)",
    "Write(**/.env.*)",
    "Write(**/secrets/**)",
    "Write(**/*.pem)",
    "Write(**/*.key)",
    "Write(**/credentials*)",
]

BASE_ALLOW: Final[list[str]] = [
    "Task",
    "Read",
    "Read(**)",
    "Edit",
    "Edit(**)",
    "Write",
    "Write(**)",
    "NotebookEdit",
    "WebSearch",
    "WebFetch",
    "mcp__*",
    "Bash(go test *)",
    "Bash(go build *)",
    "Bash(go run *)",
    "Bash(go mod *)",
    "Bash(go vet *)",
    "Bash(go vet)",
    "Bash(go clean -cache)",
    "Bash(goimports *)",
    "Bash(golangci-lint *)",
    "Bash(mockery *)",
    "Bash(uv run *)",
    "Bash(uv sync *)",
    "Bash(uvx *)",
    "Bash(poetry run *)",
    "Bash(pytest *)",
    "Bash(ruff *)",
    "Bash(mypy *)",
    "Bash(python *)",
    "Bash(python3 *)",
    "Bash(pip install *)",
    "Bash(pip list *)",
    "Bash(pnpm *)",
    "Bash(npx *)",
    "Bash(node *)",
    "Bash(jsonnet *)",
    "Bash(jsonnetfmt *)",
    "Bash(jb *)",
    "Bash(buf *)",
    "Bash(make *)",
    "Bash(docker build *)",
    "Bash(docker run *)",
    "Bash(docker compose *)",
    "Bash(docker ps *)",
    "Bash(docker images *)",
    "Bash(docker logs *)",
    "Bash(gh pr view *)",
    "Bash(gh pr list *)",
    "Bash(gh pr diff *)",
    "Bash(gh pr checks *)",
    "Bash(gh issue view *)",
    "Bash(gh issue list *)",
    "Bash(gh api *)",
    "Bash(gh run *)",
    "Bash(git add *)",
    "Bash(git add .)",
    "Bash(git status *)",
    "Bash(git status)",
    "Bash(git diff *)",
    "Bash(git diff)",
    "Bash(git log *)",
    "Bash(git show *)",
    "Bash(git branch *)",
    "Bash(git branch)",
    "Bash(git blame *)",
    "Bash(git ls-files *)",
    "Bash(git ls-files)",
    "Bash(git ls-tree *)",
    "Bash(git rev-parse *)",
    "Bash(git stash *)",
    "Bash(git checkout -b *)",
    "Bash(git switch *)",
    "Bash(git remote *)",
    "Bash(git fetch *)",
    "Bash(git config --get *)",
    "Bash(git worktree list *)",
    "Bash(git worktree list)",
    "Bash(.claude/bin/*)",
    "Bash(ls *)",
    "Bash(ls)",
    "Bash(test *)",
    "Bash([ -f *)",
    "Bash([ -d *)",
    "Bash(mkdir *)",
    "Bash(wc *)",
    "Bash(stat *)",
    "Bash(file *)",
    "Bash(jq *)",
    "Bash(which *)",
    "Bash(pwd)",
    "Bash(head *)",
    "Bash(tail *)",
    "Bash(diff *)",
    "Bash(sort *)",
    "Bash(uniq *)",
    "Bash(cut *)",
    "Bash(tr *)",
    "Bash(awk *)",
    "Bash(sed *)",
    "Bash(xargs *)",
    "Bash(tee *)",
    "Bash(env *)",
    "Bash(date *)",
    "Bash(basename *)",
    "Bash(dirname *)",
]

GIT_WRITE_ALLOW: Final[list[str]] = [
    "Bash(git commit -m *)",
    "Bash(git merge --ff-only *)",
    "Bash(git merge --no-edit *)",
    "Bash(git switch -c *)",
    "Bash(git branch -d *)",
]

GIT_WRITE_DENY: Final[list[str]] = [
    "Bash(git merge main *)",
    "Bash(git merge master *)",
]

USAGE: Final[str] = (
    "Usage: claude_fix_perms.py [--with-git] [--go] [--python] [--node] [--all] [--no-detect]\n"
    "  Inject/merge permissions into .claude/settings.local.json\n"
    "\n"
    "Options:\n"
    "  --with-git   Add git write permissions (commit, merge, branch)\n"
    "  --go         Add Go toolchain permissions (reserved -- base covers these)\n"
    "  --python     Add Python toolchain permissions (reserved -- base covers these)\n"
    "  --node       Add Node toolchain permissions (reserved -- base covers these)\n"
    "  --all        Shortcut for --go --python --node\n"
    "  --no-detect  Skip auto-detection, only apply base rules + explicit flags\n"
    "\n"
    "Auto-detection (default): detects project type from marker files and applies\n"
    "the appropriate flags. Explicit flags merge on top of detected ones.\n"
)


@dataclass
class ParsedArgs:
    with_git: bool = False
    with_go: bool = False
    with_python: bool = False
    with_node: bool = False
    no_detect: bool = False
    show_usage: bool = False


@dataclass(frozen=True)
class ParseFailure:
    message: str


@dataclass
class DetectionResult:
    detected: list[str] = field(default_factory=list)


def parse_args(argv: list[str]) -> ParsedArgs | ParseFailure:
    args = ParsedArgs()
    for arg in argv:
        if arg == "--with-git":
            args.with_git = True
        elif arg == "--go":
            args.with_go = True
        elif arg == "--python":
            args.with_python = True
        elif arg == "--node":
            args.with_node = True
        elif arg == "--all":
            args.with_go = True
            args.with_python = True
            args.with_node = True
        elif arg == "--no-detect":
            args.no_detect = True
        elif arg in ("-h", "--help"):
            args.show_usage = True
        else:
            return ParseFailure(f"Unknown option: {arg}")
    return args


def detect_project(root: Path) -> DetectionResult:
    result = DetectionResult()
    if (root / ".git").is_dir():
        result.detected.append("git")
    if (root / "go.mod").is_file():
        result.detected.append("go")
    if (
        (root / "pyproject.toml").is_file()
        or (root / "setup.py").is_file()
        or (root / "requirements.txt").is_file()
    ):
        result.detected.append("python")
    if (root / "package.json").is_file():
        result.detected.append("node")
    return result


def apply_detection(args: ParsedArgs, detection: DetectionResult) -> None:
    if "git" in detection.detected:
        args.with_git = True
    if "go" in detection.detected:
        args.with_go = True
    if "python" in detection.detected:
        args.with_python = True
    if "node" in detection.detected:
        args.with_node = True


def _dedup_sorted(items: list[str]) -> list[str]:
    return sorted(set(items))


@dataclass
class PermissionsBlock:
    default_mode: str
    allow: list[str]
    deny: list[str]

    def to_json(self) -> dict[str, object]:
        return {
            "defaultMode": self.default_mode,
            "allow": list(self.allow),
            "deny": list(self.deny),
        }


@dataclass
class MergedSettings:
    permissions: PermissionsBlock
    extra: dict[str, object] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = dict(self.extra)
        out["permissions"] = self.permissions.to_json()
        return out


def _existing_permissions(existing: Mapping[str, object]) -> Mapping[str, object]:
    perms = existing.get("permissions")
    if isinstance(perms, Mapping):
        return perms
    return {}


def _extract_string_list(perms: Mapping[str, object], key: str) -> list[str]:
    raw = perms.get(key)
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, str)]


def _default_mode_from(perms: Mapping[str, object]) -> str:
    value = perms.get("defaultMode")
    if isinstance(value, str):
        return value
    return "acceptEdits"


def merge_permissions(
    existing: Mapping[str, object],
    base_allow: list[str],
    base_deny: list[str],
    add_allow: list[str],
    add_deny: list[str],
) -> MergedSettings:
    extra = {k: v for k, v in existing.items() if k != "permissions"}
    perms = _existing_permissions(existing)
    existing_allow = _extract_string_list(perms, "allow")
    existing_deny = _extract_string_list(perms, "deny")
    block = PermissionsBlock(
        default_mode=_default_mode_from(perms),
        allow=_dedup_sorted(existing_allow + base_allow + add_allow),
        deny=_dedup_sorted(existing_deny + base_deny + add_deny),
    )
    return MergedSettings(permissions=block, extra=extra)


def _flag_specific(args: ParsedArgs) -> tuple[list[str], list[str]]:
    add_allow: list[str] = []
    add_deny: list[str] = []
    if args.with_git:
        add_allow.extend(GIT_WRITE_ALLOW)
        add_deny.extend(GIT_WRITE_DENY)
    return add_allow, add_deny


def _load_existing(target: Path) -> dict[str, object]:
    if not target.is_file():
        return {}
    return io_json.load_json(target)


def _has_git_commit_allow(allow: list[str]) -> bool:
    return any("git commit" in item for item in allow)


@dataclass
class RunReport:
    detected: list[str]
    default_mode: str
    after_allow: int
    after_deny: int
    new_allow: int
    new_deny: int
    with_git: bool
    with_go: bool
    with_python: bool
    with_node: bool
    git_commit_missing: bool


def run(argv: list[str], cwd: Path) -> tuple[int, RunReport | str]:
    parsed = parse_args(argv)
    if isinstance(parsed, ParseFailure):
        return 1, parsed.message
    if parsed.show_usage:
        return 0, USAGE

    detection = DetectionResult()
    if not parsed.no_detect:
        detection = detect_project(cwd)
        apply_detection(parsed, detection)

    target = cwd / SETTINGS_RELATIVE
    existing = _load_existing(target)

    before_perms = _existing_permissions(existing)
    before_allow = len(_extract_string_list(before_perms, "allow"))
    before_deny = len(_extract_string_list(before_perms, "deny"))

    add_allow, add_deny = _flag_specific(parsed)

    merged = merge_permissions(existing, BASE_ALLOW, BASE_DENY, add_allow, add_deny)
    target.parent.mkdir(parents=True, exist_ok=True)
    io_json.dump_json(target, merged.to_json())

    after_allow = len(merged.permissions.allow)
    after_deny = len(merged.permissions.deny)

    report = RunReport(
        detected=detection.detected,
        default_mode=merged.permissions.default_mode,
        after_allow=after_allow,
        after_deny=after_deny,
        new_allow=after_allow - before_allow,
        new_deny=after_deny - before_deny,
        with_git=parsed.with_git,
        with_go=parsed.with_go,
        with_python=parsed.with_python,
        with_node=parsed.with_node,
        git_commit_missing=not _has_git_commit_allow(merged.permissions.allow),
    )
    return 0, report


def format_report(report: RunReport) -> str:
    lines: list[str] = [f"Permissions updated in {SETTINGS_RELATIVE}"]
    if report.detected:
        lines.append(f"  detected:    {', '.join(report.detected)}")
    lines.append(f"  defaultMode: {report.default_mode}")
    lines.append(f"  allow rules: {report.after_allow} (+{report.new_allow} new)")
    lines.append(f"  deny rules:  {report.after_deny} (+{report.new_deny} new)")
    if report.with_git:
        lines.append("  git write:   ENABLED")
    if report.with_go:
        lines.append("  go:          OK (base patterns)")
    if report.with_python:
        lines.append("  python:      OK (base patterns)")
    if report.with_node:
        lines.append("  node:        OK (base patterns)")
    if not report.with_git and report.git_commit_missing:
        lines.append("  git write:   disabled (use --with-git to enable)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    env.setup()
    args = argv if argv is not None else sys.argv[1:]
    cwd = Path.cwd()
    exit_code, payload = run(args, cwd)

    if isinstance(payload, str):
        if exit_code == 0:
            sys.stdout.write(payload)
        else:
            sys.stderr.write(payload + "\n")
            sys.stderr.write(USAGE)
        return exit_code

    sys.stdout.write(format_report(payload))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
