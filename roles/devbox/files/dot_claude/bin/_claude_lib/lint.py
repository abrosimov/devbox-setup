from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Each entry maps a file-extension or special filename to the linter argv
# template. Returning a fresh list per call protects callers that mutate the
# result before invoking subprocess.

_BY_SUFFIX: dict[str, list[str]] = {
    ".go": ["golangci-lint", "run"],
    ".py": ["ruff", "check"],
    ".ts": ["npx", "eslint"],
    ".tsx": ["npx", "eslint"],
    ".js": ["npx", "eslint"],
    ".jsx": ["npx", "eslint"],
}

_BY_FILENAME: dict[str, list[str]] = {
    "Dockerfile": ["hadolint"],
    "docker-compose.yml": ["dclint"],
    "docker-compose.yaml": ["dclint"],
    "compose.yml": ["dclint"],
    "compose.yaml": ["dclint"],
}


def linter_for_file(path: Path) -> list[str] | None:
    name = path.name
    if name in _BY_FILENAME:
        return list(_BY_FILENAME[name])
    if name.startswith("Dockerfile") and "." not in name[len("Dockerfile") :]:
        return ["hadolint"]
    suffix = path.suffix.lower()
    cmd = _BY_SUFFIX.get(suffix)
    if cmd is None:
        return None
    return list(cmd)
