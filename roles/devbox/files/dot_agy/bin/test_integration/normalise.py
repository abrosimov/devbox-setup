"""Canonicalisation of stdout/stderr before assertion.

Scripts can differ in *form* (trailing newlines, ANSI escape codes,
per-invocation random tokens) without differing in *semantics*. This module
strips those incidentals so that fixture-driven assertions compare what
actually matters.
"""

from __future__ import annotations

import re
from typing import Final

from test_integration.anonymise import anonymise_text

_ANSI_ESCAPE_RE: Final[re.Pattern[str]] = re.compile(
    # CSI sequences (most ANSI escapes used in our scripts).
    r"\x1b\[[0-?]*[ -/]*[@-~]",
)

_TRUECOLOR_RE: Final[re.Pattern[str]] = re.compile(
    r"\x1b\[(?:38|48);2;\d+;\d+;\d+m",
)

# pre-bash-boundary-wrap generates a per-invocation random hex token in the
# boundary tag name (see `bin/pre-bash-boundary-wrap`). Strip it so two runs
# of the same input compare equal.
_BOUNDARY_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"untrusted-content-[0-9a-f]{8,}",
)


def strip_boundary_tokens(text: str) -> str:
    if not text:
        return text
    return _BOUNDARY_TOKEN_RE.sub("untrusted-content-<TOKEN>", text)


def strip_ansi(text: str) -> str:
    if not text:
        return text
    out = _TRUECOLOR_RE.sub("", text)
    return _ANSI_ESCAPE_RE.sub("", out)


def strip_trailing_whitespace(text: str) -> str:
    if not text:
        return text
    return "\n".join(line.rstrip() for line in text.splitlines()) + (
        "\n" if text.endswith("\n") else ""
    )


def normalise_text(text: str) -> str:
    if not text:
        return ""
    out = strip_ansi(text)
    out = strip_boundary_tokens(out)
    out = anonymise_text(out)
    out = strip_trailing_whitespace(out)
    return out.strip()
