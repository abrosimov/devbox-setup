#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _claude_lib import env

Level = Literal["critical", "important", "optional"]


@dataclass(frozen=True)
class Tool:
    name: str
    level: Level
    install: str


@dataclass(frozen=True)
class CheckResult:
    tool: Tool
    location: str | None


TOOLS: Final[tuple[Tool, ...]] = (
    Tool("mise", "critical", "brew install mise"),
    Tool("node", "critical", "mise use --global node@lts"),
    Tool("git", "critical", "brew install git"),
    Tool("gh", "critical", "brew install gh"),
    Tool("goimports", "critical", "go install golang.org/x/tools/cmd/goimports@latest"),
    Tool("ruff", "critical", "uv tool install ruff"),
    Tool("jq", "critical", "brew install jq"),
    Tool("go", "important", "brew install go"),
    Tool("uv", "important", "brew install uv"),
    Tool("golangci-lint", "important", "brew install golangci-lint"),
    Tool("mypy", "important", "uv tool install mypy"),
    Tool("docker", "important", "brew install orbstack (or Docker Desktop)"),
    Tool("kubectl", "important", "brew install kubectl"),
    Tool("helm", "important", "brew install helm"),
    Tool("mockery", "important", "go install github.com/vektra/mockery/v2@latest"),
    Tool("sqlc", "important", "go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest"),
    Tool("hadolint", "important", "brew install hadolint"),
    Tool("dclint", "important", "npm install -g dclint"),
    Tool("rg", "optional", "brew install ripgrep"),
    Tool("fd", "optional", "brew install fd"),
    Tool("tree", "optional", "brew install tree"),
    Tool("bat", "optional", "brew install bat"),
    Tool("fzf", "optional", "brew install fzf"),
    Tool("ansible-lint", "optional", "uv tool install ansible-lint"),
    Tool("cargo", "optional", "brew install rustup && rustup-init"),
    Tool("task", "optional", "brew install go-task"),
)

LEVEL_ICONS: Final[dict[Level, str]] = {
    "critical": "\x1b[31m[CRITICAL]\x1b[0m",
    "important": "\x1b[33m[IMPORTANT]\x1b[0m",
    "optional": "\x1b[36m[OPTIONAL]\x1b[0m",
}


def locate(tool_name: str) -> str | None:
    return shutil.which(tool_name)


def check_tools(tools: tuple[Tool, ...]) -> tuple[list[CheckResult], list[CheckResult]]:
    found: list[CheckResult] = []
    missing: list[CheckResult] = []
    for tool in tools:
        loc = locate(tool.name)
        result = CheckResult(tool=tool, location=loc)
        if loc:
            found.append(result)
        else:
            missing.append(result)
    return found, missing


def render_report(
    found: list[CheckResult],
    missing: list[CheckResult],
    total: int,
) -> str:
    parts: list[str] = []
    parts.append("\n  Claude Code Toolchain Health Check")
    parts.append("  " + "=" * 38 + "\n")

    if found:
        parts.append(f"  \x1b[32m{len(found)} tools found\x1b[0m\n")

    if not missing:
        parts.append(f"  \x1b[32mAll {total} tools available. No issues.\x1b[0m\n")
        return "\n".join(parts)

    parts.append(f"  \x1b[31m{len(missing)} tools missing:\x1b[0m\n")
    for entry in missing:
        parts.append(f"  {LEVEL_ICONS[entry.tool.level]} {entry.tool.name}")
        parts.append(f"    Install: {entry.tool.install}\n")

    if any(entry.tool.level == "critical" for entry in missing):
        parts.append("  \x1b[31mCritical tools missing — hooks will fail silently.\x1b[0m\n")
    return "\n".join(parts)


def main() -> int:
    env.setup()
    found, missing = check_tools(TOOLS)
    print(render_report(found, missing, total=len(TOOLS)))
    if any(entry.tool.level == "critical" for entry in missing):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
