from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = PurePosixPath("roles/devbox/files/dot_ai/skills/fpf-thinking/references")


AUTHORED = {"bundle-index.md"}


def is_mirrored(path):
    name = PurePosixPath(path).name
    return path not in AUTHORED and (name.endswith(".md") or name == "LICENSE")


class TestUpstreamDocsBundle:
    def test_snapshot_records_exactly_the_mirrored_files_on_disk(self):
        manifest = json.loads((ROOT / "config/upstream-docs.json").read_bytes())
        assert manifest["destination"] == str(REFERENCES)
        provenance = json.loads((ROOT / REFERENCES / "upstream-snapshot.json").read_bytes())
        assert provenance["schema_version"] == 1
        assert provenance["repository"] == manifest["repository"]
        assert re.fullmatch(r"[0-9a-f]{40}", provenance["commit"])
        root = ROOT / REFERENCES
        on_disk = {
            path.relative_to(root).as_posix(): path
            for path in root.rglob("*")
            if path.is_file() and is_mirrored(path.relative_to(root).as_posix())
        }
        records = {record["source"]: record for record in provenance["files"]}
        assert len(records) == len(provenance["files"])
        assert set(records) == set(on_disk)
        for source, record in records.items():
            assert record["destination"] == (REFERENCES / source).as_posix()
            target = on_disk[source]
            assert not target.is_symlink()
            assert record["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()

    def test_documents_named_by_skills_are_present(self):
        for source in (
            "FPF-Spec.md",
            "LICENSE",
            "DPFs/Narrativization-and-Narrative-Studies-Principles-Framework.md",
        ):
            assert (ROOT / REFERENCES / source).is_file(), source

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
