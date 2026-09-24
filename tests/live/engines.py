from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Final, NoReturn

import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping

_VERSION_TIMEOUT_SECONDS: Final = 60.0

# A caller that has installed an engine on purpose — CI does — lists it here, and
# every route by which this suite would otherwise quietly decline to exercise it
# becomes a failure instead. Without it a runner whose install step silently
# produced nothing reports the same green as one that exercised everything.
REQUIRED_ENGINES_VARIABLE: Final = "DEVBOX_LIVE_REQUIRE_ENGINES"


def required_engines(environment: Mapping[str, str] | None = None) -> frozenset[str]:
    declared = (os.environ if environment is None else environment).get(
        REQUIRED_ENGINES_VARIABLE, ""
    )
    return frozenset(name.strip() for name in declared.split(",") if name.strip())


def unusable(engine: str, reason: str) -> NoReturn:
    if engine in required_engines():
        pytest.fail(f"{REQUIRED_ENGINES_VARIABLE} lists {engine}, but {reason}")
    pytest.skip(f"{engine}: {reason}")


def require_binary(name: str) -> str:
    located = shutil.which(name)
    if located is None:
        unusable(name, "the CLI is not on PATH; cannot exercise it against a generated home")
    return located


def binary_version(binary: str) -> str:
    try:
        completed = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError as error:
        pytest.skip(f"cannot run `{binary} --version`: {error}")
    return completed.stdout.strip() or completed.stderr.strip()
