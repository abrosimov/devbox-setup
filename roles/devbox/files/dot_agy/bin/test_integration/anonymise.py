"""Anonymisation helpers for integration fixtures.

Replaces identifying tokens (usernames, emails, SHAs, timestamps, ...) with
deterministic placeholders. The transformation MUST be idempotent: applying
``anonymise`` twice yields the same result as once.

Used in two places:
- ``extract_fixtures.py`` runs anonymise over every harvested hook payload
  before writing it to disk.
- ``test_anonymise.py`` verifies idempotence and absence of identifying
  artefacts in shipped fixtures.

Stdlib only — fixtures must be reproducible on a CI box that doesn't have
this repo's dev venv.
"""

from __future__ import annotations

import getpass
import os
import re
from typing import Any, Final

# Placeholder strings. Names avoid "TOKEN" so ruff's S105 (hardcoded password)
# heuristic doesn't flag them — they describe sentinel sentinels, not secrets.
HOME_PLACEHOLDER: Final[str] = "<HOME>"
TMPDIR_PLACEHOLDER: Final[str] = "<TMPDIR>"
EMAIL_PLACEHOLDER: Final[str] = "user@example.com"
SHA_PLACEHOLDER: Final[str] = "<SHA>"
TIMESTAMP_PLACEHOLDER: Final[str] = "<TIMESTAMP>"
SECRET_PLACEHOLDER: Final[str] = "<TOKEN>"  # noqa: S105
MAC_PLACEHOLDER: Final[str] = "<MAC>"
IP_PLACEHOLDER: Final[str] = "<IP>"


def _current_user_paths() -> tuple[str, ...]:
    try:
        username = getpass.getuser()
    except (OSError, KeyError):  # pragma: no cover
        username = ""
    candidates = []
    if username:
        candidates.append(f"/Users/{username}/")
        candidates.append(f"/Users/{username}")
        candidates.append(f"/home/{username}/")
        candidates.append(f"/home/{username}")
    env_home = os.environ.get("HOME")
    if env_home and env_home.endswith("/") is False:
        candidates.append(env_home + "/")
        candidates.append(env_home)
    return tuple(candidates)


# ``\b[0-9a-f]{40}\b`` — full git commit SHAs. Anchored to word boundaries so
# we don't match the middle of longer hex sequences.
_SHA_FULL_RE: Final[re.Pattern[str]] = re.compile(r"\b[0-9a-f]{40}\b")

# 7-12 hex chars in clearly git-shaped contexts. Conservative: only inside
# ``commit `` / ``sha:`` / ``HEAD@`` / quoted hashes to avoid hitting unrelated
# hex (colours, hashes-of-other-things). Idempotent because the replacement
# token contains no hex characters.
_SHA_SHORT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<prefix>commit |sha[:=]|HEAD@\{|\"hash\":\s*\")(?P<sha>[0-9a-f]{7,12})\b",
)

# Email — RFC-pragmatic regex. Replacement is deterministic so applying twice
# is a no-op (the placeholder itself is not a valid email by the same regex —
# wait, it is. Guard idempotence by skipping the canonical placeholder.)
_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
)

# ISO timestamps without timezone (the trailing ``Z`` and ``+00:00`` are
# stripped because the body of the timestamp is what we care about).
_ISO_TIMESTAMP_RE: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
)

# API key / bearer token patterns. Conservative — only strings with the
# distinguishing prefix get masked. Anonymised value also doesn't match the
# same prefix, so idempotence holds.
_TOKEN_RES: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghs_[A-Za-z0-9_-]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_-]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}"),
)

# MAC address.
_MAC_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
)

# ``github.com/<user>/<repo>`` — the user segment is identifying. We
# replace ``<user>`` with ``<HOME>`` (overloaded placeholder; it is the
# anonymised "person" token). Idempotent because ``<HOME>`` does not
# match ``[A-Za-z0-9][A-Za-z0-9-]*``.
_GITHUB_URL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<host>github\.com/)(?P<user>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)/",
)

