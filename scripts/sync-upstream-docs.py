from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final
from urllib.parse import quote

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

ROOT: Final = Path(__file__).resolve().parents[1]
SNAPSHOT_NAME: Final = "upstream-snapshot.json"
MANIFEST_SCHEMA: Final = 2
SNAPSHOT_SCHEMA: Final = 1
MAX_DOCUMENT_BYTES: Final = 64 * 1024 * 1024
MAX_ARCHIVE_BYTES: Final = 256 * 1024 * 1024
MAX_UNPACKED_BYTES: Final = 1024 * 1024 * 1024
MAX_API_BYTES: Final = 1024 * 1024
API_SECONDS: Final = 45
ARCHIVE_SECONDS: Final = 300
ATTEMPTS: Final = 3
RETRY_DELAY_SECONDS: Final = 2.0
HTTP_OK: Final = 200
HTTP_ERROR_FLOOR: Final = 400
TRANSIENT_CURL_EXITS: Final = frozenset({5, 6, 7, 16, 18, 28, 35, 52, 55, 56, 92})
TRANSIENT_HTTP_STATUSES: Final = frozenset({408, 429, 500, 502, 503, 504})


class SyncError(RuntimeError):
    pass


class TransientDownloadError(SyncError):
    pass


@dataclass(frozen=True)
class Manifest:
    repository: str
    ref: str
    destination: PurePosixPath


@dataclass(frozen=True)
class Snapshot:
    commit: str | None
    owned: frozenset[str]


@dataclass(frozen=True)
class Original:
    content: bytes | None
    mode: int


@dataclass(frozen=True)
class Report:
    repository: str
    previous_commit: str | None
    commit: str
    added: tuple[str, ...]
    removed: tuple[str, ...]
    modified: tuple[str, ...]
    renamed: tuple[tuple[str, str], ...]
    changed: bool

    def lines(self) -> list[str]:
        lines = [f"{self.repository}: {self.previous_commit or '(no snapshot)'} -> {self.commit}"]
        lines += [f"  renamed  {old} -> {new}" for old, new in self.renamed]
        lines += [f"  added    {path}" for path in self.added]
        lines += [f"  removed  {path}" for path in self.removed]
        lines += [f"  modified {path}" for path in self.modified]
        if not (self.renamed or self.added or self.removed or self.modified):
            lines.append("  no document changes")
        return lines


def relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        msg = f"{label} must be a non-empty POSIX path"
        raise SyncError(msg)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or value == ".":
        msg = f"{label} must be normalised and relative: {value!r}"
        raise SyncError(msg)
    return value


def is_document_name(name: str) -> bool:
    return name.endswith(".md") or name == "LICENSE"


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
        "destination",
    }:
        msg = "manifest has unsupported fields"
        raise SyncError(msg)
    if type(value["schema_version"]) is not int or value["schema_version"] != MANIFEST_SCHEMA:
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
    destination = PurePosixPath(relative_path(value["destination"], "destination"))
    return Manifest(repository, ref, destination)


def parse_snapshot(content: bytes | None) -> Snapshot:
    if content is None:
        return Snapshot(None, frozenset())
    try:
        value = json.loads(content)
    except (ValueError, UnicodeError) as error:
        msg = "previous snapshot is not valid JSON; refusing to guess which files it owns"
        raise SyncError(msg) from error
    if not isinstance(value, dict) or value.get("schema_version") != SNAPSHOT_SCHEMA:
        msg = "previous snapshot has an unsupported schema"
        raise SyncError(msg)
    commit = value.get("commit")
    files = value.get("files")
    if not isinstance(commit, str) or not isinstance(files, list):
        msg = "previous snapshot lacks a commit or a file list"
        raise SyncError(msg)
    owned: set[str] = set()
    for record in files:
        source = record.get("source") if isinstance(record, dict) else None
        path = relative_path(source, "snapshot source")
        if not is_document_name(PurePosixPath(path).name):
            msg = f"previous snapshot owns a non-document file: {path!r}"
            raise SyncError(msg)
        owned.add(path)
    return Snapshot(commit, frozenset(owned))


