#!/usr/bin/env python3
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# Claude's env may carry the operator's real Langfuse credentials for the langfuse skill.
# The vendored hook reads these names before CC_LANGFUSE_*, and the SDK prefers
# LANGFUSE_BASE_URL over the host it is given, so traces would leave the loopback edge.
SHADOWING_VARIABLES: Final[tuple[str, ...]] = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
)
VENDORED_HOOK: Final[Path] = Path(__file__).resolve().parent / "vendor" / "langfuse_hook.py"


def scrub_shadowing_credentials(environment: MutableMapping[str, str]) -> None:
    for name in SHADOWING_VARIABLES:
        environment.pop(name, None)


def main() -> None:
    scrub_shadowing_credentials(os.environ)
    # The import root the vendored file gets when it is run directly.
    sys.path[0] = str(VENDORED_HOOK.parent)
    runpy.run_path(str(VENDORED_HOOK), run_name="__main__")


if __name__ == "__main__":
    main()