# Generic IPv4. Heuristic: only replace addresses whose first octet is ≥ 24,
# which excludes most version-number-shaped quadruples (``1.2.3.4``,
# ``10.0.0.1`` for loopbacks etc.). The condition lives inside the
# substitution callback so we don't accidentally clobber semver strings.
_IPV4_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b",
)

_MIN_USERNAME_LEN: Final[int] = 4


def _home_replacement(prefix: str) -> str:
    return f"{HOME_PLACEHOLDER}/" if prefix.endswith("/") else HOME_PLACEHOLDER


def _replace_known_path_prefixes(text: str) -> str:
    out = text
    for prefix in _current_user_paths():
        out = out.replace(prefix, _home_replacement(prefix))
    # Defence in depth: any leftover ``/Users/<other>/`` that wasn't current
    # user (e.g. a coworker's path leaked into a session log).
    out = re.sub(r"/Users/[A-Za-z0-9][A-Za-z0-9_.-]*/", f"{HOME_PLACEHOLDER}/", out)
    return re.sub(r"/home/[A-Za-z0-9][A-Za-z0-9_.-]*/", f"{HOME_PLACEHOLDER}/", out)


def _seed_username_candidates() -> set[str]:
    candidates: set[str] = set()
    try:
        user = getpass.getuser()
    except (OSError, KeyError):  # pragma: no cover
        user = ""
    if user:
        candidates.add(user)
    env_user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if env_user:
        candidates.add(env_user)
    env_extras = os.environ.get("PARITY_FIXTURE_EXTRA_PII", "")
    for chunk in env_extras.split(","):
        token = chunk.strip()
        if token:
            candidates.add(token)
    return candidates


