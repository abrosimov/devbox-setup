#!/usr/bin/env python3
"""Fetch and compare CI run timings from GitHub Actions (through gh) or GitLab CI (through glab).

  history  list completed runs (GitHub) or successful pipelines (GitLab) of one branch, as TSV
  fetch    store each run's API JSON under DIR: run-ID.json, jobs-ID.json, timings-ID.tsv, and
           with --sections (GitLab) sections-ID.json parsed from the job logs
  report   print one stored run: job timeline, exact runner time, billed estimate, slow steps
  compare  print two stored runs and their per-job and per-phase difference

The provider is chosen from the host of the repository remote and from what gh and glab are
authenticated for; --provider, --host and --repo override it. Every API call is a GET: the
script never triggers, re-runs or cancels a run.

Phases split each job at its work: on GitHub, the leading "Set up job" and unnamed action
steps ("Run owner/action@ref") are set-up, and the trailing "Post ..." steps, unnamed action
steps and "Complete job" come after the work. On GitLab the same split uses the runner's
top-level log sections, so it needs fetch --sections.

Exit status: 0 when every requested run was read; 2 on a usage, detection or input-file error
or a missing gh/glab; 3 when gh/glab is not authenticated for the host; 4 when an API call
fails or a command times out. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast
from urllib.parse import quote, urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

PROG: Final = "ci_run_timings"

EXIT_OK: Final = 0
EXIT_USAGE: Final = 2
EXIT_AUTH: Final = 3
EXIT_API: Final = 4

GITHUB: Final = "github"
GITLAB: Final = "gitlab"
TOOLS: Final[dict[str, str]] = {GITHUB: "gh", GITLAB: "glab"}
CLI_NAMES: Final[dict[str, str]] = {GITHUB: "GitHub CLI", GITLAB: "GitLab CLI"}
DEFAULT_HOSTS: Final[dict[str, str]] = {GITHUB: "github.com", GITLAB: "gitlab.com"}

GIT_TIMEOUT_S: Final = 10.0
# gh auth status checks each stored token against the host over the network.
AUTH_TIMEOUT_S: Final = 30.0
API_TIMEOUT_S: Final = 120.0
# A job log can run to several megabytes.
LOG_TIMEOUT_S: Final = 300.0

PAGE_SIZE: Final = 100
DEFAULT_HISTORY_LIMIT: Final = 30
DEFAULT_MIN_STEP_S: Final = 30.0

TIMING_COLUMNS: Final = (
    "provider",
    "run_id",
    "attempt",
    "job_id",
    "job_name",
    "stage",
    "status",
    "conclusion",
    "queued_s",
    "start_offset_s",
    "duration_s",
    "billed_min_estimate",
    "step_number",
    "step_name",
    "step_duration_s",
)
HISTORY_COLUMNS: Final = (
    "provider",
    "run_id",
    "attempt",
    "branch",
    "sha",
    "status",
    "conclusion",
    "created_at",
    "wall_s",
)

GITLAB_TERMINAL: Final = frozenset({"success", "failed", "canceled", "skipped"})
GITHUB_ACTION_STEP: Final = r"Run [\w.-]+/[\w./-]+@\S+"
GITHUB_PRELUDE: Final = re.compile(rf"^(?:Set up job|Initialize containers|{GITHUB_ACTION_STEP})$")
GITHUB_POSTLUDE: Final = re.compile(
    rf"^(?:Post .+|Complete job|Stop containers|{GITHUB_ACTION_STEP})$"
)
# Section names that GitLab Runner writes into job logs; not checked against its documentation.
GITLAB_PRELUDE: Final = frozenset(
    {
        "resolve_secrets",
        "prepare_executor",
        "prepare_script",
        "get_sources",
        "clear_worktree",
        "restore_cache",
        "download_artifacts",
    }
)
GITLAB_POSTLUDE: Final = frozenset(
    {
        "after_script",
        "archive_cache",
        "archive_cache_on_failure",
        "upload_artifacts_on_success",
        "upload_artifacts_on_failure",
        "cleanup_file_variables",
    }
)
SECTION_MARKER: Final = re.compile(r"\x1b\[0Ksection_(start|end):(\d+):([A-Za-z0-9_.-]+)")

SCP_LIKE_URL: Final = re.compile(r"^(?:[^@/:]+@)?(?P<host>[^/:]+):(?P<path>[^/].*)$")
URL_SCHEMES: Final = frozenset({"ssh", "git+ssh", "git", "http", "https"})
DEFAULT_PORTS: Final[dict[str, int]] = {"http": 80, "https": 443}
PATH_SEGMENT: Final = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_.-]*$")
REMOTE_NAME: Final = re.compile(r"^[A-Za-z0-9_.][A-Za-z0-9_./-]*$")

type JsonObject = dict[str, object]
type Runner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]
type Which = Callable[[str], str | None]


class CiTimingsError(Exception):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class DataError(ValueError):
    pass


def run_command(args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        msg = f"timed out after {timeout:.0f}s: {shlex.join(args)}"
        raise CiTimingsError(msg, EXIT_API) from err
    except OSError as err:
        msg = f"cannot run {shlex.join(args)}: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def describe_failure(args: Sequence[str], result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stderr or "").strip()
    head = f"command failed with exit {result.returncode}: {shlex.join(args)}"
    return f"{head}\n{detail}" if detail else head


def _as_object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return cast("JsonObject", value)
    msg = f"expected a JSON object, got {type(value).__name__}"
    raise DataError(msg)


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return cast("list[object]", value)
    msg = f"expected a JSON array, got {type(value).__name__}"
    raise DataError(msg)


def _text(obj: JsonObject, key: str) -> str:
    value = obj.get(key)
    return value if isinstance(value, str) else ""


def _int(obj: JsonObject, key: str) -> int | None:
    value = obj.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _required_int(obj: JsonObject, key: str) -> int:
    value = _int(obj, key)
    if value is None:
        msg = f"missing integer field {key!r}"
        raise DataError(msg)
    return value


def _number(obj: JsonObject, key: str) -> float | None:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _timestamp(obj: JsonObject, key: str) -> float | None:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as err:
        msg = f"field {key!r} is not an ISO 8601 timestamp: {value!r}"
        raise DataError(msg) from err
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _span(start: float | None, end: float | None) -> float | None:
    return None if start is None or end is None else end - start


def decode_json_stream(text: str) -> list[object]:
    decoder = json.JSONDecoder()
    values: list[object] = []
    index = 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return values
        try:
            value, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as err:
            msg = f"invalid JSON: {err}"
            raise DataError(msg) from err
        values.append(value)


def _single_object(values: list[object]) -> JsonObject:
    if len(values) != 1:
        msg = f"expected one JSON document, got {len(values)}"
        raise DataError(msg)
    return _as_object(values[0])


def merge_pages(pages: Iterable[object], key: str | None) -> list[JsonObject]:
    items: list[JsonObject] = []
    seen: set[int] = set()
    for page in pages:
        entries = page if key is None else _as_object(page).get(key)
        for entry in _as_list(entries):
            item = _as_object(entry)
            ident = _int(item, "id")
            if ident is not None:
                if ident in seen:
                    continue
                seen.add(ident)
            items.append(item)
    return items


@dataclass(frozen=True)
class Remote:
    host: str
    path: str


def parse_remote_url(url: str) -> Remote:
    text = url.strip()
    if "://" in text:
        try:
            parts = urlsplit(text)
            hostname = parts.hostname
            port = parts.port
        except ValueError as err:
            msg = "the remote URL has a malformed host or port"
            raise DataError(msg) from err
        if parts.scheme not in URL_SCHEMES or not hostname:
            msg = f"unsupported remote URL scheme {parts.scheme!r}"
            raise DataError(msg)
        host = hostname
        # An ssh port says nothing about the API host, so only an http(s) port is kept.
        if parts.scheme in DEFAULT_PORTS and port not in {None, DEFAULT_PORTS[parts.scheme]}:
            host = f"{host}:{port}"
        path = parts.path
    else:
        match = SCP_LIKE_URL.match(text)
        if match is None:
            msg = "the remote URL is neither scp-like, ssh:// nor https://"
            raise DataError(msg)
        host = match["host"].lower()
        path = match["path"]
    path = path.strip("/").removesuffix(".git").strip("/")
    if not path:
        msg = "the remote URL has no project path"
        raise DataError(msg)
    return Remote(host=host, path=path)


def read_remote(name: str, runner: Runner) -> Remote:
    if not REMOTE_NAME.match(name):
        msg = f"invalid remote name {name!r}"
        raise CiTimingsError(msg, EXIT_USAGE)
    args = ["git", "remote", "get-url", name]
    result = runner(args, GIT_TIMEOUT_S)
    if result.returncode != 0:
        msg = (
            f"cannot read remote {name!r}; pass --host and --repo\n{describe_failure(args, result)}"
        )
        raise CiTimingsError(msg, EXIT_USAGE)
    try:
        return parse_remote_url(result.stdout)
    except DataError as err:
        msg = f"cannot parse the URL of remote {name!r}: {err}; pass --host and --repo"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def current_branch(runner: Runner) -> str:
    args = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    result = runner(args, GIT_TIMEOUT_S)
    branch = result.stdout.strip()
    if result.returncode != 0 or not branch or branch == "HEAD":
        msg = "cannot tell the current branch; pass --branch"
        raise CiTimingsError(msg, EXIT_USAGE)
    return branch


@dataclass(frozen=True)
class Target:
    provider: str
    host: str
    repo: str

    @property
    def tool(self) -> str:
        return TOOLS[self.provider]

    @property
    def project_api(self) -> str:
        if self.provider == GITHUB:
            return f"repos/{self.repo}"
        return f"projects/{quote(self.repo, safe='')}"


REPO_FORMS: Final[dict[str | None, str]] = {
    GITHUB: "OWNER/REPO",
    GITLAB: "GROUP[/SUBGROUP...]/PROJECT",
    None: "OWNER/REPO or GROUP[/SUBGROUP...]/PROJECT",
}


def validate_repo(provider: str | None, repo: str) -> None:
    segments = repo.split("/")
    shaped = len(segments) == 2 if provider == GITHUB else len(segments) >= 2
    valid = all(PATH_SEGMENT.match(segment) and segment not in {".", ".."} for segment in segments)
    if not shaped or not valid:
        msg = f"repository {repo!r} is not of the form {REPO_FORMS[provider]}; pass --repo"
        raise CiTimingsError(msg, EXIT_USAGE)


def locate(args: argparse.Namespace, runner: Runner) -> tuple[str, str]:
    host: str | None = args.host.lower() if args.host else None
    repo: str | None = args.repo
    if host is not None and repo is not None:
        return host, repo
    try:
        remote = read_remote(args.remote, runner)
    except CiTimingsError:
        if repo is None or args.provider == "auto":
            raise
        return host or DEFAULT_HOSTS[args.provider], repo
    return host or remote.host, repo or remote.path


def gh_known_hosts(runner: Runner) -> set[str]:
    # Lists hosts only: with --json gh exits 0 whatever the authentication state.
    result = runner(["gh", "auth", "status", "--json", "hosts"], AUTH_TIMEOUT_S)
    if result.returncode != 0:
        return set()
    try:
        values = decode_json_stream(result.stdout)
        hosts = _as_object(values[0]).get("hosts") if values else None
    except DataError:
        return set()
    if isinstance(hosts, dict):
        return {str(name).lower() for name in cast("dict[object, object]", hosts)}
    return set()


def glab_status_ok(host: str, runner: Runner) -> bool:
    return runner(["glab", "auth", "status", "--hostname", host], AUTH_TIMEOUT_S).returncode == 0


def detect_provider(host: str, runner: Runner, which: Which) -> str:
    if host == DEFAULT_HOSTS[GITHUB]:
        return GITHUB
    if host == DEFAULT_HOSTS[GITLAB]:
        return GITLAB
    github = which("gh") is not None and host in gh_known_hosts(runner)
    gitlab = which("glab") is not None and glab_status_ok(host, runner)
    if github and gitlab:
        msg = f"both gh and glab know {host}; pass --provider github|gitlab"
        raise CiTimingsError(msg, EXIT_USAGE)
    if github:
        return GITHUB
    if gitlab:
        return GITLAB
    msg = f"cannot tell whether {host} is GitHub or GitLab; pass --provider github|gitlab"
    raise CiTimingsError(msg, EXIT_USAGE)


def check_auth(provider: str, host: str, runner: Runner) -> None:
    tool = TOOLS[provider]
    login = f"{tool} is not authenticated for {host}; run: {tool} auth login --hostname {host}"
    probes = [[tool, "auth", "status", "--hostname", host]]
    if provider == GITLAB:
        # glab does not document the exit code of auth status, so a real call confirms it.
        probes.append(["glab", "api", "--hostname", host, "--method", "GET", "user"])
    for args in probes:
        result = runner(args, AUTH_TIMEOUT_S)
        if result.returncode != 0:
            msg = f"{login}\n{describe_failure(args, result)}"
            raise CiTimingsError(msg, EXIT_AUTH)


def resolve_target(args: argparse.Namespace, runner: Runner, which: Which) -> Target:
    host, repo = locate(args, runner)
    provider: str = args.provider
    if provider == "auto":
        validate_repo(None, repo)
        provider = detect_provider(host, runner, which)
    validate_repo(provider, repo)
    tool = TOOLS[provider]
    if which(tool) is None:
        msg = f"{tool} not found on PATH; install {CLI_NAMES[provider]} or pass --provider"
        raise CiTimingsError(msg, EXIT_USAGE)
    check_auth(provider, host, runner)
    return Target(provider=provider, host=host, repo=repo)


@dataclass(frozen=True)
class Api:
    target: Target
    runner: Runner

    def get_text(self, path: str, *, paginate: bool = False, timeout: float = API_TIMEOUT_S) -> str:
        args = [self.target.tool, "api", "--hostname", self.target.host, "--method", "GET"]
        if paginate:
            args.append("--paginate")
        args.append(path)
        result = self.runner(args, timeout)
        if result.returncode != 0:
            raise CiTimingsError(describe_failure(args, result), EXIT_API)
        return result.stdout

    def get_object(self, path: str) -> JsonObject:
        try:
            return _single_object(decode_json_stream(self.get_text(path)))
        except DataError as err:
            msg = f"unexpected response from {self.target.tool} api {path}: {err}"
            raise CiTimingsError(msg, EXIT_API) from err

    def get_all(self, path: str, key: str | None) -> list[JsonObject]:
        try:
            return merge_pages(decode_json_stream(self.get_text(path, paginate=True)), key)
        except DataError as err:
            msg = f"unexpected response from {self.target.tool} api {path}: {err}"
            raise CiTimingsError(msg, EXIT_API) from err


@dataclass(frozen=True)
class Section:
    name: str
    start: int
    end: int | None
    depth: int


def parse_sections(log: str) -> list[Section]:
    sections: list[Section] = []
    opened: list[tuple[str, int]] = []
    for match in SECTION_MARKER.finditer(log):
        kind, stamp, name = match.groups()
        if kind == "start":
            sections.append(Section(name=name, start=int(stamp), end=None, depth=len(opened)))
            opened.append((name, len(sections) - 1))
            continue
        for position in range(len(opened) - 1, -1, -1):
            if opened[position][0] == name:
                index = opened.pop(position)[1]
                sections[index] = replace(sections[index], end=int(stamp))
                break
    return sections


@dataclass(frozen=True)
class Unit:
    number: int
    name: str
    status: str
    conclusion: str
    start: float | None
    end: float | None
    depth: int = 0

    @property
    def duration(self) -> float | None:
        return _span(self.start, self.end)


@dataclass(frozen=True)
class Job:
    job_id: int
    name: str
    stage: str
    attempt: int
    status: str
    conclusion: str
    queued_s: float | None
    start: float | None
    end: float | None
    units: tuple[Unit, ...]

    @property
    def duration(self) -> float | None:
        return _span(self.start, self.end)

    @property
    def executed(self) -> bool:
        return self.duration is not None and self.conclusion != "skipped"

    @property
    def runner_seconds(self) -> float:
        duration = self.duration
        return duration if duration is not None and self.executed else 0.0

    @property
    def outcome(self) -> str:
        return self.conclusion or self.status or "unknown"


@dataclass(frozen=True)
class Run:
    provider: str
    run_id: int
    sha: str
    conclusion: str
    latest_attempt: int
    references: dict[int, float]
    jobs: tuple[Job, ...]

    def offset(self, job: Job, moment: float | None) -> float | None:
        reference = self.references.get(job.attempt)
        return None if reference is None or moment is None else moment - reference


def _github_step(raw: JsonObject) -> Unit:
    return Unit(
        number=_int(raw, "number") or 0,
        name=_text(raw, "name"),
        status=_text(raw, "status"),
        conclusion=_text(raw, "conclusion"),
        start=_timestamp(raw, "started_at"),
        end=_timestamp(raw, "completed_at"),
    )


def _github_job(raw: JsonObject) -> Job:
    created = _timestamp(raw, "created_at")
    start = _timestamp(raw, "started_at")
    steps = raw.get("steps")
    return Job(
        job_id=_required_int(raw, "id"),
        name=_text(raw, "name"),
        stage="",
        attempt=_int(raw, "run_attempt") or 1,
        status=_text(raw, "status"),
        conclusion=_text(raw, "conclusion"),
        queued_s=_span(created, start),
        start=start,
        end=_timestamp(raw, "completed_at"),
        units=tuple(_github_step(_as_object(step)) for step in _as_list(steps or [])),
    )


def _section_units(raw: object) -> tuple[Unit, ...]:
    units: list[Unit] = []
    for number, entry in enumerate(_as_list(raw), start=1):
        section = _as_object(entry)
        end = _number(section, "end")
        units.append(
            Unit(
                number=number,
                name=_text(section, "name"),
                status="open" if end is None else "completed",
                conclusion="",
                start=_number(section, "start"),
                end=end,
                depth=_int(section, "depth") or 0,
            )
        )
    return tuple(units)


def _gitlab_jobs(raw_jobs: list[JsonObject], sections: JsonObject | None) -> tuple[Job, ...]:
    attempts: dict[int, int] = {}
    seen: dict[str, int] = {}
    for raw in sorted(raw_jobs, key=lambda item: _int(item, "id") or 0):
        name = _text(raw, "name")
        seen[name] = seen.get(name, 0) + 1
        attempts[_required_int(raw, "id")] = seen[name]
    jobs: list[Job] = []
    for raw in raw_jobs:
        job_id = _required_int(raw, "id")
        status = _text(raw, "status")
        job_sections = sections.get(str(job_id)) if sections is not None else None
        jobs.append(
            Job(
                job_id=job_id,
                name=_text(raw, "name"),
                stage=_text(raw, "stage"),
                attempt=attempts[job_id],
                status=status,
                conclusion=status if status in GITLAB_TERMINAL else "",
                queued_s=_number(raw, "queued_duration"),
                start=_timestamp(raw, "started_at"),
                end=_timestamp(raw, "finished_at"),
                units=_section_units(job_sections) if job_sections is not None else (),
            )
        )
    return tuple(jobs)


def _earliest(*moments: float | None) -> float | None:
    known = [moment for moment in moments if moment is not None]
    return min(known) if known else None


def _references(
    provider: str, declared: float | None, latest: int, jobs: tuple[Job, ...]
) -> dict[int, float]:
    attempts = {job.attempt for job in jobs} | {latest}
    if provider == GITLAB:
        # Retried GitLab jobs run inside the same pipeline, so one origin serves every attempt.
        origin = _earliest(declared, *(job.start for job in jobs))
        return {} if origin is None else dict.fromkeys(attempts, origin)
    references: dict[int, float] = {}
    for attempt in attempts:
        first = _earliest(*(job.start for job in jobs if job.attempt == attempt))
        # run_started_at belongs to the latest attempt only; GitHub resets it on a re-run.
        origin = _earliest(declared, first) if attempt == latest else first
        if origin is not None:
            references[attempt] = origin
    return references


def provider_of(run: JsonObject) -> str:
    if "project_id" in run:
        return GITLAB
    if "run_attempt" in run or "workflow_id" in run:
        return GITHUB
    msg = "the run file is neither a GitHub workflow run nor a GitLab pipeline"
    raise DataError(msg)


def build_run(run: JsonObject, raw_jobs: object, sections: object | None) -> Run:
    provider = provider_of(run)
    if provider == GITHUB:
        pages = _as_list(raw_jobs) if isinstance(raw_jobs, list) else [raw_jobs]
        jobs = tuple(_github_job(raw) for raw in merge_pages(pages, "jobs"))
        declared = _timestamp(run, "run_started_at") or _timestamp(run, "created_at")
        sha = _text(run, "head_sha")
        conclusion = _text(run, "conclusion") or _text(run, "status")
    else:
        section_map = _as_object(sections) if sections is not None else None
        jobs = _gitlab_jobs(merge_pages([raw_jobs], None), section_map)
        declared = _timestamp(run, "started_at") or _timestamp(run, "created_at")
        sha = _text(run, "sha")
        conclusion = _text(run, "status")
    latest = max((job.attempt for job in jobs), default=1)
    if provider == GITHUB:
        latest = _int(run, "run_attempt") or latest
    return Run(
        provider=provider,
        run_id=_required_int(run, "id"),
        sha=sha,
        conclusion=conclusion or "unknown",
        latest_attempt=latest,
        references=_references(provider, declared, latest, jobs),
        jobs=jobs,
    )


def billed_minutes(provider: str, job: Job, cost_factor: float) -> float | None:
    if not job.executed:
        return None
    if provider == GITHUB:
        return float(math.ceil(job.runner_seconds / 60))
    return job.runner_seconds / 60 * cost_factor


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    rounded = round(value, digits)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")


def _cell(text: str) -> str:
    return " ".join(text.split())


def timing_rows(run: Run) -> list[list[str]]:
    rows: list[list[str]] = []
    for job in run.jobs:
        ident = [
            run.provider,
            str(run.run_id),
            str(job.attempt),
            str(job.job_id),
            _cell(job.name),
            _cell(job.stage),
        ]
        offset = run.offset(job, job.start)
        billed = billed_minutes(run.provider, job, 1.0)
        rows.append(
            [
                *ident,
                job.status,
                job.conclusion,
                _fmt(job.queued_s),
                _fmt(offset),
                _fmt(job.duration),
                _fmt(billed, 4),
                "",
                "",
                "",
            ]
        )
        rows.extend(
            [
                *ident,
                unit.status,
                unit.conclusion,
                "",
                "",
                "",
                "",
                str(unit.number),
                _cell(unit.name),
                _fmt(unit.duration),
            ]
            for unit in job.units
        )
    return rows


def render_tsv(columns: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    lines = ["\t".join(columns), *("\t".join(row) for row in rows)]
    return "\n".join(lines) + "\n"


def wall_clock(run: Run) -> float | None:
    latest = [job for job in run.jobs if job.attempt == run.latest_attempt]
    measured = latest if run.provider == GITHUB else list(run.jobs)
    ends = [run.offset(job, job.end) for job in measured if job.executed]
    known = [end for end in ends if end is not None]
    return max(known) if known else None


def runner_seconds(run: Run) -> float:
    return sum(job.runner_seconds for job in run.jobs)


def run_billed(run: Run, cost_factor: float) -> float:
    return sum(billed_minutes(run.provider, job, cost_factor) or 0.0 for job in run.jobs)


@dataclass(frozen=True)
class Phases:
    setup: float
    work: float
    after: float


def _is_prelude(provider: str, name: str) -> bool:
    if provider == GITHUB:
        return GITHUB_PRELUDE.match(name) is not None
    return name in GITLAB_PRELUDE


def _is_postlude(provider: str, name: str) -> bool:
    if provider == GITHUB:
        return GITHUB_POSTLUDE.match(name) is not None
    return name in GITLAB_POSTLUDE


def job_phases(provider: str, job: Job) -> Phases | None:
    if not job.executed or job.start is None or job.end is None:
        return None
    timed = sorted(
        (unit.start, unit.end, unit.number, unit.name)
        for unit in job.units
        if unit.depth == 0 and unit.start is not None and unit.end is not None
    )
    if not timed:
        return None
    first = 0
    while first < len(timed) and _is_prelude(provider, timed[first][3]):
        first += 1
    last = len(timed)
    while last > first and _is_postlude(provider, timed[last - 1][3]):
        last -= 1
    work = timed[first:last]
    if not work:
        boundary = max(unit[1] for unit in timed[:first]) if first else job.start
        return Phases(setup=boundary - job.start, work=0.0, after=job.end - boundary)
    work_start = work[0][0]
    work_end = max(unit[1] for unit in work)
    return Phases(
        setup=work_start - job.start,
        work=work_end - work_start,
        after=job.end - work_end,
    )


def _whole(value: float | None) -> str:
    return "-" if value is None else str(round(value))


def _job_label(job: Job) -> str:
    return job.name if job.attempt <= 1 else f"{job.name} (attempt {job.attempt})"


def _timeline(run: Run) -> list[str]:
    started: list[tuple[int, float, str, float | None, Job]] = []
    waiting: list[Job] = []
    for job in run.jobs:
        offset = run.offset(job, job.start)
        if offset is None:
            waiting.append(job)
            continue
        # GitHub attempts each have their own origin; GitLab retries share the pipeline's.
        attempt = job.attempt if run.provider == GITHUB else 0
        started.append((attempt, offset, job.name, run.offset(job, job.end), job))
    lines: list[str] = []
    for _, offset, _, end, job in sorted(started, key=lambda item: item[:3]):
        lines.append(
            f"  start {_seconds_cell(offset)}  end {_seconds_cell(end)}"
            f"  dur {_seconds_cell(job.duration)}  {job.outcome}  {_job_label(job)}"
        )
    lines.extend(
        f"  start {_seconds_cell(None)}  end {_seconds_cell(None)}"
        f"  dur {_seconds_cell(None)}  {job.outcome}  {_job_label(job)}"
        for job in waiting
    )
    return lines


def _seconds_cell(value: float | None) -> str:
    return f"{'-':>6} " if value is None else f"{_whole(value):>6}s"


def _billed_line(run: Run, cost_factor: float) -> str:
    billed = run_billed(run, cost_factor)
    if run.provider == GITHUB:
        return f"  billed estimate {billed:.0f} min (each job rounded up to a whole minute)"
    return (
        f"  billed estimate {billed:.2f} compute min"
        f" (duration / 60 x cost factor {cost_factor:g}, not rounded)"
    )


def _slow_units(run: Run, min_unit_s: float) -> list[str]:
    label = "steps" if run.provider == GITHUB else "sections"
    if run.provider == GITLAB and not any(job.units for job in run.jobs):
        return ["  sections: none recorded (fetch --sections reads them from the job logs)"]
    lines = [f"  {label} >= {min_unit_s:g}s:"]
    for job in run.jobs:
        for unit in job.units:
            duration = unit.duration
            if unit.end is None:
                unfinished = unit.start is not None or unit.status != "completed"
                shown = "open" if unfinished else "-"
                lines.append(f"  {shown:>9}  {_job_label(job)} :: {unit.name}")
            elif duration is not None and duration >= min_unit_s:
                lines.append(f"  {_whole(duration):>8}s  {_job_label(job)} :: {unit.name}")
    return lines


def render_report(run: Run, *, min_unit_s: float, cost_factor: float) -> list[str]:
    exact = runner_seconds(run)
    return [
        f"== run {run.run_id} {run.sha[:7]} {run.conclusion} wall {_whole(wall_clock(run))}s",
        *_timeline(run),
        f"  runner time total {exact:.0f}s ({exact / 60:.1f} min)",
        _billed_line(run, cost_factor),
        *_slow_units(run, min_unit_s),
    ]


@dataclass(frozen=True)
class Totals:
    wall: float | None
    exact_s: float
    billed_min: float
    executed: int
    phases: Phases
    phase_jobs: int


def run_totals(run: Run) -> Totals:
    executed = [job for job in run.jobs if job.executed]
    phases = [phases for job in executed if (phases := job_phases(run.provider, job)) is not None]
    return Totals(
        wall=wall_clock(run),
        exact_s=runner_seconds(run),
        billed_min=run_billed(run, 1.0),
        executed=len(executed),
        phases=Phases(
            setup=sum(item.setup for item in phases),
            work=sum(item.work for item in phases),
            after=sum(item.after for item in phases),
        ),
        phase_jobs=len(phases),
    )


def _change(base: float | None, new: float | None, *, digits: int, unit: str) -> str:
    def show(value: float | None) -> str:
        return "-" if value is None else f"{value:.{digits}f}{unit}"

    if base is None or new is None:
        return f"{show(base)} -> {show(new)}"
    diff = new - base
    percent = f" ({diff / base * 100:+.1f}%)" if base else ""
    return f"{show(base)} -> {show(new)}, {diff:+.{digits}f}{unit}{percent}"


def _latest_by_name(run: Run) -> dict[str, Job]:
    latest: dict[str, Job] = {}
    for job in run.jobs:
        current = latest.get(job.name)
        if current is None or job.attempt >= current.attempt:
            latest[job.name] = job
    return latest


def _per_job(base: Run, new: Run) -> list[str]:
    base_jobs = _latest_by_name(base)
    new_jobs = _latest_by_name(new)
    names = [*base_jobs, *(name for name in new_jobs if name not in base_jobs)]
    lines = [
        "  per job (duration of the latest attempt):",
        f"  {'base':>8}  {'new':>8}  {'delta':>8}  name",
    ]
    for name in names:
        before = base_jobs.get(name)
        after = new_jobs.get(name)
        old_s = before.duration if before is not None and before.executed else None
        new_s = after.duration if after is not None and after.executed else None
        delta = None if old_s is None or new_s is None else new_s - old_s
        shown = "-" if delta is None else f"{delta:+.0f}"
        lines.append(f"  {_whole(old_s):>8}  {_whole(new_s):>8}  {shown:>8}  {name}")
    return lines


def render_difference(base: Run, new: Run) -> list[str]:
    old = run_totals(base)
    cur = run_totals(new)
    billed_digits = 0 if base.provider == GITHUB and new.provider == GITHUB else 2
    rows = [
        ("wall clock", _change(old.wall, cur.wall, digits=0, unit="s")),
        ("runner time, exact", _change(old.exact_s / 60, cur.exact_s / 60, digits=1, unit=" min")),
        (
            "billed estimate",
            _change(old.billed_min, cur.billed_min, digits=billed_digits, unit=" min"),
        ),
        (
            "rounding slack (billed minus exact)",
            _change(
                old.billed_min - old.exact_s / 60,
                cur.billed_min - cur.exact_s / 60,
                digits=1,
                unit=" min",
            ),
        ),
        ("jobs executed", f"{old.executed} -> {cur.executed}"),
        (
            "jobs split into phases",
            f"{old.phase_jobs} of {old.executed} -> {cur.phase_jobs} of {cur.executed}",
        ),
        ("set-up before the work", _change(old.phases.setup, cur.phases.setup, digits=0, unit="s")),
        ("the work", _change(old.phases.work, cur.phases.work, digits=0, unit="s")),
        ("after the work", _change(old.phases.after, cur.phases.after, digits=0, unit="s")),
    ]
    return [
        f"== difference {base.run_id} -> {new.run_id}",
        *(f"  {label + ':':<38}{value}" for label, value in rows),
        *_per_job(base, new),
    ]


def read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        msg = f"missing file {path}; run fetch first"
        raise CiTimingsError(msg, EXIT_USAGE) from err
    except OSError as err:
        msg = f"cannot read {path}: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        msg = f"{path} is not valid JSON: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def load_run(directory: Path, run_id: int) -> Run:
    run_path = directory / f"run-{run_id}.json"
    sections_path = directory / f"sections-{run_id}.json"
    run = read_json(run_path)
    jobs = read_json(directory / f"jobs-{run_id}.json")
    sections = read_json(sections_path) if sections_path.exists() else None
    try:
        return build_run(_as_object(run), jobs, sections)
    except DataError as err:
        msg = f"cannot read run {run_id} from {directory}: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def write_text(path: Path, text: str) -> None:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as err:
        msg = f"cannot write {path}: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2) + "\n")


def ensure_directory(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        msg = f"cannot create {path}: {err}"
        raise CiTimingsError(msg, EXIT_USAGE) from err


def github_history(api: Api, branch: str, limit: int) -> list[JsonObject]:
    per_page = min(limit, PAGE_SIZE)
    runs: list[JsonObject] = []
    page = 1
    while len(runs) < limit:
        path = (
            f"{api.target.project_api}/actions/runs?branch={quote(branch, safe='')}"
            f"&status=completed&per_page={per_page}&page={page}"
        )
        try:
            entries = _as_list(api.get_object(path).get("workflow_runs"))
            runs.extend(_as_object(entry) for entry in entries)
        except DataError as err:
            msg = f"unexpected response from gh api {path}: {err}"
            raise CiTimingsError(msg, EXIT_API) from err
        if len(entries) < per_page:
            break
        page += 1
    return runs[:limit]


def gitlab_history(api: Api, branch: str, limit: int) -> list[JsonObject]:
    per_page = min(limit, PAGE_SIZE)
    listed: list[JsonObject] = []
    page = 1
    while len(listed) < limit:
        path = (
            f"{api.target.project_api}/pipelines?ref={quote(branch, safe='')}"
            f"&status=success&order_by=id&sort=desc&per_page={per_page}&page={page}"
        )
        entries = _gitlab_page(api, path)
        listed.extend(entries)
        if len(entries) < per_page:
            break
        page += 1
    try:
        ids = [_required_int(item, "id") for item in listed[:limit]]
    except DataError as err:
        msg = f"unexpected pipeline record from glab api: {err}"
        raise CiTimingsError(msg, EXIT_API) from err
    # The list endpoint omits started_at and finished_at, which the wall clock needs.
    return [api.get_object(f"{api.target.project_api}/pipelines/{ident}") for ident in ids]


def _gitlab_page(api: Api, path: str) -> list[JsonObject]:
    try:
        values = decode_json_stream(api.get_text(path))
        return merge_pages(values, None)
    except DataError as err:
        msg = f"unexpected response from glab api {path}: {err}"
        raise CiTimingsError(msg, EXIT_API) from err


def history_row(provider: str, run: JsonObject) -> list[str]:
    if provider == GITHUB:
        wall = _span(_timestamp(run, "run_started_at"), _timestamp(run, "updated_at"))
        attempt = str(_int(run, "run_attempt") or "")
        branch = _text(run, "head_branch")
        sha = _text(run, "head_sha")
        status = _text(run, "status")
        conclusion = _text(run, "conclusion")
    else:
        wall = _span(_timestamp(run, "started_at"), _timestamp(run, "finished_at"))
        attempt = ""
        branch = _text(run, "ref")
        sha = _text(run, "sha")
        status = _text(run, "status")
        conclusion = status if status in GITLAB_TERMINAL else ""
    return [
        provider,
        str(_int(run, "id") or ""),
        attempt,
        _cell(branch),
        sha,
        status,
        conclusion,
        _text(run, "created_at"),
        _fmt(wall),
    ]


def cmd_history(args: argparse.Namespace, runner: Runner, which: Which) -> int:
    target = resolve_target(args, runner, which)
    branch: str = args.branch or current_branch(runner)
    api = Api(target=target, runner=runner)
    history = (
        github_history(api, branch, args.limit)
        if target.provider == GITHUB
        else gitlab_history(api, branch, args.limit)
    )
    if args.out is not None:
        out: Path = args.out
        ensure_directory(out)
        write_json(out / f"history-{re.sub(r'[^A-Za-z0-9._-]', '_', branch)}.json", history)
    try:
        rows = [history_row(target.provider, run) for run in history]
    except DataError as err:
        msg = f"unexpected run record: {err}"
        raise CiTimingsError(msg, EXIT_API) from err
    sys.stdout.write(render_tsv(HISTORY_COLUMNS, rows))
    return EXIT_OK


def _job_sections(api: Api, jobs: list[JsonObject]) -> JsonObject:
    sections: JsonObject = {}
    for job in jobs:
        if _timestamp(job, "started_at") is None:
            continue
        job_id = _required_int(job, "id")
        log = api.get_text(f"{api.target.project_api}/jobs/{job_id}/trace", timeout=LOG_TIMEOUT_S)
        sections[str(job_id)] = [asdict(section) for section in parse_sections(log)]
    return sections


def fetch_run(api: Api, run_id: int, out: Path, *, sections: bool) -> Run:
    project = api.target.project_api
    if api.target.provider == GITHUB:
        run = api.get_object(f"{project}/actions/runs/{run_id}")
        jobs = api.get_all(
            f"{project}/actions/runs/{run_id}/jobs?filter=all&per_page={PAGE_SIZE}", "jobs"
        )
        raw_jobs: object = {"total_count": len(jobs), "jobs": jobs}
        job_sections: JsonObject | None = None
    else:
        run = api.get_object(f"{project}/pipelines/{run_id}")
        jobs = api.get_all(
            f"{project}/pipelines/{run_id}/jobs?include_retried=true&per_page={PAGE_SIZE}", None
        )
        raw_jobs = jobs
        try:
            job_sections = _job_sections(api, jobs) if sections else None
        except DataError as err:
            msg = f"unexpected job record in pipeline {run_id}: {err}"
            raise CiTimingsError(msg, EXIT_API) from err
    try:
        normalised = build_run(run, raw_jobs, job_sections)
    except DataError as err:
        msg = f"unexpected response for run {run_id}: {err}"
        raise CiTimingsError(msg, EXIT_API) from err
    write_json(out / f"run-{run_id}.json", run)
    write_json(out / f"jobs-{run_id}.json", raw_jobs)
    if job_sections is not None:
        write_json(out / f"sections-{run_id}.json", job_sections)
    write_text(out / f"timings-{run_id}.tsv", render_tsv(TIMING_COLUMNS, timing_rows(normalised)))
    return normalised


def cmd_fetch(args: argparse.Namespace, runner: Runner, which: Which) -> int:
    target = resolve_target(args, runner, which)
    if args.sections and target.provider == GITHUB:
        msg = "--sections applies to GitLab only; GitHub jobs carry their own step timings"
        raise CiTimingsError(msg, EXIT_USAGE)
    out: Path = args.out
    ensure_directory(out)
    api = Api(target=target, runner=runner)
    failed = 0
    for run_id in args.run_ids:
        try:
            run = fetch_run(api, run_id, out, sections=args.sections)
        except CiTimingsError as err:
            if err.exit_code != EXIT_API:
                raise
            print(f"{PROG}: error: run {run_id}: {err}", file=sys.stderr)
            failed += 1
            continue
        print(f"run {run_id}: {len(run.jobs)} jobs stored in {out}")
    return EXIT_API if failed else EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    run = load_run(args.dir, args.run_id)
    cost_factor: float | None = args.cost_factor
    if cost_factor is not None and run.provider != GITLAB:
        msg = "--cost-factor applies to GitLab compute minutes only"
        raise CiTimingsError(msg, EXIT_USAGE)
    lines = render_report(
        run,
        min_unit_s=args.min_step_seconds,
        cost_factor=1.0 if cost_factor is None else cost_factor,
    )
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def cmd_compare(args: argparse.Namespace) -> int:
    base = load_run(args.dir, args.base_run_id)
    new = load_run(args.dir, args.new_run_id)
    lines = [
        *render_report(base, min_unit_s=args.min_step_seconds, cost_factor=1.0),
        *render_report(new, min_unit_s=args.min_step_seconds, cost_factor=1.0),
        *render_difference(base, new),
    ]
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_id(text: str) -> int:
    if not text.isdigit() or int(text) == 0:
        msg = f"not a run or pipeline ID: {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return int(text)


def _positive_int(text: str) -> int:
    if not text.isdigit() or int(text) == 0:
        msg = f"not a positive integer: {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return int(text)


def _float_at_least(text: str, minimum: float, *, inclusive: bool) -> float:
    try:
        value = float(text)
    except ValueError as err:
        msg = f"not a number: {text!r}"
        raise argparse.ArgumentTypeError(msg) from err
    if not math.isfinite(value) or value < minimum or (value == minimum and not inclusive):
        relation = "at least" if inclusive else "greater than"
        msg = f"must be {relation} {minimum:g}: {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return value


def _non_negative_float(text: str) -> float:
    return _float_at_least(text, 0.0, inclusive=True)


def _positive_float(text: str) -> float:
    return _float_at_least(text, 0.0, inclusive=False)


def _add_target_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=("auto", GITHUB, GITLAB), default="auto")
    parser.add_argument("--repo", help="OWNER/REPO on GitHub, the project path on GitLab")
    parser.add_argument("--host", help="API host; overrides the host of the remote")
    parser.add_argument("--remote", default="origin", help="git remote to read (default: origin)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ci_run_timings.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    history = commands.add_parser("history", help="list recorded runs of one branch")
    _add_target_options(history)
    history.add_argument("--branch", help="branch to list (default: the checked-out branch)")
    history.add_argument("--limit", type=_positive_int, default=DEFAULT_HISTORY_LIMIT)
    history.add_argument("--out", type=Path, help="also store the raw run records here")

    fetch = commands.add_parser("fetch", help="store runs and their jobs as JSON and TSV")
    _add_target_options(fetch)
    fetch.add_argument("--sections", action="store_true", help="GitLab: parse job log sections")
    fetch.add_argument("--out", type=Path, required=True)
    fetch.add_argument("run_ids", nargs="+", type=_run_id, metavar="RUN_ID")

    report = commands.add_parser("report", help="print one stored run")
    report.add_argument("dir", type=Path, metavar="DIR")
    report.add_argument("run_id", type=_run_id, metavar="RUN_ID")
    report.add_argument("--min-step-seconds", type=_non_negative_float, default=DEFAULT_MIN_STEP_S)
    report.add_argument("--cost-factor", type=_positive_float, help="GitLab runner cost factor")

    compare = commands.add_parser("compare", help="print two stored runs and their difference")
    compare.add_argument("dir", type=Path, metavar="DIR")
    compare.add_argument("base_run_id", type=_run_id, metavar="BASE_RUN_ID")
    compare.add_argument("new_run_id", type=_run_id, metavar="NEW_RUN_ID")
    compare.add_argument("--min-step-seconds", type=_non_negative_float, default=DEFAULT_MIN_STEP_S)
    return parser


def main(
    argv: Sequence[str] | None = None,
    runner: Runner = run_command,
    which: Which = shutil.which,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "history":
            return cmd_history(args, runner, which)
        if args.command == "fetch":
            return cmd_fetch(args, runner, which)
        if args.command == "report":
            return cmd_report(args)
        return cmd_compare(args)
    except CiTimingsError as err:
        print(f"{PROG}: error: {err}", file=sys.stderr)
        return err.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
