from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

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


class TestUpstreamSync:
    @pytest.mark.parametrize("existing", [False, True])
    @pytest.mark.parametrize("external_change", ["content", "mode"])
    def test_rollback_preserves_external_edit_and_recovery_data(
        self, tree, requests, monkeypatch, existing, external_change
    ):
        destination = tree / sync_module.REFERENCES / "Core.md"
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

    def test_licences_are_manifest_documents(self):
        entry = {
            "source": "Engineering DPF Suite/LICENSE",
            "destination": str(sync_module.REFERENCES / "Engineering DPF Suite/LICENSE"),
        }
        assert sync_module.parse_document(entry).source == entry["source"]

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
        before = self.snapshot(tree)
        result = sync_module.main(["--repo-root", str(tree), "--check", "--ref", COMMIT])
        assert result == 1
        assert requests[0].endswith("/commits/" + COMMIT)
        assert self.snapshot(tree) == before

    @pytest.mark.parametrize("response", [b"{}", b'{"sha":"main"}', b"<html>error</html>"])
    def test_invalid_commit_response_preserves_all(self, tree, monkeypatch, response):
        before = self.snapshot(tree)
        monkeypatch.setattr(sync_module, "download", lambda _url: response)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert self.snapshot(tree) == before

    @pytest.mark.parametrize("failure", ["timeout", "http"])
    def test_curl_errors_are_bounded_failures(self, monkeypatch, failure):
        def run(command, **kwargs):
            if failure == "timeout":
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            return subprocess.CompletedProcess(command, 22, b"", b"http error")

        monkeypatch.setattr(sync_module.subprocess, "run", run)
        with pytest.raises(sync_module.SyncError):
            sync_module.download("https://example.test/doc")

    @pytest.fixture
    def tree(self, tmp_path, monkeypatch):
        manifest = {
            "schema_version": 1,
            "repository": "ailev/FPF",
            "ref": "main",
            "files": [
                {"source": "Core.md", "destination": str(sync_module.REFERENCES / "Core.md")},
                {
                    "source": "Suite/Part One.md",
                    "destination": str(sync_module.REFERENCES / "Suite/Part One.md"),
                },
            ],
        }
        manifest_path = tmp_path / "config/upstream-docs.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(json.dumps(manifest))
        for entry in manifest["files"]:
            path = tmp_path / entry["destination"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"old\n")
        provenance = tmp_path / sync_module.PROVENANCE
        provenance.write_bytes(b"old provenance\n")
        cache = tmp_path / "cache/devbox-setup"
        cache.mkdir(parents=True)
        for name in ("fpf-drift", "narrative-drift"):
            (cache / name).write_bytes(b"1\n")
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        return tmp_path

    @pytest.fixture
    def requests(self, monkeypatch):
        urls = []

        def fetch(url):
            urls.append(url)
            return (
                json.dumps({"sha": COMMIT}).encode() if "api.github.com" in url else b"# Upstream\n"
            )

        monkeypatch.setattr(sync_module, "download", fetch)
        return urls

    def snapshot(self, tree):
        return {
            str(path.relative_to(tree)): path.read_bytes()
            for path in tree.rglob("*")
            if path.is_file()
        }

    def run_sync(self, tree, *, check=False, reset_drift=True):
        return sync_module.sync(
            tree, Path("config/upstream-docs.json"), ref=None, check=check, reset_drift=reset_drift
        )

    def test_pinned_urls_provenance_idempotence_and_read_only_check(self, tree, requests):
        before = self.snapshot(tree)
        assert self.run_sync(tree, check=True)
        assert self.snapshot(tree) == before
        assert self.run_sync(tree)
        assert not self.run_sync(tree)
        assert not self.run_sync(tree, check=True)
        assert len([url for url in requests if "api.github.com" in url]) == 4
        assert all(f"/{COMMIT}/" in url for url in requests if "raw.githubusercontent.com" in url)
        assert any("Part%20One.md" in url for url in requests)
        record = json.loads((tree / sync_module.PROVENANCE).read_bytes())
        assert record["commit"] == COMMIT
        assert len(record["files"]) == 2
        assert (tree / "cache/devbox-setup/fpf-drift").read_bytes() == b"0\n"

    @pytest.mark.parametrize(
        "failure", ["download", "invalid", "manifest-edit", "target-edit", "provenance-edit"]
    )
    def test_late_failure_preserves_documents_provenance_and_cache(
        self, tree, monkeypatch, failure
    ):
        before = self.snapshot(tree)
        calls = 0
        edited = None

        def fetch(url):
            nonlocal calls, edited
            calls += 1
            if calls == 3:
                if failure == "download":
                    msg = "late failure"
                    raise sync_module.SyncError(msg)
                if failure == "invalid":
                    return b"<html>Error</html>"
                edited = (
                    tree
                    / {
                        "manifest-edit": "config/upstream-docs.json",
                        "target-edit": str(sync_module.REFERENCES / "Core.md"),
                        "provenance-edit": sync_module.PROVENANCE,
                    }[failure]
                )
                edited.write_bytes(b"concurrent edit")
            return (
                json.dumps({"sha": COMMIT}).encode() if "api.github.com" in url else b"# Upstream\n"
            )

        monkeypatch.setattr(sync_module, "download", fetch)
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        if edited is not None:
            before[str(edited.relative_to(tree))] = b"concurrent edit"
        assert self.snapshot(tree) == before

    @pytest.mark.parametrize("fail_at", [2, 4])
    def test_write_failure_rolls_back_all_changed_files(self, tree, requests, monkeypatch, fail_at):
        before = self.snapshot(tree)
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
        assert self.snapshot(tree) == before
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
        "mutation", ["unknown", "duplicate", "escape", "absolute", "source-escape", "reserved"]
    )
    def test_manifest_rejection_before_network(self, tree, requests, mutation):
        path = tree / "config/upstream-docs.json"
        value = json.loads(path.read_bytes())
        if mutation == "unknown":
            value["unknown"] = True
        elif mutation == "duplicate":
            value["files"].append(value["files"][0])
        elif mutation == "source-escape":
            value["files"][0]["source"] = "../outside.md"
        else:
            value["files"][0]["destination"] = {
                "escape": "../outside.md",
                "absolute": str(tree / "outside.md"),
                "reserved": sync_module.PROVENANCE,
            }[mutation]
        path.write_text(json.dumps(value))
        with pytest.raises(sync_module.SyncError):
            self.run_sync(tree)
        assert requests == []

    def test_destination_symlink_rejected(self, tree, requests):
        destination = tree / sync_module.REFERENCES / "Core.md"
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
            assert "--max-time" in command
            assert kwargs["timeout"] == 50
            assert "shell" not in kwargs
            return subprocess.CompletedProcess(command, 0, b"# doc", b"")

        monkeypatch.setattr(sync_module.subprocess, "run", run)
        assert sync_module.download("https://example.test/doc") == b"# doc"
