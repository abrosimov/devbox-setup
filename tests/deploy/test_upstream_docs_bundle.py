from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = PurePosixPath("roles/devbox/files/dot_ai/skills/fpf-thinking/references")


class TestUpstreamDocsBundle:
    def test_portable_bundle_matches_manifest_and_commit_provenance(self):
        manifest = json.loads((ROOT / "config/upstream-docs.json").read_bytes())
        provenance = json.loads((ROOT / REFERENCES / "upstream-snapshot.json").read_bytes())
        assert provenance["schema_version"] == 1
        assert provenance["repository"] == manifest["repository"]
        assert re.fullmatch(r"[0-9a-f]{40}", provenance["commit"])
        assert len(provenance["files"]) == len(manifest["files"])
        records = {entry["destination"]: entry for entry in provenance["files"]}
        assert len(records) == len(manifest["files"])
        for entry in manifest["files"]:
            destination = PurePosixPath(entry["destination"])
            assert REFERENCES in destination.parents
            assert destination.relative_to(REFERENCES).as_posix() == entry["source"]
            assert ".." not in destination.parts
            target = ROOT / destination
            assert target.is_file()
            assert not target.is_symlink()
            record = records[entry["destination"]]
            assert record["source"] == entry["source"]
            assert record["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()

    def test_authored_index_relative_file_links_resolve(self):
        directory = ROOT / REFERENCES
        source = (directory / "bundle-index.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]\n]+\]\((?:<([^>]+)>|([^\s)]+))\)", source)
        assert links
        for enclosed, bare in links:
            link = urlsplit(enclosed or bare)
            if link.scheme or link.netloc or not link.path:
                continue
            target = (directory / unquote(link.path)).resolve()
            assert target.is_relative_to(directory.resolve())
            assert target.is_file(), enclosed or bare
