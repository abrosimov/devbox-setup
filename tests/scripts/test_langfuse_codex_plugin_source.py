"""Offline contract tests for the Codex Langfuse hook source pin."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/langfuse-codex-plugin-source.py"
ARTIFACT_PATH = "plugins/tracing/dist/index.mjs"
UPSTREAM_ARTIFACT = b"first line\nsecond line\n"
PATCHED_ARTIFACT = b"first line\npatched line\n"
UPSTREAM_LICENCE = b"MIT License\n"
FIXTURE_PATCH = f"""diff --git a/{ARTIFACT_PATH} b/{ARTIFACT_PATH}
--- a/{ARTIFACT_PATH}
+++ b/{ARTIFACT_PATH}
@@ -1,2 +1,2 @@
 first line
-second line
+patched line
"""


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("langfuse_codex_plugin_source", SOURCE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_upstream_fixture(_info: dict, destination: Path) -> None:
    (destination / ARTIFACT_PATH).parent.mkdir(parents=True)
    (destination / ARTIFACT_PATH).write_bytes(UPSTREAM_ARTIFACT)
    (destination / "LICENSE").write_bytes(UPSTREAM_LICENCE)


def built_artifact(work: Path, info: dict) -> bytes:
    return (work / info["artifact_path"]).read_bytes()


def git_write_tree(directory: Path) -> str:
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-c", "core.autocrlf=false", *arguments],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    git("init", "--quiet")
    git("add", "--all", "--force")
    return git("write-tree")


@pytest.fixture
def offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, Path, Path]:
    module = load_module()
    patches = tmp_path / "patches"
    patches.mkdir()
    (patches / "0001-fixture.patch").write_text(FIXTURE_PATCH, encoding="utf-8")
    output = tmp_path / "vendor/index.mjs"
    output.parent.mkdir()
    output.write_bytes(b"committed bundle")
    monkeypatch.setattr(module, "PATCH_DIR", patches)
    monkeypatch.setattr(module, "OUTPUT", output)
    monkeypatch.setattr(module, "LICENSE", tmp_path / "vendor/LICENSE")
    monkeypatch.setattr(module, "check_toolchain", lambda _info: None)
    monkeypatch.setattr(module, "fetch_upstream", write_upstream_fixture)
    monkeypatch.setattr(module, "build", built_artifact)
    return module, tmp_path, output


def pin(
    module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **fields: object
) -> None:
    manifest = tmp_path / "lock.json"
    pinned = dict(module.manifest()) | {"patches": ["0001-fixture.patch"]} | fields
    manifest.write_text(json.dumps(pinned), encoding="utf-8")
    monkeypatch.setattr(module, "MANIFEST", manifest)


def fixture_tree_sha1(module: ModuleType, tmp_path: Path) -> str:
    tree = tmp_path / "fixture-tree"
    tree.mkdir()
    write_upstream_fixture({}, tree)
    return module.git_tree_sha1(tree)


def run(module: ModuleType, monkeypatch: pytest.MonkeyPatch, *arguments: str) -> int:
    monkeypatch.setattr(sys, "argv", ["langfuse-codex-plugin-source.py", *arguments])
    return module.main()


def test_deployed_bundle_matches_pin() -> None:
    module = load_module()
    info = module.manifest()

    assert module.git_blob_sha1(module.OUTPUT.read_bytes()) == info["output_git_blob_sha1"]
    assert info["patches"] == [
        "0001-export-interrupted-and-ended-turns.patch",
        "0002-one-hook-run-per-rollout.patch",
        "0003-export-subagent-turns-after-the-spawning-turn.patch",
    ]
    assert info["artifact_path"] == ARTIFACT_PATH
    assert module.LICENSE.read_text(encoding="utf-8").startswith("MIT License")


def test_tree_hash_is_the_one_git_writes(tmp_path: Path) -> None:
    module = load_module()
    tree = tmp_path / "tree"
    (tree / "nested/deeper").mkdir(parents=True)
    (tree / "nested/deeper/leaf.ts").write_text("export {};\n", encoding="utf-8")
    (tree / "nested.json").write_text("{}\n", encoding="utf-8")
    (tree / "a-b").write_text("sorts between nested.json and nested/\n", encoding="utf-8")
    script = tree / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    (tree / "link").symlink_to("nested.json")
    (tree / "empty").mkdir()

    expected = git_write_tree(tree)
    (tree / ".git").rename(tmp_path / "git-metadata")

    assert module.git_tree_sha1(tree) == expected


def test_refresh_rejects_an_upstream_tree_that_does_not_match_the_pin(
    offline: tuple[ModuleType, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, tmp_path, output = offline
    pin(module, tmp_path, monkeypatch, upstream_tree_sha1="0" * 40)

    with pytest.raises(ValueError, match="does not match the pinned"):
        run(module, monkeypatch, "refresh")
    assert output.read_bytes() == b"committed bundle"


def test_refresh_rejects_a_build_that_differs_from_the_locked_output(
    offline: tuple[ModuleType, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, tmp_path, output = offline
    pin(
        module,
        tmp_path,
        monkeypatch,
        upstream_tree_sha1=fixture_tree_sha1(module, tmp_path),
        output_git_blob_sha1="0" * 40,
    )

    with pytest.raises(ValueError, match="differs from the locked hash"):
        run(module, monkeypatch, "refresh")
    assert output.read_bytes() == b"committed bundle"


def test_refresh_writes_the_patched_bundle_and_upstream_licence(
    offline: tuple[ModuleType, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, tmp_path, output = offline
    pin(
        module,
        tmp_path,
        monkeypatch,
        upstream_tree_sha1=fixture_tree_sha1(module, tmp_path),
        output_git_blob_sha1=module.git_blob_sha1(PATCHED_ARTIFACT),
    )

    assert run(module, monkeypatch, "refresh") == 0
    assert output.read_bytes() == PATCHED_ARTIFACT
    assert module.LICENSE.read_bytes() == UPSTREAM_LICENCE


def test_print_hashes_reports_the_hashes_a_lock_update_needs_without_enforcing_the_pin(
    offline: tuple[ModuleType, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module, tmp_path, output = offline
    pin(module, tmp_path, monkeypatch, upstream_tree_sha1="0" * 40, output_git_blob_sha1="0" * 40)
    tree = fixture_tree_sha1(module, tmp_path)

    assert run(module, monkeypatch, "refresh", "--print-hashes") == 0
    assert capsys.readouterr().out.splitlines() == [
        f'"upstream_tree_sha1": "{tree}"',
        f'"output_git_blob_sha1": "{module.git_blob_sha1(PATCHED_ARTIFACT)}"',
    ]
    assert output.read_bytes() == b"committed bundle"
    assert not module.LICENSE.exists()


def test_print_hashes_is_refused_for_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()

    with pytest.raises(SystemExit) as exc:
        run(module, monkeypatch, "verify", "--print-hashes")
    assert exc.value.code == 2


def test_verify_rejects_a_bundle_that_differs_from_the_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    edited = tmp_path / "index.mjs"
    edited.write_bytes(module.OUTPUT.read_bytes() + b"\n")
    monkeypatch.setattr(module, "OUTPUT", edited)

    with pytest.raises(ValueError, match="differs from the locked build output"):
        run(module, monkeypatch, "verify")


def test_unsafe_patch_name_is_rejected(tmp_path: Path) -> None:
    module = load_module()

    with pytest.raises(ValueError, match="Patch must be a basename"):
        module.apply_patches(tmp_path, ["../outside.patch"])


@pytest.mark.parametrize(
    ("node", "pnpm", "message"),
    [
        ("v26.13.1", "9.5.0", "the lock pins Node 22"),
        ("v22.22.0", "10.29.3", "the lock pins pnpm 9.5.0"),
    ],
)
def test_a_toolchain_other_than_the_pinned_one_is_refused(
    monkeypatch: pytest.MonkeyPatch, node: str, pnpm: str, message: str
) -> None:
    module = load_module()
    versions = {"node": node, "pnpm": pnpm}
    monkeypatch.setattr(module, "_tool_version", versions.__getitem__)

    with pytest.raises(ValueError, match=message):
        module.check_toolchain(module.manifest())


def test_the_pinned_toolchain_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    versions = {"node": "v22.22.0", "pnpm": "9.5.0"}
    monkeypatch.setattr(module, "_tool_version", versions.__getitem__)

    module.check_toolchain(module.manifest())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("commit", "e1d02be", "full commit SHA"),
        ("artifact_path", "../outside.mjs", "relative to the upstream tree"),
        ("artifact_path", "/etc/passwd", "relative to the upstream tree"),
    ],
)
def test_manifest_rejects_an_unsafe_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str, message: str
) -> None:
    module = load_module()
    pin(module, tmp_path, monkeypatch, **{field: value})

    with pytest.raises(ValueError, match=message):
        module.manifest()


@pytest.mark.parametrize(("field", "value"), [("node_major", "22"), ("pnpm_version", 9)])
def test_manifest_rejects_a_toolchain_pin_of_the_wrong_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    module = load_module()
    pin(module, tmp_path, monkeypatch, **{field: value})

    with pytest.raises(TypeError, match="must pin node_major"):
        module.manifest()