def curl_command(url: str, output: Path, *, max_bytes: int, max_seconds: int) -> list[str]:
    return [
        "curl",
        "--disable",
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
        str(max_seconds),
        "--max-filesize",
        str(max_bytes),
        "--output",
        str(output),
        "--write-out",
        "%{http_code}",
        url,
    ]


def download_once(url: str, *, max_bytes: int, max_seconds: int) -> bytes:
    with tempfile.TemporaryDirectory(prefix="upstream-docs-") as directory:
        body = Path(directory) / "body"
        try:
            result = subprocess.run(
                curl_command(url, body, max_bytes=max_bytes, max_seconds=max_seconds),
                capture_output=True,
                check=False,
                timeout=max_seconds + 15,
            )
        except subprocess.TimeoutExpired as error:
            msg = f"upstream download timed out: {url}"
            raise TransientDownloadError(msg) from error
        except OSError as error:
            msg = f"curl is unavailable: {error}"
            raise SyncError(msg) from error
        status_text = result.stdout.decode("ascii", "replace").strip()
        status = int(status_text) if status_text.isdigit() else 0
        # Checked before the exit code: curl over HTTP/2 can report a 404 as exit 56.
        if status >= HTTP_ERROR_FLOOR:
            msg = f"upstream returned HTTP {status} for {url}"
            raise (TransientDownloadError if status in TRANSIENT_HTTP_STATUSES else SyncError)(msg)
        if result.returncode:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            reason = detail[-1] if detail else "no diagnostic"
            msg = f"upstream download failed (curl exit {result.returncode}: {reason}): {url}"
            transient = result.returncode in TRANSIENT_CURL_EXITS
            raise (TransientDownloadError if transient else SyncError)(msg)
        if status != HTTP_OK:
            msg = f"upstream returned unexpected HTTP status {status_text or 'none'} for {url}"
            raise SyncError(msg)
        if body.stat().st_size > max_bytes:
            msg = f"upstream response exceeds {max_bytes} bytes: {url}"
            raise SyncError(msg)
        return body.read_bytes()


def download(url: str, *, max_bytes: int, max_seconds: int) -> bytes:
    for attempt in range(1, ATTEMPTS):
        try:
            return download_once(url, max_bytes=max_bytes, max_seconds=max_seconds)
        except TransientDownloadError as error:
            print(f"upstream sync: {error}; retrying", file=sys.stderr)
            time.sleep(RETRY_DELAY_SECONDS * attempt)
    try:
        return download_once(url, max_bytes=max_bytes, max_seconds=max_seconds)
    except TransientDownloadError as error:
        msg = f"{error} (gave up after {ATTEMPTS} attempts)"
        raise SyncError(msg) from error


def resolve_commit(manifest: Manifest, ref: str | None) -> str:
    selected = ref if ref is not None else manifest.ref
    if not selected.strip():
        msg = "ref must not be empty"
        raise SyncError(msg)
    url = f"https://api.github.com/repos/{manifest.repository}/commits/{quote(selected, safe='')}"
    try:
        response = json.loads(download(url, max_bytes=MAX_API_BYTES, max_seconds=API_SECONDS))
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


def archive_path(member: tarfile.TarInfo) -> tuple[str, str]:
    name = member.name.rstrip("/") if member.isdir() else member.name
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or ".." in path.parts or str(path) != name:
        msg = f"upstream archive contains an unsafe path: {member.name!r}"
        raise SyncError(msg)
    top, *rest = path.parts
    return top, "/".join(rest)


def extract_documents(archive: bytes) -> dict[str, bytes]:
    documents: dict[str, bytes] = {}
    prefix: str | None = None
    unpacked = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for member in bundle:
                top, path = archive_path(member)
                if prefix not in (None, top):
                    msg = "upstream archive has more than one top-level directory"
                    raise SyncError(msg)
                prefix = top
                unpacked += max(member.size, 0)
                if unpacked > MAX_UNPACKED_BYTES:
                    msg = f"upstream archive unpacks to more than {MAX_UNPACKED_BYTES} bytes"
                    raise SyncError(msg)
                if not path or member.isdir() or not is_document_name(PurePosixPath(path).name):
                    continue
                if path in documents:
                    msg = f"upstream archive repeats a path: {path}"
                    raise SyncError(msg)
                documents[path] = read_document(bundle, member, path)
    except (tarfile.TarError, EOFError, zlib.error, OSError) as error:
        msg = f"upstream archive is not a readable gzip tarball: {error}"
        raise SyncError(msg) from error
    return documents


