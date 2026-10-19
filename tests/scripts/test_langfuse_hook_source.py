"""Offline contract tests for the Claude Langfuse source pin."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/langfuse-hook-source.py"


def load_module():
    spec = importlib.util.spec_from_file_location("langfuse_hook_source", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployed_artifact_matches_pin() -> None:
    module = load_module()
    info = module.manifest()
    assert module.git_blob_sha1(module.OUTPUT.read_bytes()) == info["output_git_blob_sha1"]
    assert module.build(module.OUTPUT.read_bytes(), info) == module.OUTPUT.read_bytes()


def test_upstream_mismatch_is_rejected() -> None:
    module = load_module()
    info = module.manifest()
    with pytest.raises(ValueError, match="Upstream content"):
        module.build(b"tampered", info)


def test_unsafe_patch_name_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    info = dict(module.manifest())
    info["patches"] = ["../outside.patch"]
    with pytest.raises(ValueError, match="Patch must be a basename"):
        module.build(module.OUTPUT.read_bytes(), info)
