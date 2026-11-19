#!/usr/bin/env python3
"""Explicit upstream rebuild and offline verification for the deployed Codex Langfuse hook.

The built bundle is committed. Hook execution and provisioning never fetch code
or install packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
VENDOR: Final = ROOT / "roles/devbox/files/dot_codex/bin/vendor"
MANIFEST = VENDOR / "langfuse-codex-upstream.lock.json"
OUTPUT = VENDOR / "langfuse-codex/index.mjs"
LICENSE = VENDOR / "langfuse-codex/LICENSE"
PATCH_DIR = VENDOR / "patches"

FETCH_TIMEOUT_SECONDS: Final = 60
STEP_TIMEOUT_SECONDS: Final = 900
_HEX: Final = frozenset("0123456789abcdef")
_EXECUTABLE_BITS: Final = 0o111


def git_blob_sha1(data: bytes) -> str:
    blob = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(blob, usedforsecurity=False).hexdigest()


def git_tree_sha1(directory: Path) -> str:
    """The SHA-1 `git write-tree` gives this directory, equal to `<commit>^{tree}` upstream."""
    entries: list[tuple[bytes, bytes, bytes]] = []
    for child in directory.iterdir():
        name = child.name.encode()
        if child.is_symlink():
            target = os.fsencode(child.readlink())
            entries.append((name, b"120000", bytes.fromhex(git_blob_sha1(target))))
        elif child.is_dir():
            if not any(child.iterdir()):
                continue
            entries.append((name + b"/", b"40000", bytes.fromhex(git_tree_sha1(child))))
        else:
            mode = b"100755" if child.stat().st_mode & _EXECUTABLE_BITS else b"100644"
            entries.append((name, mode, bytes.fromhex(git_blob_sha1(child.read_bytes()))))
    body = b"".join(
        mode + b" " + key.removesuffix(b"/") + b"\0" + digest
        for key, mode, digest in sorted(entries)
    )
    tree = b"tree " + str(len(body)).encode() + b"\0" + body
    return hashlib.sha1(tree, usedforsecurity=False).hexdigest()


def manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        message = "Unsupported manifest schema"
        raise ValueError(message)
    if len(data["commit"]) != 40 or not set(data["commit"]) <= _HEX:
        message = "Upstream must be pinned to a full commit SHA"
        raise ValueError(message)
    if not isinstance(data["node_major"], int) or not isinstance(data["pnpm_version"], str):
        message = "The lock must pin node_major (integer) and pnpm_version (string)"
        raise TypeError(message)
    artifact = PurePosixPath(data["artifact_path"])
    if artifact.is_absolute() or ".." in artifact.parts:
        message = "artifact_path must be relative to the upstream tree"
        raise ValueError(message)
    return data


def fetch_upstream(info: dict, destination: Path) -> None:
    url = f"https://codeload.github.com/{info['source']}/tar.gz/{info['commit']}"
    with tempfile.TemporaryDirectory(prefix="langfuse-codex-fetch-") as scratch:
        archive = Path(scratch) / "upstream.tar.gz"
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:
            archive.write_bytes(response.read())
        unpacked = Path(scratch) / "unpacked"
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(unpacked, filter="data")
        (top,) = unpacked.iterdir()
        shutil.move(top, destination)


def check_toolchain(info: dict) -> None:
    node = _tool_version("node").removeprefix("v")
    if node.split(".")[0] != str(info["node_major"]):
        message = f"node {node} is on PATH; the lock pins Node {info['node_major']}"
        raise ValueError(message)
    pnpm = _tool_version("pnpm")
    if pnpm != info["pnpm_version"]:
        message = f"pnpm {pnpm} is on PATH; the lock pins pnpm {info['pnpm_version']}"
        raise ValueError(message)


def _tool_version(tool: str) -> str:
    completed = subprocess.run(
        [tool, "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=STEP_TIMEOUT_SECONDS,
    )
    return completed.stdout.strip()


def apply_patches(work: Path, patches: list) -> None:
    for patch in patches:
        if not isinstance(patch, str) or not patch.endswith(".patch") or Path(patch).name != patch:
            message = "Patch must be a basename ending in .patch"
            raise ValueError(message)
        patch_path = PATCH_DIR / patch
        if not patch_path.is_file():
            raise FileNotFoundError(patch_path)
        subprocess.run(
            ["git", "apply", "--check", "--whitespace=error", str(patch_path)],
            cwd=work,
            check=True,
            timeout=STEP_TIMEOUT_SECONDS,
        )
        subprocess.run(
            ["git", "apply", str(patch_path)], cwd=work, check=True, timeout=STEP_TIMEOUT_SECONDS
        )


def build(work: Path, info: dict) -> bytes:
    for step in (
        ["pnpm", "install", "--frozen-lockfile"],
        ["pnpm", "run", "build"],
        ["pnpm", "exec", "vitest", "run"],
    ):
        subprocess.run(step, cwd=work, check=True, timeout=STEP_TIMEOUT_SECONDS)
    return (work / info["artifact_path"]).read_bytes()


def produce(info: dict, *, enforce_tree: bool) -> tuple[str, bytes, bytes]:
    check_toolchain(info)
    with tempfile.TemporaryDirectory(prefix="langfuse-codex-") as directory:
        work = Path(directory) / "upstream"
        fetch_upstream(info, work)
        tree = git_tree_sha1(work)
        if enforce_tree and tree != info["upstream_tree_sha1"]:
            message = f"Upstream tree {tree} does not match the pinned {info['upstream_tree_sha1']}"
            raise ValueError(message)
        licence = (work / "LICENSE").read_bytes()
        apply_patches(work, info["patches"])
        return tree, build(work, info), licence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "refresh"])
    parser.add_argument(
        "--print-hashes",
        action="store_true",
        help=(
            "refresh only: build from the locked commit and patch list, print the upstream "
            "tree and output blob hashes for the lock, enforce neither, write nothing"
        ),
    )
    args = parser.parse_args()
    if args.print_hashes and args.command != "refresh":
        parser.error("--print-hashes applies to refresh only")
    info = manifest()
    if args.command == "verify":
        if git_blob_sha1(OUTPUT.read_bytes()) != info["output_git_blob_sha1"]:
            message = "Vendored bundle differs from the locked build output"
            raise ValueError(message)
        print("Codex Langfuse vendored bundle matches lock (offline)")
        return 0
    tree, output, licence = produce(info, enforce_tree=not args.print_hashes)
    if args.print_hashes:
        print(f'"upstream_tree_sha1": "{tree}"')
        print(f'"output_git_blob_sha1": "{git_blob_sha1(output)}"')
        return 0
    if git_blob_sha1(output) != info["output_git_blob_sha1"]:
        message = "Built bundle differs from the locked hash; review and update the pin explicitly"
        raise ValueError(message)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(output)
    LICENSE.write_bytes(licence)
    print("Codex Langfuse vendored bundle rebuilt from pinned source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