def read_document(bundle: tarfile.TarFile, member: tarfile.TarInfo, path: str) -> bytes:
    if not member.isreg():
        msg = f"upstream path is not a regular file: {path}"
        raise SyncError(msg)
    if member.size > MAX_DOCUMENT_BYTES:
        msg = f"upstream document exceeds {MAX_DOCUMENT_BYTES} bytes: {path}"
        raise SyncError(msg)
    stream = bundle.extractfile(member)
    if stream is None:
        msg = f"upstream document is unreadable: {path}"
        raise SyncError(msg)
    content = stream.read()
    try:
        validate_markdown(content)
    except SyncError as error:
        msg = f"{error}: {path}"
        raise SyncError(msg) from error
    return content


def fetch_documents(manifest: Manifest, commit: str) -> dict[str, bytes]:
    url = f"https://api.github.com/repos/{manifest.repository}/tarball/{commit}"
    archive = download(url, max_bytes=MAX_ARCHIVE_BYTES, max_seconds=ARCHIVE_SECONDS)
    documents = extract_documents(archive)
    if not documents:
        msg = f"upstream {commit} has no documents; refusing to empty the bundle"
        raise SyncError(msg)
    return documents


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


def verify_unchanged(expected: dict[Path, Original], stage: str) -> None:
    for path, before in expected.items():
        if original(path) != before:
            msg = f"input changed during {stage}: {path}"
            raise SyncError(msg)


def stage_change(directory: Path, content: bytes | None, before: Original) -> None:
    if content is None:
        return
    candidate = directory / "candidate"
    candidate.write_bytes(content)
    candidate.chmod(before.mode)
    if before.content is not None:
        (directory / "backup").write_bytes(before.content)
        (directory / "backup").chmod(before.mode)


def undo_change(target: Path, content: bytes | None, before: Original, directory: Path) -> None:
    backup = directory / "backup"
    if content is None:
        verify_original(target, Original(None, 0o644))
        backup.replace(target)
        return
    verify_original(target, Original(content, before.mode))
    if before.content is None:
        target.unlink()
    else:
        backup.replace(target)


def replace_all(changes: dict[Path, bytes | None], expected: dict[Path, Original]) -> None:
    with contextlib.ExitStack() as stack:
        staged: dict[Path, Path] = {}
        for target, content in changes.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix=".upstream-docs-", dir=target.parent))
            stack.callback(shutil.rmtree, directory)
            stage_change(directory, content, expected[target])
            staged[target] = directory
        verify_unchanged(expected, "synchronisation")
        applied: list[Path] = []
        try:
            for target, directory in staged.items():
                verify_original(target, expected[target])
                if changes[target] is None:
                    target.replace(directory / "backup")
                else:
                    (directory / "candidate").replace(target)
                applied.append(target)
        except BaseException:
            try:
                for target in reversed(applied):
                    undo_change(target, changes[target], expected[target], staged[target])
            except (OSError, SyncError) as error:
                stack.pop_all()
                recovery = ", ".join(str(staged[target]) for target in applied)
                msg = f"rollback incomplete ({error}); recovery files retained: {recovery}"
                raise SyncError(msg) from error
            raise


def prune_empty_directories(removed: Iterable[Path], root: Path) -> None:
    for target in removed:
        directory = target.parent
        while (
            directory != root
            and root in directory.parents
            and directory.is_dir()
            and not any(directory.iterdir())
        ):
            directory.rmdir()
            directory = directory.parent


def detect_renames(
    added: Sequence[str], removed: Sequence[str], hashes: dict[str, str]
) -> list[tuple[str, str]]:
    candidates: dict[str, list[str]] = {}
    for path in removed:
        candidates.setdefault(hashes[path], []).append(path)
    renames = []
    for path in added:
        sources = candidates.get(hashes[path])
        if sources:
            renames.append((sources.pop(0), path))
    return renames


def refuse_case_collisions(paths: Iterable[str]) -> None:
    seen: dict[str, str] = {}
    for path in paths:
        other = seen.setdefault(path.casefold(), path)
        if other != path:
            msg = (
                f"upstream paths {other!r} and {path!r} differ only by case; "
                "case-insensitive filesystems cannot hold or rename them safely"
            )
            raise SyncError(msg)


