"""Shared Lua runner for the SketchyBar tests.

Every Lua interpreter found on PATH under the names the repository supports is a test
parameter, so the code is exercised on the 5.4 that Hammerspoon embeds and on whatever
newer `lua` the machine has. No interpreter at all is a failure, never a skip.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

JSON_OUT: Final = Path(__file__).resolve().parent / "lua" / "json_out.lua"
INTERPRETER_NAMES: Final = ("lua5.4", "lua")

type RunLua = Callable[..., object]


def _interpreters() -> list[str]:
    found: dict[str, str] = {}
    for name in INTERPRETER_NAMES:
        path = shutil.which(name)
        if path is not None:
            found.setdefault(os.path.realpath(path), path)
    return list(found.values())


_INTERPRETERS: Final = _interpreters()


def lua_string(value: str) -> str:
    out = ['"']
    for char in value:
        if char in {'"', "\\"}:
            out.append(f"\\{char}")
        elif ord(char) < 32 or ord(char) == 127:
            out.append(f"\\{ord(char):03d}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _scalar_literal(value: object) -> str:
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return lua_string(value)
    message = f"no Lua literal for {type(value).__name__}"
    raise TypeError(message)


def lua_literal(value: object) -> str:
    if isinstance(value, dict):
        fields = ", ".join(
            f"[{lua_literal(k)}] = {lua_literal(v)}" for k, v in value.items() if v is not None
        )
        return "{" + fields + "}"
    if isinstance(value, list | tuple):
        return "{" + ", ".join(lua_literal(v) for v in value) + "}"
    return _scalar_literal(value)


@pytest.fixture(
    params=_INTERPRETERS or [None],
    ids=[Path(path).name for path in _INTERPRETERS] or ["no-lua"],
)
def lua(request: pytest.FixtureRequest) -> str:
    if request.param is None:
        pytest.fail(
            "no Lua interpreter on PATH: install `lua5.4` (Ubuntu) or `lua` (Homebrew); "
            "these tests do not skip without one"
        )
    return str(request.param)


@pytest.fixture
def run_lua(lua: str) -> RunLua:
    """Run a Lua script with DATA (the given Python value) and `encode` (JSON) in scope.

    The script prints one JSON document; the fixture returns it decoded.
    """

    def run(script: str, data: object = None) -> object:
        encoder = lua_string(str(JSON_OUT))
        prelude = f"local encode = dofile({encoder})\nlocal DATA = {lua_literal(data)}\n"
        done = subprocess.run(
            [lua, "-"],
            input=prelude + script,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=30,
        )
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    return run
