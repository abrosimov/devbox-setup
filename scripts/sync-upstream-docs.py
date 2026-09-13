from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, cast
from urllib.parse import quote

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = PurePosixPath("roles/devbox/files/dot_ai/skills/fpf-thinking/references")
PROVENANCE = str(REFERENCES / "upstream-snapshot.json")


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class Document:
    source: str
    destination: str


@dataclass(frozen=True)
class Manifest:
    repository: str
    ref: str
    files: tuple[Document, ...]


@dataclass(frozen=True)
class Original:
    content: bytes | None
    mode: int


def relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        msg = "manifest paths must be non-empty POSIX paths"
        raise SyncError(msg)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        msg = "manifest paths must be normalised and repository-relative"
        raise SyncError(msg)
    return value


def parse_manifest(source: bytes) -> Manifest:
    try:
        value = json.loads(source)
    except (ValueError, UnicodeError) as error:
        msg = "manifest must contain UTF-8 JSON"
        raise SyncError(msg) from error
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "repository",
        "ref",
        "files",
    }:
        msg = "manifest has unsupported fields"
        raise SyncError(msg)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        msg = "unsupported manifest schema"
        raise SyncError(msg)
    repository = value["repository"]
    ref = value["ref"]
    if not isinstance(repository, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        msg = "repository must be a GitHub owner/repository pair"
        raise SyncError(msg)
    if not isinstance(ref, str) or not ref.strip():
        msg = "ref must be a non-empty string"
        raise SyncError(msg)
    entries = value["files"]
    if not isinstance(entries, list) or not entries:
        msg = "manifest files must be a non-empty list"
        raise SyncError(msg)
    files = tuple(parse_document(entry) for entry in entries)
    if len({entry.destination for entry in files}) != len(files):
        msg = "duplicate manifest destinations"
        raise SyncError(msg)
    return Manifest(repository, ref, files)


def parse_document(entry: object) -> Document:
    if not isinstance(entry, dict) or set(entry) != {"source", "destination"}:
        msg = "manifest file has unsupported fields"
        raise SyncError(msg)
    source_path = relative_path(entry["source"])
    destination = relative_path(entry["destination"])
    if REFERENCES not in PurePosixPath(destination).parents or destination == PROVENANCE:
        msg = "destinations must be non-reserved paths inside the FPF reference directory"
        raise SyncError(msg)
    if any(
        not path.endswith(".md") and PurePosixPath(path).name != "LICENSE"
        for path in (source_path, destination)
    ):
        msg = "only Markdown documents and LICENSE files are supported"
        raise SyncError(msg)
    return Document(source_path, destination)


def download(url: str) -> bytes:
    try:
        result = subprocess.run(
            [
                "curl",
                "--disable",
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--connect-timeout",
                "10",
                "--max-time",
                "45",
                "--max-filesize",
                "67108864",
                url,
            ],
            capture_output=True,
            check=False,
            timeout=50,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        msg = "upstream download unavailable or timed out"
        raise SyncError(msg) from error
    if result.returncode:
        msg = f"upstream download failed (curl exit {result.returncode}): {url}"
        raise SyncError(msg)
    return result.stdout


def resolve_commit(manifest: Manifest, ref: str | None) -> str:
    selected = ref if ref is not None else manifest.ref
    if not selected.strip():
        msg = "ref must not be empty"
        raise SyncError(msg)
    url = f"https://api.github.com/repos/{manifest.repository}/commits/{quote(selected, safe='')}"
    try:
        response = json.loads(download(url))
    except (ValueError, UnicodeError) as error:
        msg = "GitHub commit response is invalid"
        raise SyncError(msg) from error
    commit = response.get("sha") if isinstance(response, dict) else None
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        msg = "GitHub did not return a full commit SHA"
        raise SyncError(msg)
    return commit


def validate_markdown(content: bytes) -> None:
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeError as error:
        msg = "upstream document is not UTF-8"
        raise SyncError(msg) from error
    if not text or "\x00" in text or re.match(r"(?is)^(?:<!doctype\s+html|<html\b)", text):
        msg = "upstream document is empty or an HTML error page"
        raise SyncError(msg)


def original(path: Path) -> Original:
    if path.is_symlink() or path.resolve() != path.absolute():
        msg = f"symlink paths are not supported: {path}"
        raise SyncError(msg)
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return Original(None, 0o644)
    if not stat.S_ISREG(metadata.st_mode):
        msg = f"expected a regular file: {path}"
        raise SyncError(msg)
    return Original(path.read_bytes(), stat.S_IMODE(metadata.st_mode))


def verify_original(path: Path, expected: Original) -> None:
    if original(path) != expected:
        msg = f"destination changed during replacement: {path}"
        raise SyncError(msg)


def replace_all(writes: dict[Path, bytes], expected: dict[Path, Original]) -> None:
    with contextlib.ExitStack() as stack:
        staged: dict[Path, tuple[Path, Path]] = {}
        for target, content in writes.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix=".upstream-docs-", dir=target.parent))
            stack.callback(shutil.rmtree, directory)
            candidate, backup = directory / "candidate", directory / "backup"
            candidate.write_bytes(content)
            candidate.chmod(expected[target].mode)
            if expected[target].content is not None:
                backup.write_bytes(cast("bytes", expected[target].content))
                backup.chmod(expected[target].mode)
            staged[target] = candidate, backup
        for path, before in expected.items():
            if original(path) != before:
                msg = f"input changed during synchronisation: {path}"
                raise SyncError(msg)
        replaced: list[Path] = []
        try:
            for target, (candidate, _backup) in staged.items():
                verify_original(target, expected[target])
                candidate.replace(target)
                replaced.append(target)
        except BaseException:
            try:
                for target in reversed(replaced):
                    verify_original(target, Original(writes[target], expected[target].mode))
                    if expected[target].content is None:
                        target.unlink()
                    else:
                        staged[target][1].replace(target)
            except (OSError, SyncError) as error:
                stack.pop_all()
                recovery = ", ".join(str(staged[target][1].parent) for target in replaced)
                msg = f"rollback incomplete ({error}); recovery files retained: {recovery}"
                raise SyncError(msg) from error
            raise