def owned_contents(
    root: Path, previous: Snapshot, expected: dict[Path, Original]
) -> dict[str, bytes]:
    current: dict[str, bytes] = {}
    for path in sorted(previous.owned):
        content = expected[root / path].content
        if content is not None:
            current[path] = content
    return current


def claim_new_targets(root: Path, paths: Iterable[str], expected: dict[Path, Original]) -> None:
    for path in sorted(paths):
        target = root / path
        expected[target] = original(target)
        if expected[target].content is not None:
            msg = f"refusing to overwrite a file the snapshot does not own: {target}"
            raise SyncError(msg)


def sync(
    repo_root: Path, manifest_path: Path, *, ref: str | None, check: bool, reset_drift: bool
) -> Report:
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
) -> Report:
    manifest_before = original(manifest_path)
    if manifest_before.content is None:
        msg = "manifest does not exist"
        raise SyncError(msg)
    manifest = parse_manifest(manifest_before.content)
    root = repo_root / manifest.destination
    provenance = root / SNAPSHOT_NAME
    expected = {manifest_path: manifest_before, provenance: original(provenance)}
    previous = parse_snapshot(expected[provenance].content)
    for path in sorted(previous.owned):
        expected[root / path] = original(root / path)
    caches = []
    if reset_drift and not check:
        cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "devbox-setup"
        caches = [cache / "fpf-drift", cache / "narrative-drift"]
        for target in caches:
            expected[target] = original(target)
    commit = resolve_commit(manifest, ref)
    desired = fetch_documents(manifest, commit)
    verify_unchanged(expected, "download")
    current = owned_contents(root, previous, expected)
    obsolete = sorted(current.keys() - desired.keys())
    refuse_case_collisions([*sorted(desired), *obsolete])
    claim_new_targets(root, desired.keys() - previous.owned, expected)

    hashes = {path: hashlib.sha256(content).hexdigest() for path, content in desired.items()}
    hashes.update({path: hashlib.sha256(current[path]).hexdigest() for path in obsolete})
    added = sorted(desired.keys() - current.keys())
    modified = sorted(
        path for path in desired.keys() & current.keys() if current[path] != desired[path]
    )
    renamed = detect_renames(added, obsolete, hashes)
    renamed_paths = {path for pair in renamed for path in pair}

    changes: dict[Path, bytes | None] = dict.fromkeys((root / path for path in obsolete), None)
    changes.update({root / path: desired[path] for path in [*added, *modified]})
    record = {
        "schema_version": SNAPSHOT_SCHEMA,
        "repository": manifest.repository,
        "commit": commit,
        "files": [
            {
                "source": path,
                "destination": (manifest.destination / path).as_posix(),
                "sha256": hashes[path],
            }
            for path in sorted(desired)
        ],
    }
    snapshot = (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode()
    if snapshot != expected[provenance].content:
        changes[provenance] = snapshot
    report = Report(
        repository=manifest.repository,
        previous_commit=previous.commit,
        commit=commit,
        added=tuple(path for path in added if path not in renamed_paths),
        removed=tuple(path for path in obsolete if path not in renamed_paths),
        modified=tuple(modified),
        renamed=tuple(renamed),
        changed=bool(changes),
    )
    changes.update({target: b"0\n" for target in caches if expected[target].content != b"0\n"})
    if changes and not check:
        replace_all(changes, expected)
        prune_empty_directories((root / path for path in obsolete), root)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mirror the upstream FPF documents")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=Path("config/upstream-docs.json"))
    parser.add_argument("--ref")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-reset-drift", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = sync(
            args.repo_root,
            args.manifest,
            ref=args.ref,
            check=args.check,
            reset_drift=not args.no_reset_drift,
        )
    except (SyncError, OSError) as error:
        print(f"upstream sync: {error}", file=sys.stderr)
        return 2
    print("\n".join(report.lines()))
    if args.check:
        print("Upstream documents differ" if report.changed else "Upstream documents match")
    else:
        print("Upstream documents synchronised")
    return int(report.changed and args.check)


if __name__ == "__main__":
    raise SystemExit(main())