def _username_fragments(seeds: set[str]) -> set[str]:
    # Derive partial fragments so embedded usernames inside longer tokens
    # (project names, repo slugs) get masked. Long single-token usernames
    # (``kirillabrosimov``) get 6-char windows so embedded surnames like
    # ``abrosimov`` are caught without an explicit boundary.
    boundary_re = re.compile(r"[._0-9-]+")
    extras: set[str] = set()
    for cand in seeds:
        for part in boundary_re.split(cand):
            if len(part) >= _MIN_USERNAME_LEN + 2:
                extras.add(part)
        if len(cand) >= 10 and cand.isalpha():
            chunk_size = 6
            for start in range(len(cand) - chunk_size + 1):
                extras.add(cand[start : start + chunk_size])
            extras.add(cand[len(cand) // 2 :])
            extras.add(cand[: len(cand) // 2])
    return extras


def _username_candidates() -> set[str]:
    # Standalone occurrences of the current username (not embedded in a path)
    # — captures log messages that name the user without a path prefix.
    candidates = _seed_username_candidates()
    candidates |= _username_fragments(candidates)
    return candidates


def _replace_paths(text: str) -> str:
    out = _replace_known_path_prefixes(text)
    candidates = _username_candidates()
    # Sort by length descending so longer candidates (``kirillabrosimov``)
    # are masked before shorter sub-tokens would try to match an
    # already-replaced string.
    for cand in sorted(candidates, key=len, reverse=True):
        if len(cand) < _MIN_USERNAME_LEN:
            continue
        # Plain substring replacement: identifying surnames frequently appear
        # embedded in project names (e.g. ``kabrosimov_notes``) where ``\b``
        # would skip the match. Candidates are long enough (>= 4 chars) that
        # false positives are negligible.
        out = re.sub(re.escape(cand), HOME_PLACEHOLDER, out, flags=re.IGNORECASE)
    return out


def _replace_tmpdirs(text: str) -> str:
    out = text
    # macOS folders-style temp directory: ``/var/folders/<xx>/<rest>/T/``
    out = re.sub(
        r"/var/folders/[A-Za-z0-9_+-]+/[A-Za-z0-9_+-]+/T/",
        f"{TMPDIR_PLACEHOLDER}/",
        out,
    )
    out = re.sub(
        r"/var/folders/[A-Za-z0-9_+-]+/[A-Za-z0-9_+-]+/T\b",
        TMPDIR_PLACEHOLDER,
        out,
    )
    # System tempdir on the env. Replace before catching ``/tmp/`` so the
    # explicit env-provided value wins.
    env_tmpdir = os.environ.get("TMPDIR")
    if env_tmpdir:
        normalised = env_tmpdir.rstrip("/")
        if normalised and normalised != TMPDIR_PLACEHOLDER:
            out = out.replace(normalised + "/", TMPDIR_PLACEHOLDER + "/")
            out = out.replace(normalised, TMPDIR_PLACEHOLDER)
    out = re.sub(r"/private/tmp/", f"{TMPDIR_PLACEHOLDER}/", out)
    return re.sub(r"(?<![A-Za-z0-9_])/tmp/", f"{TMPDIR_PLACEHOLDER}/", out)


def _replace_shas(text: str) -> str:
    out = _SHA_FULL_RE.sub(SHA_PLACEHOLDER, text)
    return _SHA_SHORT_RE.sub(lambda m: f"{m.group('prefix')}{SHA_PLACEHOLDER}", out)


def _replace_emails(text: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        if match.group(0) == EMAIL_PLACEHOLDER:
            return match.group(0)
        return EMAIL_PLACEHOLDER

    return _EMAIL_RE.sub(_sub, text)


def _replace_timestamps(text: str) -> str:
    return _ISO_TIMESTAMP_RE.sub(TIMESTAMP_PLACEHOLDER, text)


def _replace_tokens(text: str) -> str:
    out = text
    for pattern in _TOKEN_RES:
        out = pattern.sub(SECRET_PLACEHOLDER, out)
    return out


def _replace_macs(text: str) -> str:
    return _MAC_RE.sub(MAC_PLACEHOLDER, text)


def _replace_github_users(text: str) -> str:
    safe_orgs = {
        "anthropic",
        "anthropics",
        "google",
        "golang",
        "modelcontextprotocol",
        "kubernetes",
        "helm",
        "docker",
        "rust-lang",
        "python",
        "npm",
        "node",
        "facebook",
        "meta",
        "openai",
        "microsoft",
        "torvalds",
        "homebrew",
        "Homebrew",
        "go-task",
        "FelixKratz",
        "nikitabobko",
        "neovim",
        "fish-shell",
        "ipython",
        "pytorch",
    }

    def _sub(match: re.Match[str]) -> str:
        host = match.group("host")
        user = match.group("user")
        if user.lower() in {org.lower() for org in safe_orgs}:
            return f"{host}{user}/"
        return f"{host}{HOME_PLACEHOLDER}/"

    return _GITHUB_URL_RE.sub(_sub, text)


def _replace_ipv4(text: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        first = int(match.group(1))
        # Only mask if the leading octet looks like a real IPv4 (≥ 24). This
        # heuristic preserves semver-like ``1.2.3.4`` while still masking
        # ``192.168.x.y`` and any externally-routable address.
        threshold = 24
        if first < threshold:
            return match.group(0)
        max_octet = 255
        for grp in match.groups():
            if int(grp) > max_octet:
                return match.group(0)
        return IP_PLACEHOLDER

    return _IPV4_RE.sub(_sub, text)


def anonymise_text(text: str) -> str:
    # Order matters. Paths first so SHA-like fragments embedded in paths are
    # already framed; tokens before generic email/IP to avoid double-masking
    # bearer tokens that contain @ or dots.
    out = _replace_paths(text)
    out = _replace_tmpdirs(out)
    out = _replace_tokens(out)
    out = _replace_shas(out)
    out = _replace_timestamps(out)
    out = _replace_emails(out)
    out = _replace_github_users(out)
    out = _replace_macs(out)
    return _replace_ipv4(out)


def anonymise(data: Any) -> Any:
    if isinstance(data, str):
        return anonymise_text(data)
    if isinstance(data, list):
        return [anonymise(item) for item in data]
    if isinstance(data, tuple):
        return tuple(anonymise(item) for item in data)
    if isinstance(data, dict):
        return {key: anonymise(value) for key, value in data.items()}
    return data
