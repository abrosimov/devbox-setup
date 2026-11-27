from __future__ import annotations

import ctypes
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/session-separate-spaces.py"
SKYLIGHT = "/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight"
MAIN_CONNECTION = 4242


class FakeSymbol:
    def __init__(self, result: Callable[..., int]) -> None:
        self.result = result
        self.argtypes: list[object] | None = None
        self.restype: object | None = None
        self.arguments: list[tuple[object, ...]] = []

    def __call__(self, *arguments: object) -> int:
        self.arguments.append(arguments)
        return self.result(*arguments)


class FakeSkyLight:
    def __init__(self, mode: int, *, missing: tuple[str, ...] = ()) -> None:
        self.missing = missing
        self.SLSMainConnectionID = FakeSymbol(lambda: MAIN_CONNECTION)
        self.SLSGetSpaceManagementMode = FakeSymbol(lambda _connection: mode)

    def __getattribute__(self, name: str) -> object:
        if name in object.__getattribute__(self, "missing"):
            message = f"{name}: undefined symbol"
            raise AttributeError(message)
        return object.__getattribute__(self, name)


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location("session_separate_spaces", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def load_library(monkeypatch: pytest.MonkeyPatch, library: FakeSkyLight) -> list[str]:
    loaded: list[str] = []

    def cdll(name: str) -> FakeSkyLight:
        loaded.append(name)
        return library

    monkeypatch.setattr(ctypes, "CDLL", cdll)
    return loaded


class TestMain:
    def test_separate_spaces_mode_prints_true(
        self,
        script: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        load_library(monkeypatch, FakeSkyLight(1))

        status = script.main()

        captured = capsys.readouterr()
        assert status == 0
        assert captured.out == "true\n"
        assert captured.err == ""

    @pytest.mark.parametrize("mode", [0, 2, -1, 3, 256])
    def test_every_other_mode_prints_false(
        self,
        script: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        mode: int,
    ) -> None:
        load_library(monkeypatch, FakeSkyLight(mode))

        status = script.main()

        captured = capsys.readouterr()
        assert status == 0
        assert captured.out == "false\n"
        assert captured.err == ""

    def test_the_main_connection_is_the_one_the_mode_is_asked_for(
        self, script: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        library = FakeSkyLight(1)
        loaded = load_library(monkeypatch, library)

        script.main()

        assert loaded == [SKYLIGHT]
        assert library.SLSGetSpaceManagementMode.arguments == [(MAIN_CONNECTION,)]
        assert library.SLSMainConnectionID.arguments == [()]

    def test_the_calls_declare_the_c_int_signature_skylight_has(
        self, script: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        library = FakeSkyLight(1)
        load_library(monkeypatch, library)

        script.main()

        assert library.SLSMainConnectionID.argtypes == []
        assert library.SLSMainConnectionID.restype is ctypes.c_int
        assert library.SLSGetSpaceManagementMode.argtypes == [ctypes.c_int]
        assert library.SLSGetSpaceManagementMode.restype is ctypes.c_int

    def test_a_library_that_cannot_be_loaded_fails_with_nothing_on_stdout(
        self,
        script: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def cdll(name: str) -> object:
            message = f"{name}: cannot open shared object file"
            raise OSError(message)

        monkeypatch.setattr(ctypes, "CDLL", cdll)

        status = script.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "SkyLight" in captured.err
        assert captured.err.startswith("session-separate-spaces: ")

    @pytest.mark.parametrize("symbol", ["SLSMainConnectionID", "SLSGetSpaceManagementMode"])
    def test_a_missing_symbol_fails_with_nothing_on_stdout(
        self,
        script: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        symbol: str,
    ) -> None:
        load_library(monkeypatch, FakeSkyLight(1, missing=(symbol,)))

        status = script.main()

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "SkyLight" in captured.err
        assert symbol in captured.err


class TestRunAsAScript:
    def test_the_answer_is_one_word_or_a_failure_that_says_why(self) -> None:
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            assert result.stdout in {"true\n", "false\n"}
        else:
            assert result.returncode == 1
            assert result.stdout == ""
            assert "SkyLight" in result.stderr
