"""Offline contract tests for the Claude Langfuse source pin."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/langfuse-hook-source.py"


def load_module():
    spec = importlib.util.spec_from_file_location("langfuse_hook_source", SOURCE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployed_artifact_matches_pin() -> None:
    module = load_module()
    info = module.manifest()
    assert module.git_blob_sha1(module.OUTPUT.read_bytes()) == info["output_git_blob_sha1"]
    assert info["patches"] == [
        "0001-durable-checkpoint.patch",
        "0002-flush-before-checkpoint.patch",
        "0003-visible-delivery-errors.patch",
        "0004-propagate-emission-failures.patch",
        "0005-replay-snapshot-identity.patch",
        "0006-durable-otlp-exporter.patch",
        "0007-discard-uncommitted-spans.patch",
        "0008-deterministic-observation-ids.patch",
        "0009-untruncated-by-default.patch",
        "0010-pep723-langfuse-5.patch",
    ]


def test_upstream_mismatch_is_rejected() -> None:
    module = load_module()
    info = module.manifest()
    with pytest.raises(ValueError, match="Upstream content"):
        module.build(b"tampered", info)


def test_unsafe_patch_name_is_rejected() -> None:
    module = load_module()
    info = dict(module.manifest())
    info["patches"] = ["../outside.patch"]
    source = b"synthetic upstream fixture"
    info["upstream_git_blob_sha1"] = module.git_blob_sha1(source)
    with pytest.raises(ValueError, match="Patch must be a basename"):
        module.build(source, info)


UPSTREAM_FIXTURE = b"first line\nsecond line\n"
PATCHED_FIXTURE = b"first line\npatched line\n"
FIXTURE_PATCH = """diff --git a/langfuse_hook.py b/langfuse_hook.py
--- a/langfuse_hook.py
+++ b/langfuse_hook.py
@@ -1,2 +1,2 @@
 first line
-second line
+patched line
"""


def run_print_hashes(
    module, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> str:
    patches = tmp_path / "patches"
    patches.mkdir()
    (patches / "0001-fixture.patch").write_text(FIXTURE_PATCH, encoding="utf-8")
    manifest = tmp_path / "lock.json"
    pinned = dict(module.manifest())
    pinned |= {
        "patches": ["0001-fixture.patch"],
        "upstream_git_blob_sha1": "0" * 40,
        "output_git_blob_sha1": "0" * 40,
    }
    manifest.write_text(json.dumps(pinned), encoding="utf-8")
    output = tmp_path / "langfuse_hook.py"
    output.write_bytes(b"committed artifact")
    monkeypatch.setattr(module, "MANIFEST", manifest)
    monkeypatch.setattr(module, "PATCH_DIR", patches)
    monkeypatch.setattr(module, "OUTPUT", output)
    monkeypatch.setattr(module, "fetch_upstream", lambda _info: UPSTREAM_FIXTURE)
    monkeypatch.setattr(sys, "argv", ["langfuse-hook-source.py", "refresh", "--print-hashes"])
    assert module.main() == 0
    assert output.read_bytes() == b"committed artifact"
    return capsys.readouterr().out


def test_print_hashes_reports_the_hashes_a_lock_update_needs_without_enforcing_the_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = load_module()
    printed = run_print_hashes(module, tmp_path, monkeypatch, capsys)
    upstream = module.git_blob_sha1(UPSTREAM_FIXTURE)
    output = module.git_blob_sha1(PATCHED_FIXTURE)
    assert printed.splitlines() == [
        f'"upstream_git_blob_sha1": "{upstream}"',
        f'"output_git_blob_sha1": "{output}"',
    ]


def test_print_hashes_is_refused_for_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(sys, "argv", ["langfuse-hook-source.py", "verify", "--print-hashes"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
