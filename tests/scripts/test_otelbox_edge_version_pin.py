"""The otelbox edge version pin has exactly one home: defaults/main/packages.yml.

scripts/otelbox-edge-test.sh must derive it, never repeat it — a repeated literal is
how a version bump ends up asserting the previous release. The extraction awk is read
out of the script and executed against the real defaults file.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/otelbox-edge-test.sh"
PACKAGES = REPO_ROOT / "roles/devbox/defaults/main/packages.yml"

_script_text = SCRIPT.read_text(encoding="utf-8")
_extraction = re.search(
    r"pinned=\$\(awk '(?P<program>.*?)'\s*\"\$\{REPO_ROOT\}/(?P<path>[^\"]+)\"",
    _script_text,
    re.DOTALL,
)

PINNED_VERSION: str = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))["devbox_packages"][
    "otelbox_edge"
]["version"]

# A three-component number is a version; a four-component one is an IPv4 literal
# (127.0.0.1 appears throughout the probe URLs and is legitimate).
_DOTTED_NUMBER = re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b")


def test_extraction_block_is_present() -> None:
    assert _extraction is not None, "version extraction awk not found in the script"


def test_extraction_reads_the_defaults_file() -> None:
    assert _extraction is not None
    assert (REPO_ROOT / _extraction.group("path")).resolve() == PACKAGES.resolve()


def test_extraction_returns_the_pinned_version() -> None:
    assert _extraction is not None
    result = subprocess.run(
        ["/usr/bin/awk", _extraction.group("program"), str(PACKAGES)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == PINNED_VERSION


def test_no_hardcoded_version_literal() -> None:
    versions = [m for m in _DOTTED_NUMBER.findall(_script_text) if m.count(".") != 3]
    assert versions == [], f"hardcoded version literal(s) in {SCRIPT.name}: {versions}"
