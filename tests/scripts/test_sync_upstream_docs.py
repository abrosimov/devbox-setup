from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

import pytest

SPEC = importlib.util.spec_from_file_location(
    "sync_upstream_docs", Path(__file__).resolve().parents[2] / "scripts/sync-upstream-docs.py"
)
assert SPEC is not None
assert SPEC.loader is not None
sync_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sync_module
SPEC.loader.exec_module(sync_module)
COMMIT = "a" * 40
PREVIOUS = "b" * 40
PREFIX = "ailev-FPF-aaaaaaa"
REFERENCES = PurePosixPath("roles/devbox/files/dot_ai/skills/fpf-thinking/references")
SNAPSHOT = REFERENCES / "upstream-snapshot.json"
OWNED = ("Core.md", "Suite/Part One.md")


def tarball(files, *members):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        top = tarfile.TarInfo(PREFIX)
        top.type = tarfile.DIRTYPE
        archive.addfile(top)
        for path, content in files.items():
            info = tarfile.TarInfo(f"{PREFIX}/{path}")
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        for info in members:
            archive.addfile(info)
    return buffer.getvalue()


def special_member(name, kind):
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = f"{PREFIX}/Core.md"
    return info


def snapshot_record(commit, documents):
    files = [
        {
            "source": path,
            "destination": str(REFERENCES / path),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for path, content in sorted(documents.items())
    ]
    record = {"schema_version": 1, "repository": "ailev/FPF", "commit": commit, "files": files}
    return json.dumps(record, indent=2) + "\n"


class TestUpstreamSync:
    @pytest.fixture
    def tree(self, tmp_path, monkeypatch):
        manifest = {
            "schema_version": 2,
            "repository": "ailev/FPF",
            "ref": "main",
            "destination": str(REFERENCES),
        }
        manifest_path = tmp_path / "config/upstream-docs.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(json.dumps(manifest))
        root = tmp_path / REFERENCES
        for path in OWNED:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(b"old\n")
        (root / "bundle-index.md").write_bytes(b"authored\n")
        (tmp_path / SNAPSHOT).write_text(snapshot_record(PREVIOUS, dict.fromkeys(OWNED, b"old\n")))
        cache = tmp_path / "cache/devbox-setup"
        cache.mkdir(parents=True)
        for name in ("fpf-drift", "narrative-drift"):
            (cache / name).write_bytes(b"1\n")
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        return tmp_path

    @pytest.fixture
    def upstream(self):
        return {
            "Core.md": b"# Upstream\n",
            "Suite/Part One.md": b"# Upstream\n",
            "Other.txt": b"not selected\n",
            "Suite/diagram.png": b"\x89PNG",
        }

    @pytest.fixture
    def requests(self, monkeypatch, upstream):
        urls = []

        def fetch(url, **_limits):
            urls.append(url)
            return json.dumps({"sha": COMMIT}).encode() if "/commits/" in url else tarball(upstream)

        monkeypatch.setattr(sync_module, "download", fetch)
        return urls

    def files(self, tree):
        return {
            str(path.relative_to(tree)): path.read_bytes()
            for path in tree.rglob("*")
            if path.is_file()
        }

    def run_sync(self, tree, *, check=False, reset_drift=True):
        return sync_module.sync(
            tree, Path("config/upstream-docs.json"), ref=None, check=check, reset_drift=reset_drift
        )

    def recorded_sources(self, tree):
        return [entry["source"] for entry in json.loads((tree / SNAPSHOT).read_bytes())["files"]]

    @pytest.mark.parametrize("existing", [False, True])
    @pytest.mark.parametrize("external_change", ["content", "mode"])
    def test_rollback_preserves_external_edit_and_recovery_data(
        self, tree, requests, monkeypatch, existing, external_change
    ):
        destination = tree / REFERENCES / "Core.md"
        if not existing:
            destination.unlink()
        replace = os.replace
        calls = 0

        def edit_then_fail(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                if external_change == "content":
                    destination.write_bytes(b"external edit\n")
                else:
                    destination.chmod(0o600)
                msg = "later installation failure"
                raise PermissionError(msg)
            replace(source, target)

        monkeypatch.setattr(sync_module.os, "replace", edit_then_fail)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests
        assert destination.read_bytes() == (
            b"external edit\n" if external_change == "content" else b"# Upstream\n"
        )
        if external_change == "mode":
            assert destination.stat().st_mode & 0o777 == 0o600
        recovery = list(destination.parent.glob(".upstream-docs-*"))
        assert recovery
        if existing:
            assert any((directory / "backup").read_bytes() == b"old\n" for directory in recovery)

    @pytest.mark.parametrize(
        ("name", "expected"),
        [("Part.md", True), ("LICENSE", True), ("diagram.png", False), ("Other.txt", False)],
    )
    def test_only_markdown_and_licence_are_documents(self, name, expected):
        assert sync_module.is_document_name(name) is expected

    @pytest.mark.usefixtures("requests")
    def test_documents_at_any_depth_are_mirrored(self, tree, upstream):
        upstream["DPFs/Suite/Deep.md"] = b"# Deep\n"
        report = self.run_sync(tree)
        assert "DPFs/Suite/Deep.md" in report.added
        assert (tree / REFERENCES / "DPFs/Suite/Deep.md").read_bytes() == b"# Deep\n"
        assert not (tree / REFERENCES / "Other.txt").exists()

    def test_failed_rollback_retains_recovery_bytes(self, tree, requests, monkeypatch):
        replace = os.replace
        count = 0

        def fail_after_first(source, target):
            nonlocal count
            count += 1
            if count > 1:
                msg = "persistent rename failure"
                raise PermissionError(msg)
            replace(source, target)

        monkeypatch.setattr(sync_module.os, "replace", fail_after_first)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests
        backups = list(tree.rglob(".upstream-docs-*/backup"))
        assert backups
        assert any(path.read_bytes() == b"old\n" for path in backups)
        assert (tree / "cache/devbox-setup/fpf-drift").read_bytes() == b"1\n"

    def test_check_ref_override_has_no_filesystem_effects(self, tree, requests):
        before = self.files(tree)
        result = sync_module.main(["--repo-root", str(tree), "--check", "--ref", COMMIT])
        assert result == 1
        assert requests[0].endswith("/commits/" + COMMIT)
        assert self.files(tree) == before

    @pytest.mark.parametrize("response", [b"{}", b'{"sha":"main"}', b"<html>error</html>"])
    def test_invalid_commit_response_preserves_all(self, tree, monkeypatch, response):
        before = self.files(tree)
        monkeypatch.setattr(sync_module, "download", lambda _url, **_limits: response)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert self.files(tree) == before

    def fake_curl(self, monkeypatch, responses):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            outcome = responses[min(len(calls), len(responses)) - 1]
            if outcome == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            code, status = outcome
            Path(command[command.index("--output") + 1]).write_bytes(b"# doc")
            return subprocess.CompletedProcess(command, code, status, b"curl: (56) failure")

        monkeypatch.setattr(sync_module.subprocess, "run", run)
        monkeypatch.setattr(sync_module.time, "sleep", lambda _seconds: None)
        return calls

    def fetch_doc(self):
        return sync_module.download("https://example.test/doc", max_bytes=1024, max_seconds=5)

    @pytest.mark.parametrize("code", [0, 22, 56])
    def test_http_error_reports_status_without_retry(self, monkeypatch, code):
        calls = self.fake_curl(monkeypatch, [(code, b"404")])
        with pytest.raises(sync_module.SyncError, match="HTTP 404"):
            self.fetch_doc()
        assert len(calls) == 1

    @pytest.mark.parametrize("failure", ["timeout", (0, b"503"), (56, b"000"), (28, b"000")])
    def test_transient_failures_retry_then_give_up(self, monkeypatch, failure):
        calls = self.fake_curl(monkeypatch, [failure])
        with pytest.raises(sync_module.SyncError, match="gave up after 3 attempts"):
            self.fetch_doc()
        assert len(calls) == sync_module.ATTEMPTS

    def test_transient_failure_recovers_on_retry(self, monkeypatch):
        calls = self.fake_curl(monkeypatch, [(0, b"503"), (56, b"000"), (0, b"200")])
        assert self.fetch_doc() == b"# doc"
        assert len(calls) == 3

    def test_permanent_curl_failure_is_not_retried(self, monkeypatch):
        calls = self.fake_curl(monkeypatch, [(63, b"200")])
        with pytest.raises(sync_module.SyncError, match="curl exit 63"):
            self.fetch_doc()
        assert len(calls) == 1

    def test_pinned_archive_provenance_idempotence_and_read_only_check(self, tree, requests):
        before = self.files(tree)
        assert self.run_sync(tree, check=True).changed
        assert self.files(tree) == before
        assert self.run_sync(tree).changed
        assert not self.run_sync(tree).changed
        assert not self.run_sync(tree, check=True).changed
        assert len([url for url in requests if "/commits/" in url]) == 4
        archives = [url for url in requests if "/commits/" not in url]
        assert archives == [f"https://api.github.com/repos/ailev/FPF/tarball/{COMMIT}"] * 4
        record = json.loads((tree / SNAPSHOT).read_bytes())
        assert record["commit"] == COMMIT
        assert self.recorded_sources(tree) == list(OWNED)
        assert (tree / "cache/devbox-setup/fpf-drift").read_bytes() == b"0\n"
        assert (tree / REFERENCES / "bundle-index.md").read_bytes() == b"authored\n"

    @pytest.mark.usefixtures("requests")
    def test_rename_is_detected_and_applied(self, tree, upstream):
        upstream.clear()
        upstream.update({"Core.md": b"old\n", "Suite/Renamed.md": b"old\n"})
        report = self.run_sync(tree)
        assert report.renamed == (("Suite/Part One.md", "Suite/Renamed.md"),)
        assert (report.added, report.removed, report.modified) == ((), (), ())
        assert not (tree / REFERENCES / "Suite/Part One.md").exists()
        assert (tree / REFERENCES / "Suite/Renamed.md").read_bytes() == b"old\n"
        assert self.recorded_sources(tree) == ["Core.md", "Suite/Renamed.md"]

    @pytest.mark.usefixtures("requests")
    def test_removal_deletes_owned_file_and_prunes_empty_directory(self, tree, upstream):
        del upstream["Suite/Part One.md"]
        report = self.run_sync(tree)
        assert report.removed == ("Suite/Part One.md",)
        assert report.modified == ("Core.md",)
        assert not (tree / REFERENCES / "Suite").exists()
        assert (tree / REFERENCES / "bundle-index.md").read_bytes() == b"authored\n"
        assert self.recorded_sources(tree) == ["Core.md"]

    @pytest.mark.usefixtures("requests")
    def test_removal_preserves_unowned_files(self, tree, upstream):
        local = tree / REFERENCES / "Suite/Local.md"
        local.write_bytes(b"mine\n")
        del upstream["Suite/Part One.md"]
        self.run_sync(tree)
        assert local.read_bytes() == b"mine\n"
        assert not (tree / REFERENCES / "Suite/Part One.md").exists()
        assert (tree / REFERENCES / "bundle-index.md").read_bytes() == b"authored\n"

    @pytest.mark.usefixtures("requests")
    def test_refuses_to_overwrite_unowned_file(self, tree, upstream):
        (tree / REFERENCES / "Suite/Local.md").write_bytes(b"mine\n")
        upstream["Suite/Local.md"] = b"# Upstream\n"
        before = self.files(tree)
        with pytest.raises(sync_module.SyncError, match="does not own"):
            self.run_sync(tree)
        assert self.files(tree) == before

    @pytest.mark.usefixtures("requests")
    def test_empty_match_refuses_to_empty_bundle(self, tree, upstream):
        upstream.clear()
        upstream["Other.txt"] = b"not selected\n"
        before = self.files(tree)
        with pytest.raises(sync_module.SyncError, match="refusing to empty"):
            self.run_sync(tree)
        assert self.files(tree) == before

    @pytest.mark.usefixtures("requests")
    def test_case_only_rename_is_refused(self, tree, upstream):
        upstream["Suite/part one.md"] = upstream.pop("Suite/Part One.md")
        before = self.files(tree)
        with pytest.raises(sync_module.SyncError, match="differ only by case"):
            self.run_sync(tree)
        assert self.files(tree) == before

    @pytest.mark.usefixtures("requests")
    def test_deletion_rolls_back_on_failure(self, tree, upstream, monkeypatch):
        upstream.clear()
        upstream["Core.md"] = b"old\n"
        before = self.files(tree)
        replace = os.replace
        count = 0

        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                msg = "injected rename failure"
                raise PermissionError(msg)
            replace(source, target)

        monkeypatch.setattr(sync_module.os, "replace", fail_second)
        with pytest.raises(PermissionError):
            self.run_sync(tree)
        assert self.files(tree) == before

    @pytest.mark.parametrize(
        "member",
        [
            special_member(f"{PREFIX}/Suite/Evil.md", tarfile.SYMTYPE),
            special_member(f"{PREFIX}/Suite/Evil.md", tarfile.LNKTYPE),
            special_member(f"{PREFIX}/Suite/Evil.md", tarfile.CHRTYPE),
            special_member(f"{PREFIX}/../escape.md", tarfile.REGTYPE),
            special_member("/etc/escape.md", tarfile.REGTYPE),
            special_member("other-top/Core.md", tarfile.REGTYPE),
        ],
    )
    def test_unsafe_archive_members_are_refused(self, tree, monkeypatch, upstream, member):
        archive = tarball(upstream, member)
        monkeypatch.setattr(
            sync_module,
            "download",
            lambda url, **_limits: (
                json.dumps({"sha": COMMIT}).encode() if "/commits/" in url else archive
            ),
        )
        before = self.files(tree)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert self.files(tree) == before

    def test_non_document_links_are_ignored(self, upstream):
        archive = tarball(upstream, special_member(f"{PREFIX}/link.txt", tarfile.SYMTYPE))
        documents = sync_module.extract_documents(archive)
        assert set(documents) == {"Core.md", "Suite/Part One.md"}

    def test_oversized_document_is_refused(self, upstream, monkeypatch):
        monkeypatch.setattr(sync_module, "MAX_DOCUMENT_BYTES", 4)
        with pytest.raises(sync_module.SyncError, match="exceeds"):
            sync_module.extract_documents(tarball(upstream))

    def test_corrupt_archive_is_refused(self):
        with pytest.raises(sync_module.SyncError, match="gzip tarball"):
            sync_module.extract_documents(b"<html>error</html>")

    @pytest.mark.usefixtures("requests")
    def test_check_prints_report_without_changes(self, tree, upstream, capsys):
        upstream.clear()
        upstream.update(
            {"Core.md": b"old\n", "Suite/Renamed.md": b"old\n", "Suite/New.md": b"# New\n"}
        )
        before = self.files(tree)
        assert sync_module.main(["--repo-root", str(tree), "--check"]) == 1
        output = capsys.readouterr().out
        assert f"ailev/FPF: {PREVIOUS} -> {COMMIT}" in output
        assert "renamed  Suite/Part One.md -> Suite/Renamed.md" in output
        assert "added    Suite/New.md" in output
        assert "Upstream documents differ" in output
        assert self.files(tree) == before

    @pytest.mark.usefixtures("requests")
    def test_check_reports_absence_of_changes(self, tree, capsys):
        self.run_sync(tree)
        capsys.readouterr()
        assert sync_module.main(["--repo-root", str(tree), "--check"]) == 0
        output = capsys.readouterr().out
        assert f"ailev/FPF: {COMMIT} -> {COMMIT}" in output
        assert "no document changes" in output
        assert "Upstream documents match" in output

    @pytest.mark.parametrize(
        "failure", ["download", "invalid", "manifest-edit", "target-edit", "provenance-edit"]
    )
    def test_late_failure_preserves_documents_provenance_and_cache(
        self, tree, monkeypatch, upstream, failure
    ):
        before = self.files(tree)
        edited = None

        def fetch(url, **_limits):
            nonlocal edited
            if "/commits/" in url:
                return json.dumps({"sha": COMMIT}).encode()
            if failure == "download":
                msg = "late failure"
                raise sync_module.SyncError(msg)
            if failure == "invalid":
                return tarball({"Core.md": b"<html>Error</html>"})
            edited = (
                tree
                / {
                    "manifest-edit": "config/upstream-docs.json",
                    "target-edit": str(REFERENCES / "Core.md"),
                    "provenance-edit": str(SNAPSHOT),
                }[failure]
            )
            edited.write_bytes(b"concurrent edit")
            return tarball(upstream)

        monkeypatch.setattr(sync_module, "download", fetch)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        if edited is not None:
            before[str(edited.relative_to(tree))] = b"concurrent edit"
        assert self.files(tree) == before

    @pytest.mark.parametrize("fail_at", [2, 4])
    def test_write_failure_rolls_back_all_changed_files(self, tree, requests, monkeypatch, fail_at):
        before = self.files(tree)
        replace = os.replace
        count = 0

        def fail_once(source, target):
            nonlocal count
            count += 1
            if count == fail_at:
                msg = "injected rename failure"
                raise PermissionError(msg)
            replace(source, target)

        monkeypatch.setattr(sync_module.os, "replace", fail_once)
        with pytest.raises(PermissionError):
            self.run_sync(tree)
        assert self.files(tree) == before
        assert requests

    def test_no_reset_leaves_cache_unchanged(self, tree, requests):
        self.run_sync(tree, reset_drift=False)
        assert requests
        assert (tree / "cache/devbox-setup/fpf-drift").read_bytes() == b"1\n"

    @pytest.mark.parametrize(
        "content", [b"", b" \n", b"\xff", b"<!DOCTYPE html><title>error</title>", b"\x00"]
    )
    def test_rejects_bad_document(self, content):
        with pytest.raises(sync_module.SyncError):
            sync_module.validate_markdown(content)

    @pytest.mark.parametrize(
        "mutation",
        [
            "unknown",
            "include",
            "destination-escape",
            "legacy-files",
        ],
    )
    def test_manifest_rejection_before_network(self, tree, requests, mutation):
        path = tree / "config/upstream-docs.json"
        value = json.loads(path.read_bytes())
        if mutation == "unknown":
            value["unknown"] = True
        elif mutation == "include":
            value["include"] = ["*.md"]
        elif mutation == "destination-escape":
            value["destination"] = "../outside"
        elif mutation == "legacy-files":
            value = {
                "schema_version": 1,
                "repository": "ailev/FPF",
                "ref": "main",
                "files": [{"source": "Core.md", "destination": str(REFERENCES / "Core.md")}],
            }
        path.write_text(json.dumps(value))
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests == []

    @pytest.mark.parametrize("snapshot", [b"not json", b'{"schema_version": 9}', b"{}"])
    def test_unreadable_snapshot_is_refused_before_network(self, tree, requests, snapshot):
        (tree / SNAPSHOT).write_bytes(snapshot)
        with pytest.raises(sync_module.SyncError, match="snapshot"):
            self.run_sync(tree)
        assert requests == []

    def test_snapshot_cannot_claim_files_outside_destination(self, tree, requests):
        record = json.loads((tree / SNAPSHOT).read_bytes())
        record["files"][0]["source"] = "../../outside.md"
        (tree / SNAPSHOT).write_text(json.dumps(record))
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests == []

    def test_destination_symlink_rejected(self, tree, requests):
        destination = tree / REFERENCES / "Core.md"
        destination.unlink()
        destination.symlink_to(tree / "config/upstream-docs.json")
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests == []

    def test_competing_sync_rejected_without_network(self, tree, requests):
        descriptor = os.open(tree, os.O_RDONLY)
        try:
            sync_module.fcntl.flock(descriptor, sync_module.fcntl.LOCK_EX)
            with pytest.raises(sync_module.SyncError):
                self.run_sync(tree)
        finally:
            os.close(descriptor)
        assert requests == []

    def test_curl_is_bounded_and_has_no_shell(self, monkeypatch):
        def run(command, **kwargs):
            assert command[:2] == ["curl", "--disable"]
            assert command[-1] == "https://example.test/doc"
            assert command[command.index("--max-time") + 1] == "5"
            assert command[command.index("--max-filesize") + 1] == "1024"
            assert command[command.index("--proto") + 1] == "=https"
            assert "--fail" not in command
            assert kwargs["timeout"] == 20
            assert "shell" not in kwargs
            Path(command[command.index("--output") + 1]).write_bytes(b"# doc")
            return subprocess.CompletedProcess(command, 0, b"200", b"")

        monkeypatch.setattr(sync_module.subprocess, "run", run)
        assert self.fetch_doc() == b"# doc"

    def test_oversized_response_is_refused(self, monkeypatch):
        def run(command, **_kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(b"x" * 2048)
            return subprocess.CompletedProcess(command, 0, b"200", b"")

        monkeypatch.setattr(sync_module.subprocess, "run", run)
        with pytest.raises(sync_module.SyncError, match="exceeds"):
            self.fetch_doc()
