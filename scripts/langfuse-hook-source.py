#!/usr/bin/env python3
"""Explicit upstream refresh and offline verification for the deployed Claude Langfuse hook.

The vendored output is committed. Normal hook execution and provisioning never
fetch code or resolve third-party packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "roles/devbox/files/dot_claude/bin/vendor/langfuse-upstream.lock.json"
OUTPUT = ROOT / "roles/devbox/files/dot_claude/bin/vendor/langfuse_hook.py"
PATCH_DIR = ROOT / "roles/devbox/files/dot_claude/bin/vendor/patches"


def git_blob_sha1(data: bytes) -> str:
    blob = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(blob, usedforsecurity=False).hexdigest()


def manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        message = "Unsupported manifest schema"
        raise ValueError(message)
    if len(data["commit"]) != 40 or not all(c in "0123456789abcdef" for c in data["commit"]):
        message = "Upstream must be pinned to a full commit SHA"
        raise ValueError(message)
    return data


def fetch_upstream(info: dict) -> bytes:
    url = f"https://raw.githubusercontent.com/{info['source']}/{info['commit']}/{info['path']}"
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def fetch_pinned_source(info: dict) -> bytes:
    source = fetch_upstream(info)
    if git_blob_sha1(source) != info["upstream_git_blob_sha1"]:
        message = "Upstream blob hash mismatch"
        raise ValueError(message)
    return source


def build(source: bytes, info: dict) -> bytes:
    if git_blob_sha1(source) != info["upstream_git_blob_sha1"]:
        message = "Upstream content does not match pin"
        raise ValueError(message)
    return apply_patches(source, info["patches"])


def print_hashes(info: dict) -> None:
    # Neither hash is enforced: this is how the values for a lock update are obtained.
    source = fetch_upstream(info)
    output = apply_patches(source, info["patches"])
    print(f'"upstream_git_blob_sha1": "{git_blob_sha1(source)}"')
    print(f'"output_git_blob_sha1": "{git_blob_sha1(output)}"')


def apply_patches(source: bytes, patches: list) -> bytes:
    if not patches:
        return source
    with tempfile.TemporaryDirectory(prefix="langfuse-hook-") as directory:
        work = Path(directory)
        target = work / "langfuse_hook.py"
        target.write_bytes(source)
        for patch in patches:
            if (
                not isinstance(patch, str)
                or not patch.endswith(".patch")
                or Path(patch).name != patch
            ):
                message = "Patch must be a basename ending in .patch"
                raise ValueError(message)
            patch_path = PATCH_DIR / patch
            if not patch_path.is_file():
                raise FileNotFoundError(patch_path)
            subprocess.run(
                ["git", "apply", "--check", "--whitespace=error", str(patch_path)],
                cwd=work,
                check=True,
            )
            subprocess.run(["git", "apply", str(patch_path)], cwd=work, check=True)
        return target.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "refresh"])
    parser.add_argument(
        "--print-hashes",
        action="store_true",
        help=(
            "refresh only: build from the locked commit and patch list, print the upstream "
            "and output Git blob hashes for the lock, enforce neither, write nothing"
        ),
    )
    args = parser.parse_args()
    if args.print_hashes and args.command != "refresh":
        parser.error("--print-hashes applies to refresh only")
    info = manifest()
    if args.command == "verify":
        actual = OUTPUT.read_bytes()
        if git_blob_sha1(actual) != info["output_git_blob_sha1"]:
            message = "Vendored output differs from locked generated artifact"
            raise ValueError(message)
        print("Langfuse vendored artifact matches lock (offline)")
        return 0
    if args.print_hashes:
        print_hashes(info)
        return 0
    source = fetch_pinned_source(info)
    output = build(source, info)
    if git_blob_sha1(output) != info["output_git_blob_sha1"]:
        message = "Generated output differs from locked hash; review and update pin explicitly"
        raise ValueError(message)
    OUTPUT.write_bytes(output)
    print("Langfuse vendored artifact refreshed from pinned source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
