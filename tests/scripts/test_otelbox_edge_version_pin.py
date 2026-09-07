from __future__ import annotations

import re
from pathlib import Path

import yaml
from otelbox_edge.smoke import read_pinned_version

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "scripts/otelbox_edge/smoke.py"
PACKAGES = REPO_ROOT / "roles/devbox/defaults/main/packages.yml"
PINNED_VERSION: str = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))["devbox_packages"][
    "otelbox_edge"
]["version"]
DOTTED_NUMBER = re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b")


class TestVersionPin:
    def test_parser_reads_the_authoritative_defaults_value(self) -> None:
        assert read_pinned_version(PACKAGES) == PINNED_VERSION

    def test_smoke_source_has_no_hardcoded_version(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        versions = [match for match in DOTTED_NUMBER.findall(source) if match.count(".") != 3]

        assert versions == []
