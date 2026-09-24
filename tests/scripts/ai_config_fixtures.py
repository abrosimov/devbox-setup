from __future__ import annotations

import shutil
from pathlib import Path

from ai_config.adapters import EngineKind, engine_adapter

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_DIRECTORY = Path("roles/devbox/defaults/main")
PROFILES_DIRECTORY = Path("profiles")


def copy_template_variables(repo_root: Path) -> None:
    """Give an isolated repository the role defaults and every profile overlay.

    Copied rather than synthesised so that a test rendering a real engine source
    fails when a variable the source needs disappears from the real defaults.
    """
    for directory in (DEFAULTS_DIRECTORY, PROFILES_DIRECTORY):
        destination = repo_root / directory
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted((REPO_ROOT / directory).glob("*.yml")):
            shutil.copy2(path, destination / path.name)


def copy_engine_documents(engine: EngineKind, repo_root: Path) -> None:
    adapter = engine_adapter(engine)
    for relative_path in (adapter.repository_relative_path, adapter.manifest_relative_path):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative_path, destination)
    copy_template_variables(repo_root)