def sync(
    repo_root: Path, manifest_path: Path, *, ref: str | None, check: bool, reset_drift: bool
) -> bool:
    repo_root = repo_root.resolve()
    manifest_path = repo_root / manifest_path
    if not manifest_path.resolve().is_relative_to(repo_root):
        msg = "manifest must be inside the repository"
        raise SyncError(msg)
    descriptor = os.open(repo_root, os.O_RDONLY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            msg = "another upstream synchronisation is running"
            raise SyncError(msg) from error
        return sync_locked(repo_root, manifest_path, ref=ref, check=check, reset_drift=reset_drift)
    finally:
        os.close(descriptor)


def sync_locked(
    repo_root: Path, manifest_path: Path, *, ref: str | None, check: bool, reset_drift: bool
) -> bool:
    manifest_before = original(manifest_path)
    if manifest_before.content is None:
        msg = "manifest does not exist"
        raise SyncError(msg)
    manifest = parse_manifest(manifest_before.content)
    expected = {manifest_path: manifest_before}
    targets = [repo_root / entry.destination for entry in manifest.files]
    provenance = repo_root / PROVENANCE
    for target in [*targets, provenance]:
        expected[target] = original(target)
    caches = []
    if reset_drift and not check:
        cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "devbox-setup"
        caches = [cache / "fpf-drift", cache / "narrative-drift"]
        for target in caches:
            expected[target] = original(target)
    commit = resolve_commit(manifest, ref)
    writes: dict[Path, bytes] = {}
    records = []
    for entry in manifest.files:
        target = repo_root / entry.destination
        url = (
            f"https://raw.githubusercontent.com/{manifest.repository}/{commit}/"
            f"{quote(entry.source, safe='/')}"
        )
        content = download(url)
        validate_markdown(content)
        writes[target] = content
        records.append(
            {
                "source": entry.source,
                "destination": entry.destination,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    lock = {
        "schema_version": 1,
        "repository": manifest.repository,
        "commit": commit,
        "files": records,
    }
    writes[provenance] = (json.dumps(lock, indent=2, ensure_ascii=False) + "\n").encode()
    writes.update(dict.fromkeys(caches, b"0\n"))
    changed = {
        target: content for target, content in writes.items() if expected[target].content != content
    }
    for path, before in expected.items():
        if original(path) != before:
            msg = f"input changed during download: {path}"
            raise SyncError(msg)
    if changed and not check:
        replace_all(changed, expected)
    return bool(changed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronise pinned upstream Markdown documents")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=Path("config/upstream-docs.json"))
    parser.add_argument("--ref")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-reset-drift", action="store_true")
    args = parser.parse_args(argv)
    try:
        changed = sync(
            args.repo_root,
            args.manifest,
            ref=args.ref,
            check=args.check,
            reset_drift=not args.no_reset_drift,
        )
    except (SyncError, OSError) as error:
        print(f"upstream sync: {error}", file=sys.stderr)
        return 2
    print(
        "Upstream documents differ" if changed and args.check else "Upstream documents synchronised"
    )
    return int(changed and args.check)


if __name__ == "__main__":
    raise SystemExit(main())
