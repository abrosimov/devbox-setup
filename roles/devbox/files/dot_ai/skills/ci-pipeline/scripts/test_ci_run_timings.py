"""Every instant is a fixture literal or an offset from one anchor; the script reads no clock."""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import parse_qs, urlsplit

import ci_run_timings as crt
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

HERE = Path(__file__).parent
SCRIPT = HERE / "ci_run_timings.py"
GITHUB_DATA = HERE / "testdata" / "github"
GITLAB_DATA = HERE / "testdata" / "gitlab"

GITHUB_REMOTE = "git@github.com:octo/widgets.git"
GITLAB_REMOTE = "git@gitlab.com:group/sub/proj.git"
GITHUB_PROJECT = "repos/octo/widgets"
GITLAB_PROJECT = "projects/group%2Fsub%2Fproj"

TIMING_COLUMNS = [
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
]
HISTORY_COLUMNS = [
    "provider",
    "run_id",
    "attempt",
    "branch",
    "sha",
    "status",
    "conclusion",
    "created_at",
    "wall_s",
]
PHASE_LABELS = ("set-up before the work", "the work", "after the work")

ANCHOR = datetime(2026, 2, 1, tzinfo=UTC)

type Which = Callable[[str], str | None]


def at(seconds: float) -> str:
    return (ANCHOR + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def both(name: str) -> str:
    return f"/usr/bin/{name}"


def only(*names: str) -> Which:
    return lambda name: both(name) if name in names else None


def missing(_name: str) -> None:
    return None


class Result(NamedTuple):
    code: int
    out: str
    err: str


class FakeCli:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.timeouts: list[float] = []
        self._rules: list[tuple[tuple[str, ...], str | None, subprocess.CompletedProcess[str]]] = []

    def on(
        self,
        *prefix: str,
        path: str | None = None,
        stdout: str = "",
        stderr: str = "",
        code: int = 0,
        override: bool = False,
    ) -> None:
        reply = subprocess.CompletedProcess(list(prefix), code, stdout, stderr)
        rule = (prefix, path, reply)
        if override:
            self._rules.insert(0, rule)
        else:
            self._rules.append(rule)

    def __call__(self, args: Sequence[str], timeout: float) -> subprocess.CompletedProcess[str]:
        call = tuple(args)
        self.calls.append(call)
        self.timeouts.append(timeout)
        for prefix, path, reply in self._rules:
            if call[: len(prefix)] == prefix and (path is None or call[-1] == path):
                return reply
        msg = f"unexpected call: {call}"
        raise AssertionError(msg)

    def api_paths(self, tool: str | None = None) -> list[str]:
        return [
            call[-1]
            for call in self.calls
            if call[0] in {"gh", "glab"} and call[1] == "api" and tool in {None, call[0]}
        ]

    def tools_called(self) -> set[str]:
        return {call[0] for call in self.calls}


def assert_read_only(calls: Sequence[tuple[str, ...]]) -> None:
    for call in calls:
        tool, rest = call[0], call[1:]
        if tool == "git":
            assert rest[:2] == ("remote", "get-url") or rest[:1] == ("rev-parse",), call
        elif tool in {"gh", "glab"}:
            if rest[0] == "auth":
                assert rest[1] == "status", call
                continue
            assert rest[0] == "api", call
            assert rest.count("--method") == 1, call
            assert rest[rest.index("--method") + 1] == "GET", call
            forbidden = {"-X", "-f", "-F", "--field", "--raw-field", "--input", "-d", "--data"}
            assert not forbidden & set(rest), call
        else:
            msg = f"unexpected tool in {call}"
            raise AssertionError(msg)


@pytest.fixture
def cli() -> Iterator[FakeCli]:
    fake = FakeCli()
    yield fake
    assert_read_only(fake.calls)


@pytest.fixture
def invoke(capsys: pytest.CaptureFixture[str], cli: FakeCli) -> Callable[..., Result]:
    def run(*argv: str, which: Which = both) -> Result:
        code = crt.main(list(argv), cli, which)
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)

    return run


def github_ready(cli: FakeCli, remote: str = GITHUB_REMOTE, host: str = "github.com") -> None:
    cli.on("git", "remote", "get-url", stdout=remote + "\n")
    cli.on("gh", "auth", "status", "--hostname", host)


def gitlab_ready(cli: FakeCli, remote: str = GITLAB_REMOTE, host: str = "gitlab.com") -> None:
    cli.on("git", "remote", "get-url", stdout=remote + "\n")
    cli.on("glab", "auth", "status", "--hostname", host)
    cli.on("glab", "api", "--hostname", host, "--method", "GET", "user", stdout='{"id": 1}')


def github_run_path(run_id: int) -> str:
    return f"{GITHUB_PROJECT}/actions/runs/{run_id}"


def github_jobs_path(run_id: int) -> str:
    return f"{github_run_path(run_id)}/jobs?filter=all&per_page=100"


def gitlab_jobs_path(pipeline_id: int) -> str:
    return f"{GITLAB_PROJECT}/pipelines/{pipeline_id}/jobs?include_retried=true&per_page=100"


def serve_github_run(cli: FakeCli, run_id: int) -> None:
    jobs = json.loads((GITHUB_DATA / f"jobs-{run_id}.json").read_text())["jobs"]
    cli.on(
        "gh",
        "api",
        path=github_jobs_path(run_id),
        stdout=json.dumps({"total_count": len(jobs), "jobs": jobs}),
    )
    cli.on(
        "gh",
        "api",
        path=github_run_path(run_id),
        stdout=(GITHUB_DATA / f"run-{run_id}.json").read_text(),
    )


def serve_gitlab_pipeline(cli: FakeCli, pipeline_id: int = 2001) -> None:
    cli.on(
        "glab",
        "api",
        path=gitlab_jobs_path(pipeline_id),
        stdout=(GITLAB_DATA / f"jobs-{pipeline_id}.json").read_text(),
    )
    cli.on(
        "glab",
        "api",
        path=f"{GITLAB_PROJECT}/pipelines/{pipeline_id}",
        stdout=(GITLAB_DATA / f"run-{pipeline_id}.json").read_text(),
    )
    for job_id in (301, 302, 303, 307):
        cli.on(
            "glab",
            "api",
            path=f"{GITLAB_PROJECT}/jobs/{job_id}/trace",
            stdout=(GITLAB_DATA / f"trace-{job_id}.log").read_text(),
        )


def read_rows(path: Path) -> list[list[str]]:
    return list(csv.reader(io.StringIO(path.read_text()), delimiter="\t", quoting=csv.QUOTE_NONE))


def read_records(path: Path) -> list[dict[str, str]]:
    header, *rows = read_rows(path)
    return [dict(zip(header, row, strict=True)) for row in rows]


def timing_row(cells: str) -> dict[str, str]:
    return dict(zip(TIMING_COLUMNS, cells.split("|"), strict=True))


def query(path: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlsplit(path).query).items()}


def value_of(out: str, label: str) -> str:
    match = re.search(rf"^\s+{re.escape(label)}:\s+(.*)$", out, re.MULTILINE)
    assert match is not None, f"no line for {label!r} in:\n{out}"
    return match.group(1)


def leading_seconds(value: str) -> int:
    match = re.match(r"(\d+)s ->", value)
    assert match is not None, value
    return int(match.group(1))


def phases_of(out: str) -> tuple[int, ...]:
    return tuple(leading_seconds(value_of(out, label)) for label in PHASE_LABELS)


def table_after(out: str, header: str) -> list[str]:
    lines = out.splitlines()
    return lines[lines.index(header) + 1 :]


PER_JOB_HEADER = "      base       new     delta  name"


def write_run(
    directory: Path, run: dict[str, object], jobs: object, sections: object = None
) -> int:
    run_id = run["id"]
    assert isinstance(run_id, int)
    (directory / f"run-{run_id}.json").write_text(json.dumps(run))
    (directory / f"jobs-{run_id}.json").write_text(json.dumps(jobs))
    if sections is not None:
        (directory / f"sections-{run_id}.json").write_text(json.dumps(sections))
    return run_id


def gh_run(run_id: int = 1, started: float = 0) -> dict[str, object]:
    return {
        "id": run_id,
        "workflow_id": 9,
        "run_attempt": 1,
        "head_sha": "0123456789abcdef",
        "status": "completed",
        "conclusion": "success",
        "created_at": at(started),
        "run_started_at": at(started),
    }


def gh_step(number: int, name: str, start: float, end: float | None) -> dict[str, object]:
    return {
        "name": name,
        "number": number,
        "status": "completed",
        "conclusion": "success",
        "started_at": at(start),
        "completed_at": None if end is None else at(end),
    }


def gh_skipped_step(number: int, name: str) -> dict[str, object]:
    return {
        "name": name,
        "number": number,
        "status": "completed",
        "conclusion": "skipped",
        "started_at": None,
        "completed_at": None,
    }


def gh_steps(rows: Sequence[tuple[str, int, int]]) -> list[dict[str, object]]:
    return [gh_step(number, name, s, e) for number, (name, s, e) in enumerate(rows, 1)]


def gh_job(
    job_id: int,
    name: str,
    start: float | None,
    end: float | None,
    *,
    attempt: int = 1,
    conclusion: str | None = "success",
    steps: Sequence[dict[str, object]] = (),
) -> dict[str, object]:
    return {
        "id": job_id,
        "run_attempt": attempt,
        "name": name,
        "status": "completed" if end is not None else "queued",
        "conclusion": conclusion,
        "created_at": at(0),
        "started_at": None if start is None else at(start),
        "completed_at": None if end is None else at(end),
        "steps": list(steps),
    }


def gh_jobs(*jobs: dict[str, object]) -> dict[str, object]:
    return {"total_count": len(jobs), "jobs": list(jobs)}


def gl_run(run_id: int = 1, started: float = 0) -> dict[str, object]:
    return {
        "id": run_id,
        "project_id": 7,
        "status": "success",
        "sha": "fedcba9876543210",
        "created_at": at(started),
        "started_at": at(started),
    }


def gl_job(
    job_id: int,
    name: str,
    start: float | None,
    end: float | None,
    *,
    status: str = "success",
) -> dict[str, object]:
    return {
        "id": job_id,
        "name": name,
        "stage": "test",
        "status": status,
        "started_at": None if start is None else at(start),
        "finished_at": None if end is None else at(end),
        "queued_duration": None,
    }


class TestRemoteUrlParsing:
    @pytest.mark.parametrize(
        ("url", "host", "path"),
        [
            ("git@github.com:octo/widgets.git", "github.com", "octo/widgets"),
            ("github.com:octo/widgets.git", "github.com", "octo/widgets"),
            ("git@GitLab.Example.com:group/sub/proj.git", "gitlab.example.com", "group/sub/proj"),
            ("ssh://git@gitlab.example.com/group/proj.git", "gitlab.example.com", "group/proj"),
            (
                "ssh://git@gitlab.example.com:2222/group/proj.git",
                "gitlab.example.com",
                "group/proj",
            ),
            ("git+ssh://git@gitlab.example.com:2222/g/p", "gitlab.example.com", "g/p"),
            ("https://github.com/octo/widgets", "github.com", "octo/widgets"),
            ("https://github.com/octo/widgets.git", "github.com", "octo/widgets"),
            ("https://github.com/octo/widgets/", "github.com", "octo/widgets"),
            ("HTTPS://GitHub.com/Octo/Widgets.git\n", "github.com", "Octo/Widgets"),
            ("https://gitlab.example.com:8443/g/p.git", "gitlab.example.com:8443", "g/p"),
            ("http://gitlab.example.com:8080/g/p", "gitlab.example.com:8080", "g/p"),
            ("https://gitlab.com:443/g/p", "gitlab.com", "g/p"),
            ("https://github.com:443/octo/widgets.git", "github.com", "octo/widgets"),
            ("http://h:80/g/p", "h", "g/p"),
            ("https://h:80/g/p", "h:80", "g/p"),
            ("http://h:443/g/p", "h:443", "g/p"),
            ("ssh://git@h:443/g/p", "h", "g/p"),
            ("ssh://git@h:80/g/p", "h", "g/p"),
            ("git://h:9418/g/p", "h", "g/p"),
            ("https://alice:hunter2@github.com/octo/widgets.git", "github.com", "octo/widgets"),
            ("https://oauth2:glpat-abc@gitlab.com/g/s/p.git", "gitlab.com", "g/s/p"),
            ("ssh://alice:hunter2@gitlab.example.com:2222/g/p.git", "gitlab.example.com", "g/p"),
        ],
    )
    def test_host_and_project_path_are_extracted(self, url: str, host: str, path: str) -> None:
        assert crt.parse_remote_url(url) == crt.Remote(host=host, path=path)

    @pytest.mark.parametrize(
        "url",
        [
            "/srv/git/widgets.git",
            "../widgets",
            "file:///srv/git/widgets.git",
            "ftp://example.com/o/r.git",
            "",
            "   ",
            "https://github.com/",
            "https://github.com",
            "ssh://git@github.com/",
            "git@github.com:.git",
            "https://github.com:notaport/o/r",
            "https://github.com:99999/o/r",
            "https://alice:hunter2@:443/o/r",
        ],
    )
    def test_unusable_remote_is_a_data_error(self, url: str) -> None:
        with pytest.raises(crt.DataError):
            crt.parse_remote_url(url)

    @pytest.mark.parametrize(
        "remote",
        [
            "https://alice:hunter2@gitlab.example.com/",
            "https://alice:hunter2@gitlab.example.com:notaport/g/p",
            "file:///srv/alice:hunter2/widgets.git",
            "/srv/alice:hunter2/widgets.git",
        ],
    )
    def test_credentials_in_a_rejected_remote_are_never_printed(
        self, cli: FakeCli, invoke: Callable[..., Result], remote: str
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=remote + "\n")

        result = invoke("history", "--branch", "main")

        assert result.code == 2
        assert "hunter2" not in result.out + result.err
        assert "--host and --repo" in result.err
        assert cli.api_paths() == []

    def test_credentials_in_the_remote_reach_neither_output_nor_any_command(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli, remote="https://alice:hunter2@github.com/octo/widgets.git")
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        assert "hunter2" not in result.out + result.err
        assert all("hunter2" not in part for call in cli.calls for part in call)
        assert cli.api_paths()[0].startswith(f"{GITHUB_PROJECT}/actions/runs?")

    def test_credentials_are_not_printed_when_authentication_fails(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout="https://alice:hunter2@github.com/o/r.git\n")
        cli.on("gh", "auth", "status", code=1, stderr="not logged in")

        result = invoke("history", "--branch", "main")

        assert result.code == 3
        assert "hunter2" not in result.out + result.err

    @pytest.mark.parametrize(
        ("remote", "host"),
        [
            ("https://gitlab.example.com:8443/g/p.git", "gitlab.example.com:8443"),
            ("ssh://git@gitlab.example.com:2222/g/p.git", "gitlab.example.com"),
        ],
        ids=["https port kept", "ssh port dropped"],
    )
    def test_api_host_keeps_an_https_port_and_drops_an_ssh_port(
        self, cli: FakeCli, invoke: Callable[..., Result], remote: str, host: str
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=remote + "\n")
        cli.on("gh", "auth", "status", "--json", "hosts", code=1)
        cli.on("glab", "auth", "status", "--hostname", host)
        cli.on("glab", "api", "--hostname", host, "--method", "GET", "user")
        cli.on("glab", "api", stdout="[]")

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        assert ("glab", "auth", "status", "--hostname", host) in cli.calls
        assert all(call[3] == host for call in cli.calls if call[:2] == ("glab", "api"))

    @pytest.mark.parametrize(
        ("remote", "tool", "host"),
        [
            ("https://gitlab.com:443/g/p", "glab", "gitlab.com"),
            ("https://github.com:443/o/r.git", "gh", "github.com"),
            ("ssh://git@github.com:443/o/r.git", "gh", "github.com"),
        ],
    )
    def test_default_port_in_the_remote_does_not_hide_a_public_host(
        self, cli: FakeCli, invoke: Callable[..., Result], remote: str, tool: str, host: str
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=remote + "\n")
        cli.on(tool, "auth", "status", "--hostname", host)
        cli.on(tool, "api", "--hostname", host, "--method", "GET", "user")
        cli.on(tool, "api", stdout='{"workflow_runs": []}' if tool == "gh" else "[]")

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        assert cli.tools_called() == {"git", tool}
        assert (tool, "auth", "status", "--hostname", host) in cli.calls

    def test_malformed_ipv6_remote_exits_2_instead_of_crashing(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout="https://[::1/octo/widgets\n")

        assert invoke("history", "--branch", "main").code == 2


class TestProviderDetection:
    def self_hosted(
        self,
        cli: FakeCli,
        *,
        gh_hosts: dict[str, object] | None,
        glab_ok: bool,
        host: str = "code.example.com",
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=f"git@{host}:team/proj.git\n")
        if gh_hosts is None:
            cli.on("gh", "auth", "status", "--json", "hosts", code=1, stderr="boom")
        else:
            hosts = json.dumps({"hosts": gh_hosts})
            cli.on("gh", "auth", "status", "--json", "hosts", stdout=hosts)
        cli.on("gh", "auth", "status", "--hostname", host)
        cli.on("gh", "api", stdout='{"workflow_runs": []}')
        if glab_ok:
            cli.on("glab", "auth", "status", "--hostname", host)
        else:
            cli.on("glab", "auth", "status", "--hostname", host, code=1, stderr="no")
        cli.on("glab", "api", "--hostname", host, "--method", "GET", "user", stdout="{}")
        cli.on("glab", "api", stdout="[]")

    @pytest.mark.parametrize(
        ("gh_on_path", "gh_hosts", "glab_on_path", "glab_ok", "expected"),
        [
            (True, {"code.example.com": []}, False, False, "gh"),
            (True, {"CODE.Example.com": []}, True, False, "gh"),
            (True, {"other.example.com": []}, True, True, "glab"),
            (True, None, True, True, "glab"),
            (False, {"code.example.com": []}, True, True, "glab"),
            (True, {"code.example.com": []}, False, True, "gh"),
        ],
        ids=[
            "gh lists the host",
            "gh host match ignores case",
            "gh lists another host, glab accepts",
            "gh status command fails, glab accepts",
            "gh missing, glab accepts",
            "glab missing, gh lists the host",
        ],
    )
    def test_self_hosted_host_picks_the_one_tool_that_knows_it(
        self,
        cli: FakeCli,
        invoke: Callable[..., Result],
        *,
        gh_on_path: bool,
        gh_hosts: dict[str, object] | None,
        glab_on_path: bool,
        glab_ok: bool,
        expected: str,
    ) -> None:
        self.self_hosted(cli, gh_hosts=gh_hosts, glab_ok=glab_ok)
        present = (("gh", gh_on_path), ("glab", glab_on_path))
        names = tuple(name for name, available in present if available)

        result = invoke("history", "--branch", "main", which=only(*names))

        assert result.code == 0
        assert {call[0] for call in cli.calls if call[1] == "api"} == {expected}

    def test_both_tools_claiming_a_self_hosted_host_exits_2_without_any_api_call(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        self.self_hosted(cli, gh_hosts={"code.example.com": []}, glab_ok=True)

        result = invoke("history", "--branch", "main")

        assert result.code == 2
        assert "both gh and glab know code.example.com" in result.err
        assert "--provider github|gitlab" in result.err
        assert cli.api_paths() == []

    @pytest.mark.parametrize(
        ("gh_hosts", "names"),
        [
            ({"other.example.com": []}, ("gh", "glab")),
            (None, ("gh", "glab")),
            ({"code.example.com": []}, ()),
            ({}, ("gh",)),
        ],
        ids=["host unknown to both", "gh status fails, glab rejects", "no tool installed", "empty"],
    )
    def test_host_that_no_tool_claims_exits_2(
        self,
        cli: FakeCli,
        invoke: Callable[..., Result],
        gh_hosts: dict[str, object] | None,
        names: tuple[str, ...],
    ) -> None:
        self.self_hosted(cli, gh_hosts=gh_hosts, glab_ok=False)

        result = invoke("history", "--branch", "main", which=only(*names))

        assert result.code == 2
        assert "cannot tell whether code.example.com is GitHub or GitLab" in result.err
        assert "--provider github|gitlab" in result.err
        assert cli.api_paths() == []

    def test_gh_host_listing_that_is_not_json_counts_as_no_claim(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        self.self_hosted(cli, gh_hosts={}, glab_ok=True)
        cli.on("gh", "auth", "status", "--json", stdout="<html>", override=True)

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        assert {call[0] for call in cli.calls if call[1] == "api"} == {"glab"}

    def test_public_hosts_need_no_probe_of_the_other_tool(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        assert invoke("history", "--branch", "main").code == 0
        assert cli.tools_called() == {"git", "gh"}
        assert not any("--json" in call for call in cli.calls)

    def test_explicit_provider_skips_detection_for_a_self_hosted_host(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        self.self_hosted(cli, gh_hosts={"code.example.com": []}, glab_ok=True)

        result = invoke("history", "--branch", "main", "--provider", "gitlab")

        assert result.code == 0
        assert not any("--json" in call for call in cli.calls)
        assert {call[0] for call in cli.calls if call[1] == "api"} == {"glab"}

    def test_host_and_repo_flags_skip_the_remote_altogether(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("gh", "auth", "status", "--hostname", "ghe.example.com")
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        result = invoke(
            "history",
            *("--provider", "github", "--host", "GHE.example.com", "--repo", "o/r"),
            *("--branch", "main"),
        )

        assert result.code == 0
        assert "git" not in cli.tools_called()
        assert cli.api_paths()[0].startswith("repos/o/r/actions/runs?")
        assert ("gh", "auth", "status", "--hostname", "ghe.example.com") in cli.calls

    @pytest.mark.parametrize(
        ("provider", "repo", "host", "tool"),
        [
            ("github", "octo/widgets", "github.com", "gh"),
            ("gitlab", "group/proj", "gitlab.com", "glab"),
        ],
    )
    def test_provider_and_repo_without_a_remote_fall_back_to_the_public_host(
        self,
        cli: FakeCli,
        invoke: Callable[..., Result],
        provider: str,
        repo: str,
        host: str,
        tool: str,
    ) -> None:
        cli.on("git", "remote", "get-url", code=2, stderr="error: No such remote 'origin'")
        cli.on(tool, "auth", "status", "--hostname", host)
        cli.on(tool, "api", "--hostname", host, "--method", "GET", "user", stdout="{}")
        cli.on(tool, "api", stdout='{"workflow_runs": []}' if tool == "gh" else "[]")

        result = invoke("history", "--provider", provider, "--repo", repo, "--branch", "main")

        assert result.code == 0
        assert (tool, "auth", "status", "--hostname", host) in cli.calls

    @pytest.mark.parametrize(
        "argv",
        [
            ("--provider", "auto", "--repo", "octo/widgets"),
            ("--provider", "github"),
            ("--provider", "github", "--host", "ghe.example.com"),
        ],
        ids=["auto provider cannot guess a host", "no repo", "host without repo"],
    )
    def test_missing_remote_without_enough_flags_exits_2_and_says_what_to_pass(
        self, cli: FakeCli, invoke: Callable[..., Result], argv: tuple[str, ...]
    ) -> None:
        cli.on("git", "remote", "get-url", code=2, stderr="error: No such remote 'origin'")

        result = invoke("history", "--branch", "main", *argv)

        assert result.code == 2
        assert "pass --host and --repo" in result.err
        assert cli.api_paths() == []

    def test_unparseable_remote_with_provider_and_repo_falls_back_to_the_public_host(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout="/srv/git/widgets.git\n")
        cli.on("gh", "auth", "status", "--hostname", "github.com")
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        result = invoke(
            "history", "--branch", "main", "--provider", "github", "--repo", "octo/widgets"
        )

        assert result.code == 0

    def test_repo_flag_overrides_the_path_of_the_remote_but_keeps_its_host(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        invoke("history", "--branch", "main", "--repo", "other/thing")

        assert cli.api_paths()[0].startswith("repos/other/thing/actions/runs?")

    def test_another_remote_can_be_selected_by_name(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", "upstream", stdout=GITHUB_REMOTE + "\n")
        cli.on("gh", "auth", "status", "--hostname", "github.com")
        cli.on("gh", "api", stdout='{"workflow_runs": []}')

        assert invoke("history", "--branch", "main", "--remote", "upstream").code == 0
        assert ("git", "remote", "get-url", "upstream") in cli.calls

    @pytest.mark.parametrize("name", ["-x", "--upload-pack=evil", "a b", "", "a;b", "$(x)"])
    def test_remote_name_that_could_be_read_as_a_flag_or_shell_is_refused(
        self, cli: FakeCli, invoke: Callable[..., Result], name: str
    ) -> None:
        result = invoke("history", "--branch", "main", f"--remote={name}")

        assert result.code == 2
        assert "invalid remote name" in result.err
        assert cli.calls == []


class TestToolAndAuthentication:
    @pytest.mark.parametrize(
        ("remote", "tool", "label"),
        [
            (GITHUB_REMOTE, "gh", "GitHub CLI"),
            (GITLAB_REMOTE, "glab", "GitLab CLI"),
        ],
    )
    def test_missing_tool_exits_2_before_any_authentication_call(
        self, cli: FakeCli, invoke: Callable[..., Result], remote: str, tool: str, label: str
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=remote + "\n")

        result = invoke("history", "--branch", "main", which=missing)

        assert result.code == 2
        assert f"{tool} not found on PATH; install {label} or pass --provider" in result.err
        assert cli.tools_called() == {"git"}

    def test_unauthenticated_gh_exits_3_with_the_login_command_and_the_cli_stderr(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=GITHUB_REMOTE + "\n")
        cli.on(
            "gh",
            *("auth", "status", "--hostname", "github.com"),
            code=1,
            stderr="You are not logged into any GitHub hosts.",
        )

        result = invoke("history", "--branch", "main")

        assert result.code == 3
        login = "gh is not authenticated for github.com; run: gh auth login --hostname github.com"
        assert login in result.err
        assert "You are not logged into any GitHub hosts." in result.err
        assert cli.api_paths() == []
        assert not any("--json" in call for call in cli.calls)

    def test_unauthenticated_glab_exits_3_without_the_confirming_api_call(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=GITLAB_REMOTE + "\n")
        cli.on("glab", "auth", "status", "--hostname", "gitlab.com", code=1, stderr="no token")

        result = invoke("history", "--branch", "main")

        assert result.code == 3
        assert "glab auth login --hostname gitlab.com" in result.err
        assert cli.api_paths() == []

    def test_glab_status_ok_but_user_call_failing_still_exits_3(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        cli.on("git", "remote", "get-url", stdout=GITLAB_REMOTE + "\n")
        cli.on("glab", "auth", "status", "--hostname", "gitlab.com")
        cli.on(
            "glab",
            *("api", "--hostname", "gitlab.com", "--method", "GET", "user"),
            code=1,
            stderr="401 Unauthorized",
        )

        result = invoke("history", "--branch", "main")

        assert result.code == 3
        assert "glab auth login --hostname gitlab.com" in result.err
        assert "401 Unauthorized" in result.err
        assert cli.api_paths() == ["user"]

    @pytest.mark.parametrize(
        ("provider", "repo", "host"),
        [
            ("github", "octo", "github.com"),
            ("github", "a/b/c", "github.com"),
            ("github", "octo/wid gets", "github.com"),
            ("github", "octo/", "github.com"),
            ("github", "../r", "github.com"),
            ("github", "./r", "github.com"),
            ("github", "o/..", "github.com"),
            ("github", "o/.", "github.com"),
            ("gitlab", "g/../p", "gitlab.com"),
            ("gitlab", "g/./p", "gitlab.com"),
            ("gitlab", "../p", "gitlab.com"),
            ("github", "$(id)/x", "github.com"),
            ("gitlab", "solo", "gitlab.com"),
            ("gitlab", "group//proj", "gitlab.com"),
            ("gitlab", "group/pro;j", "gitlab.com"),
            ("gitlab", "group/proj?x=1", "gitlab.com"),
        ],
    )
    def test_malformed_repository_exits_2_before_any_listing_call(
        self, cli: FakeCli, invoke: Callable[..., Result], provider: str, repo: str, host: str
    ) -> None:
        tool = crt.TOOLS[provider]
        cli.on(tool, "auth", "status", "--hostname", host)
        cli.on(tool, "api", "--hostname", host, "--method", "GET", "user", stdout="{}")

        result = invoke("history", "--provider", provider, "--host", host, "--repo", repo)

        assert result.code == 2
        assert "is not of the form" in result.err
        assert all(path == "user" for path in cli.api_paths())

    @pytest.mark.parametrize("repo", ["a/../b", "a", "../b", "a/./b", "a/b/c"])
    def test_malformed_repository_with_an_explicit_github_provider_touches_no_tool(
        self, cli: FakeCli, invoke: Callable[..., Result], repo: str
    ) -> None:
        result = invoke(
            "history", *("--provider", "github", "--host", "github.com", "--repo", repo)
        )

        assert result.code == 2
        assert "is not of the form" in result.err
        assert cli.calls == []

    @pytest.mark.parametrize("repo", ["a/../b", "a", "../b", "a/./b"])
    def test_malformed_repository_is_refused_before_provider_detection(
        self, cli: FakeCli, invoke: Callable[..., Result], repo: str
    ) -> None:
        cli.on("git", "remote", "get-url", stdout="git@code.example.com:team/proj.git\n")

        result = invoke("history", "--repo", repo)

        assert result.code == 2
        assert "is not of the form" in result.err
        assert cli.tools_called() == {"git"}

    def test_gitlab_subgroup_path_is_percent_encoded_into_one_project_segment(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        cli.on("glab", "api", stdout="[]")

        invoke("history", "--branch", "main")

        assert cli.api_paths("glab")[1].startswith("projects/group%2Fsub%2Fproj/pipelines?")


class TestHistory:
    @staticmethod
    def github_page(first: int, count: int) -> str:
        runs = [
            {
                "id": first + offset,
                "run_attempt": 1 + (offset % 2),
                "head_branch": "main",
                "head_sha": f"{first + offset:040x}",
                "status": "completed",
                "conclusion": "success",
                "created_at": at(offset),
                "run_started_at": at(offset),
                "updated_at": at(offset + 90),
            }
            for offset in range(count)
        ]
        return json.dumps({"total_count": 999, "workflow_runs": runs})

    @staticmethod
    def pipeline_listing(ids: Sequence[int]) -> str:
        return json.dumps(
            [
                {
                    "id": item,
                    "status": "success",
                    "ref": "main",
                    "sha": f"{item:040x}",
                    "created_at": at(item),
                }
                for item in ids
            ]
        )

    @staticmethod
    def pipeline_detail(pipeline_id: int) -> str:
        return json.dumps(
            {
                "id": pipeline_id,
                "project_id": 7,
                "status": "success",
                "ref": "main",
                "sha": f"{pipeline_id:040x}",
                "created_at": at(pipeline_id),
                "started_at": at(pipeline_id + 5),
                "finished_at": at(pipeline_id + 125),
            }
        )

    def serve_pipelines(self, cli: FakeCli, ids: Sequence[int]) -> None:
        for ident in ids:
            cli.on(
                "glab",
                "api",
                path=f"{GITLAB_PROJECT}/pipelines/{ident}",
                stdout=self.pipeline_detail(ident),
            )

    def test_github_rows_follow_the_documented_columns_and_compute_the_wall_clock(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(500, 2))

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        header, first, second = (line.split("\t") for line in result.out.splitlines())
        assert header == HISTORY_COLUMNS
        assert first == [
            *("github", "500", "1", "main", f"{500:040x}"),
            *("completed", "success", at(0), "90"),
        ]
        assert second[1:3] == ["501", "2"]

    def test_github_query_asks_for_completed_runs_of_the_branch(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(1, 1))

        invoke("history", "--branch", "release/1.2")

        [path] = cli.api_paths("gh")
        assert path.startswith(f"{GITHUB_PROJECT}/actions/runs?")
        assert query(path) == {
            "branch": "release/1.2",
            "status": "completed",
            "per_page": "30",
            "page": "1",
        }
        assert "branch=release%2F1.2" in path

    def test_branch_name_cannot_inject_query_parameters(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(1, 1))

        invoke("history", "--branch", "main&status=queued#x")

        [path] = cli.api_paths("gh")
        assert query(path)["status"] == "completed"
        assert query(path)["branch"] == "main&status=queued#x"

    def test_current_branch_is_used_when_none_is_given(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("git", "rev-parse", "--abbrev-ref", "HEAD", stdout="topic\n")
        cli.on("gh", "api", stdout=self.github_page(1, 1))

        invoke("history")

        assert query(cli.api_paths("gh")[0])["branch"] == "topic"

    @pytest.mark.parametrize(
        ("code", "stdout"), [(0, "HEAD\n"), (0, "\n"), (128, "HEAD\n"), (128, "")]
    )
    def test_detached_head_or_unreadable_branch_exits_2(
        self, cli: FakeCli, invoke: Callable[..., Result], code: int, stdout: str
    ) -> None:
        github_ready(cli)
        cli.on("git", "rev-parse", "--abbrev-ref", "HEAD", code=code, stdout=stdout)

        result = invoke("history")

        assert result.code == 2
        assert "pass --branch" in result.err
        assert cli.api_paths() == []

    def test_a_short_page_ends_the_listing_after_one_call(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(1, 3))

        result = invoke("history", "--branch", "main", "--limit", "5")

        assert len(result.out.splitlines()) == 1 + 3
        assert len(cli.api_paths("gh")) == 1
        assert query(cli.api_paths("gh")[0])["per_page"] == "5"

    def test_a_full_page_at_the_limit_needs_no_second_call(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(1, 2))

        result = invoke("history", "--branch", "main", "--limit", "2")

        assert len(result.out.splitlines()) == 1 + 2
        assert len(cli.api_paths("gh")) == 1

    def test_limit_across_pages_truncates_to_exactly_the_limit(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        base = f"{GITHUB_PROJECT}/actions/runs?branch=main&status=completed&per_page=100"
        cli.on("gh", "api", path=f"{base}&page=1", stdout=self.github_page(1000, 100))
        cli.on("gh", "api", path=f"{base}&page=2", stdout=self.github_page(2000, 100))
        cli.on("gh", "api", path=f"{base}&page=3", stdout=self.github_page(3000, 100))

        result = invoke("history", "--branch", "main", "--limit", "150")

        ids = [line.split("\t")[1] for line in result.out.splitlines()[1:]]
        assert len(ids) == 150
        assert ids[0] == "1000"
        assert ids[100] == "2000"
        assert ids[-1] == "2049"
        assert len(cli.api_paths("gh")) == 2

    def test_paging_stops_at_the_first_short_page(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        base = f"{GITHUB_PROJECT}/actions/runs?branch=main&status=completed&per_page=100"
        cli.on("gh", "api", path=f"{base}&page=1", stdout=self.github_page(1000, 100))
        cli.on("gh", "api", path=f"{base}&page=2", stdout=self.github_page(2000, 20))

        result = invoke("history", "--branch", "main", "--limit", "500")

        assert len(result.out.splitlines()) == 1 + 120
        assert len(cli.api_paths("gh")) == 2

    def test_server_returning_more_than_the_page_size_is_still_cut_at_the_limit(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(1, 5))

        result = invoke("history", "--branch", "main", "--limit", "2")

        assert len(result.out.splitlines()) == 1 + 2

    def test_no_runs_prints_only_the_header(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout='{"total_count": 0, "workflow_runs": []}')

        result = invoke("history", "--branch", "main")

        assert result.code == 0
        assert result.out == "\t".join(HISTORY_COLUMNS) + "\n"

    @pytest.mark.parametrize("body", ["{}", "[]", "not json", '{"workflow_runs": 5}', ""])
    def test_unexpected_response_exits_4(
        self, cli: FakeCli, invoke: Callable[..., Result], body: str
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=body)

        result = invoke("history", "--branch", "main")

        assert result.code == 4
        assert "unexpected response" in result.err
        assert result.out == ""

    def test_api_failure_exits_4_with_the_cli_stderr(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", code=1, stderr="gh: Not Found (HTTP 404)")

        result = invoke("history", "--branch", "main")

        assert result.code == 4
        assert "gh: Not Found (HTTP 404)" in result.err

    def test_out_directory_receives_the_raw_records_under_a_safe_file_name(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(7, 2))
        out = tmp_path / "nested" / "out"

        result = invoke("history", "--branch", "feature/a b", "--out", str(out))

        assert result.code == 0
        [stored] = list(out.iterdir())
        assert stored.name == "history-feature_a_b.json"
        assert [run["id"] for run in json.loads(stored.read_text())] == [7, 8]

    def test_unusable_out_directory_exits_2(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", stdout=self.github_page(7, 2))
        blocker = tmp_path / "file"
        blocker.write_text("x")

        result = invoke("history", "--branch", "main", "--out", str(blocker / "sub"))

        assert result.code == 2
        assert "cannot create" in result.err

    def test_gitlab_pipelines_are_read_again_individually_for_their_wall_clock(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        self.serve_pipelines(cli, [30, 20])
        cli.on("glab", "api", stdout=self.pipeline_listing([30, 20]))

        result = invoke("history", "--branch", "main", "--limit", "2")

        assert result.code == 0
        header, first, second = (line.split("\t") for line in result.out.splitlines())
        assert header == HISTORY_COLUMNS
        assert first == [
            *("gitlab", "30", "", "main", f"{30:040x}"),
            *("success", "success", at(30), "120"),
        ]
        assert second[1] == "20"
        listing, *details = cli.api_paths("glab")[1:]
        assert query(listing) == {
            "ref": "main",
            "status": "success",
            "order_by": "id",
            "sort": "desc",
            "per_page": "2",
            "page": "1",
        }
        assert details == [f"{GITLAB_PROJECT}/pipelines/30", f"{GITLAB_PROJECT}/pipelines/20"]

    def test_gitlab_rereads_only_as_many_pipelines_as_the_limit(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        self.serve_pipelines(cli, [30, 20])
        cli.on("glab", "api", stdout=self.pipeline_listing([30, 20, 10]))

        result = invoke("history", "--branch", "main", "--limit", "2")

        assert len(result.out.splitlines()) == 1 + 2
        assert len(cli.api_paths("glab")) == 1 + 1 + 2

    def test_gitlab_full_page_continues_and_short_page_stops_the_listing(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        base = (
            f"{GITLAB_PROJECT}/pipelines?ref=main&status=success&order_by=id&sort=desc&per_page=100"
        )
        first_page = list(range(2000, 1900, -1))
        second_page = list(range(1900, 1880, -1))
        cli.on("glab", "api", path=f"{base}&page=1", stdout=self.pipeline_listing(first_page))
        cli.on("glab", "api", path=f"{base}&page=2", stdout=self.pipeline_listing(second_page))
        self.serve_pipelines(cli, first_page + second_page)

        result = invoke("history", "--branch", "main", "--limit", "500")

        ids = [line.split("\t")[1] for line in result.out.splitlines()[1:]]
        assert ids == [str(ident) for ident in first_page + second_page]
        listings = [path for path in cli.api_paths("glab") if "/pipelines?" in path]
        assert len(listings) == 2

    def test_failed_pipeline_reread_exits_4(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        cli.on("glab", "api", path=f"{GITLAB_PROJECT}/pipelines/30", code=1, stderr="404 Not Found")
        cli.on("glab", "api", stdout=self.pipeline_listing([30]))

        result = invoke("history", "--branch", "main", "--limit", "1")

        assert result.code == 4
        assert "404 Not Found" in result.err
        assert result.out == ""

    @pytest.mark.parametrize(
        "listing",
        [
            '[{"status": "success"}]',
            '[{"id": "30", "status": "success"}]',
            '[{"id": null}]',
            '[{"id": 30}, {"ref": "main"}]',
            "[1, 2]",
        ],
        ids=["no id", "string id", "null id", "second entry without id", "not objects"],
    )
    def test_gitlab_listing_entry_without_an_integer_id_exits_4_without_a_traceback(
        self, cli: FakeCli, invoke: Callable[..., Result], listing: str
    ) -> None:
        gitlab_ready(cli)
        self.serve_pipelines(cli, [30])
        cli.on("glab", "api", stdout=listing)

        result = invoke("history", "--branch", "main", "--limit", "2")

        assert result.code == 4
        assert "unexpected" in result.err
        assert "Traceback" not in result.err
        assert result.out == ""

    @pytest.mark.parametrize("limit", ["0", "-1", "abc", "1.5", ""])
    def test_limit_that_is_not_a_positive_integer_is_a_usage_error(
        self, capsys: pytest.CaptureFixture[str], limit: str
    ) -> None:
        with pytest.raises(SystemExit) as info:
            crt.main(["history", "--limit", limit], FakeCli(), both)

        assert info.value.code == 2
        assert "not a positive integer" in capsys.readouterr().err


class TestFetch:
    @staticmethod
    def fetch(
        invoke: Callable[..., Result], out: Path, *ids: str, extra: Sequence[str] = ()
    ) -> Result:
        return invoke("fetch", *extra, "--out", str(out), *ids)

    def test_github_run_is_stored_as_raw_json_plus_normalised_timings(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)
        out = tmp_path / "out"

        result = self.fetch(invoke, out, "1001")

        assert result.code == 0
        assert result.out == f"run 1001: 5 jobs stored in {out}\n"
        for name in ("run-1001.json", "jobs-1001.json"):
            assert json.loads((out / name).read_text()) == json.loads(
                (GITHUB_DATA / name).read_text()
            )
        assert sorted(path.name for path in out.iterdir()) == [
            "jobs-1001.json",
            "run-1001.json",
            "timings-1001.tsv",
        ]
        assert cli.api_paths("gh") == [github_run_path(1001), github_jobs_path(1001)]

    def test_github_timings_tsv_has_one_row_per_job_and_per_step(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)

        self.fetch(invoke, tmp_path, "1001")

        rows = read_rows(tmp_path / "timings-1001.tsv")
        assert rows[0] == TIMING_COLUMNS
        assert {len(row) for row in rows} == {15}
        records = read_records(tmp_path / "timings-1001.tsv")
        jobs = [row for row in records if row["step_number"] == ""]
        steps = [row for row in records if row["step_number"] != ""]
        assert [row["job_id"] for row in jobs] == ["11", "12", "13", "14", "15"]
        assert len(steps) == 18

    def test_github_job_rows_carry_exact_seconds_and_per_job_rounded_up_minutes(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)

        self.fetch(invoke, tmp_path, "1001")

        by_job = {
            row["job_id"]: row
            for row in read_records(tmp_path / "timings-1001.tsv")
            if row["step_number"] == ""
        }
        assert by_job["12"] == timing_row("github|1001|2|12|lint||completed|success|10|5|70|2|||")
        assert by_job["13"]["duration_s"] == "210"
        assert by_job["13"]["billed_min_estimate"] == "4"
        assert by_job["13"]["queued_s"] == "8"
        assert by_job["11"]["billed_min_estimate"] == "1"
        assert by_job["14"]["billed_min_estimate"] == ""
        assert by_job["14"]["conclusion"] == "skipped"
        assert by_job["15"] == timing_row("github|1001|1|15|never-started||queued||||||||")

    def test_github_step_rows_repeat_the_job_identity_and_leave_job_timings_empty(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)

        self.fetch(invoke, tmp_path, "1001")

        step = next(
            row
            for row in read_records(tmp_path / "timings-1001.tsv")
            if row["job_id"] == "13" and row["step_number"] == "4"
        )
        assert step == timing_row("github|1001|1|13|test||completed|success|||||4|Run pytest|180")

    def test_paginated_job_pages_are_merged_without_duplicates(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        jobs = json.loads((GITHUB_DATA / "jobs-1001.json").read_text())["jobs"]
        pages = [{"total_count": 5, "jobs": jobs[:3]}, {"total_count": 5, "jobs": jobs[2:]}]
        cli.on(
            "gh",
            "api",
            path=github_jobs_path(1001),
            stdout="\n".join(json.dumps(page) for page in pages),
        )
        cli.on(
            "gh",
            "api",
            path=github_run_path(1001),
            stdout=(GITHUB_DATA / "run-1001.json").read_text(),
        )

        result = self.fetch(invoke, tmp_path, "1001")

        assert result.out == f"run 1001: 5 jobs stored in {tmp_path}\n"
        stored = json.loads((tmp_path / "jobs-1001.json").read_text())
        assert [job["id"] for job in stored["jobs"]] == [11, 12, 13, 14, 15]
        assert stored["total_count"] == 5

    def test_jobs_call_paginates_and_the_run_call_does_not(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)

        self.fetch(invoke, tmp_path, "1001")

        jobs_call = next(call for call in cli.calls if call[-1] == github_jobs_path(1001))
        run_call = next(call for call in cli.calls if call[-1] == github_run_path(1001))
        assert "--paginate" in jobs_call
        assert "--paginate" not in run_call

    def test_one_runs_api_failure_does_not_stop_the_others_but_exits_4(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", path=github_run_path(1001), code=1, stderr="gh: Not Found (HTTP 404)")
        serve_github_run(cli, 1002)

        result = self.fetch(invoke, tmp_path, "1001", "1002")

        assert result.code == 4
        assert "run 1001" in result.err
        assert "gh: Not Found (HTTP 404)" in result.err
        assert result.out == f"run 1002: 3 jobs stored in {tmp_path}\n"
        assert (tmp_path / "timings-1002.tsv").exists()
        assert not list(tmp_path.glob("*1001*"))

    def test_failure_of_a_later_run_keeps_the_earlier_one_and_still_exits_4(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)
        cli.on("gh", "api", path=github_run_path(1002), code=1, stderr="HTTP 500")

        result = self.fetch(invoke, tmp_path, "1001", "1002")

        assert result.code == 4
        assert (tmp_path / "run-1001.json").exists()
        assert not list(tmp_path.glob("*1002*"))

    def test_a_failing_jobs_call_leaves_no_partial_files_for_that_run(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        cli.on("gh", "api", path=github_jobs_path(1001), code=1, stderr="HTTP 502")
        cli.on(
            "gh",
            "api",
            path=github_run_path(1001),
            stdout=(GITHUB_DATA / "run-1001.json").read_text(),
        )

        result = self.fetch(invoke, tmp_path, "1001")

        assert result.code == 4
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize(
        "body",
        ["not json", "[]", "{}", '{"id": 1001}', '{"id": "x", "workflow_id": 5}', ""],
        ids=["text", "array", "empty object", "no provider marker", "string id", "empty"],
    )
    def test_unexpected_run_document_exits_4_and_stores_nothing(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result], body: str
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)
        cli.on("gh", "api", path=github_run_path(1001), stdout=body, override=True)

        result = self.fetch(invoke, tmp_path, "1001")

        assert result.code == 4
        assert list(tmp_path.iterdir()) == []

    def test_sections_flag_on_github_exits_2_before_any_api_call_or_directory(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        out = tmp_path / "out"

        result = self.fetch(invoke, out, "1001", extra=("--sections",))

        assert result.code == 2
        assert "--sections applies to GitLab only" in result.err
        assert cli.api_paths() == []
        assert not out.exists()

    def test_output_path_that_is_a_file_exits_2(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        blocker = tmp_path / "file"
        blocker.write_text("x")

        result = self.fetch(invoke, blocker, "1001")

        assert result.code == 2
        assert "cannot create" in result.err
        assert cli.api_paths() == []

    def test_unwritable_target_aborts_instead_of_counting_as_an_api_failure(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)
        serve_github_run(cli, 1002)
        (tmp_path / "run-1001.json").mkdir()

        result = self.fetch(invoke, tmp_path, "1001", "1002")

        assert result.code == 2
        assert "cannot write" in result.err
        assert not (tmp_path / "run-1002.json").exists()

    @pytest.mark.parametrize("run_id", ["0", "abc", "1.5", "1e3", "-4", "../1", ""])
    def test_run_id_that_is_not_a_positive_integer_is_a_usage_error(
        self, tmp_path: Path, run_id: str
    ) -> None:
        with pytest.raises(SystemExit) as info:
            crt.main(["fetch", "--out", str(tmp_path), run_id], FakeCli(), both)

        assert info.value.code == 2

    def test_gitlab_run_stores_pipeline_jobs_and_parsed_sections(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)

        result = self.fetch(invoke, tmp_path, "2001", extra=("--sections",))

        assert result.code == 0
        assert result.out == f"run 2001: 7 jobs stored in {tmp_path}\n"
        for name in ("run-2001.json", "jobs-2001.json", "sections-2001.json"):
            stored = json.loads((tmp_path / name).read_text())
            assert stored == json.loads((GITLAB_DATA / name).read_text()), name
        assert (tmp_path / "timings-2001.tsv").exists()

    def test_gitlab_logs_are_read_only_for_jobs_that_started(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)

        self.fetch(invoke, tmp_path, "2001", extra=("--sections",))

        assert cli.api_paths("glab")[1:] == [
            f"{GITLAB_PROJECT}/pipelines/2001",
            gitlab_jobs_path(2001),
            f"{GITLAB_PROJECT}/jobs/301/trace",
            f"{GITLAB_PROJECT}/jobs/302/trace",
            f"{GITLAB_PROJECT}/jobs/303/trace",
            f"{GITLAB_PROJECT}/jobs/307/trace",
        ]
        sections = json.loads((tmp_path / "sections-2001.json").read_text())
        assert sorted(sections) == ["301", "302", "303", "307"]

    def test_gitlab_without_sections_downloads_no_logs_and_stores_no_sections_file(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)

        result = self.fetch(invoke, tmp_path, "2001")

        assert result.code == 0
        assert not any("/trace" in path for path in cli.api_paths())
        assert not (tmp_path / "sections-2001.json").exists()
        jobs_call = next(call for call in cli.calls if call[-1] == gitlab_jobs_path(2001))
        assert "--paginate" in jobs_call

    def test_gitlab_timings_use_retry_index_stage_and_unrounded_minutes(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)

        self.fetch(invoke, tmp_path, "2001", extra=("--sections",))

        records = read_records(tmp_path / "timings-2001.tsv")
        jobs = {row["job_id"]: row for row in records if row["step_number"] == ""}
        assert jobs["303"] == timing_row(
            "gitlab|2001|2|303|test|test|success|success|3.5|120|150|2.5|||"
        )
        assert jobs["302"]["attempt"] == "1"
        assert jobs["302"]["billed_min_estimate"] == "0.6667"
        assert jobs["301"]["attempt"] == "1"
        assert jobs["304"]["conclusion"] == "skipped"
        assert jobs["304"]["billed_min_estimate"] == ""
        assert jobs["305"]["conclusion"] == ""
        assert jobs["305"]["status"] == "created"
        assert jobs["306"] == timing_row("gitlab|2001|1|306|release|deploy|manual||||||||")
        assert jobs["307"] == timing_row("gitlab|2001|1|307|smoke|test|running||1|80|||||")
        running = [row for row in records if row["job_id"] == "307" and row["step_number"] != ""]
        assert [(row["status"], row["step_duration_s"]) for row in running] == [("open", "")]
        build = [row for row in records if row["job_id"] == "301" and row["step_number"] != ""]
        assert [
            (row["step_number"], row["step_name"], row["step_duration_s"]) for row in build
        ] == [
            ("1", "prepare_executor", "2"),
            ("2", "get_sources", "4"),
            ("3", "step_script", "50"),
            ("4", "compile", "40"),
            ("5", "upload_artifacts_on_success", "2"),
            ("6", "cleanup_file_variables", "2"),
        ]

    def test_a_failing_log_download_fails_that_pipeline_only(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)
        cli.on(
            "glab",
            "api",
            path=f"{GITLAB_PROJECT}/jobs/302/trace",
            code=1,
            stderr="404 Not Found",
            override=True,
        )
        cli.on(
            "glab", "api", path=f"{GITLAB_PROJECT}/pipelines/2002", stdout=json.dumps(gl_run(2002))
        )
        cli.on("glab", "api", path=gitlab_jobs_path(2002), stdout="[]")

        result = self.fetch(invoke, tmp_path, "2001", "2002", extra=("--sections",))

        assert result.code == 4
        assert "run 2001" in result.err
        assert "404 Not Found" in result.err
        assert not list(tmp_path.glob("*2001*"))
        assert (tmp_path / "timings-2002.tsv").exists()

    def test_paginated_gitlab_job_arrays_are_merged_without_duplicates(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)
        jobs = json.loads((GITLAB_DATA / "jobs-2001.json").read_text())
        cli.on(
            "glab",
            "api",
            path=gitlab_jobs_path(2001),
            stdout=json.dumps(jobs[:3]) + json.dumps(jobs[2:]),
            override=True,
        )

        result = self.fetch(invoke, tmp_path, "2001")

        assert result.out == f"run 2001: 7 jobs stored in {tmp_path}\n"
        stored = json.loads((tmp_path / "jobs-2001.json").read_text())
        assert [job["id"] for job in stored] == [301, 302, 303, 304, 305, 306, 307]

    def test_log_without_a_section_end_is_stored_open(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)
        truncated = "\x1b[0Ksection_start:1767690082:step_script\r\x1b[0Kstep_script\noutput\n"
        cli.on(
            "glab", "api", path=f"{GITLAB_PROJECT}/jobs/302/trace", stdout=truncated, override=True
        )

        self.fetch(invoke, tmp_path, "2001", extra=("--sections",))

        stored = json.loads((tmp_path / "sections-2001.json").read_text())
        assert stored["302"] == [
            {"name": "step_script", "start": 1767690082, "end": None, "depth": 0}
        ]
        row = next(
            row
            for row in read_records(tmp_path / "timings-2001.tsv")
            if row["job_id"] == "302" and row["step_number"] == "1"
        )
        assert row["status"] == "open"
        assert row["step_duration_s"] == ""

    def test_names_with_tabs_and_newlines_cannot_break_the_tsv_layout(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        job = gh_job(5, "build\tlinux\nx64", 0, 60, steps=[gh_step(1, "Run\tmake\r\ntest", 0, 60)])
        cli.on("gh", "api", path=github_jobs_path(1), stdout=json.dumps(gh_jobs(job)))
        cli.on("gh", "api", path=github_run_path(1), stdout=json.dumps(gh_run(1)))

        self.fetch(invoke, tmp_path, "1")

        rows = read_rows(tmp_path / "timings-1.tsv")
        assert {len(row) for row in rows} == {15}
        assert len(rows) == 3
        assert rows[1][4] == "build linux x64"
        assert rows[2][13] == "Run make test"

    def test_every_external_call_carries_a_finite_positive_timeout(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        gitlab_ready(cli)
        serve_gitlab_pipeline(cli)

        self.fetch(invoke, tmp_path, "2001", extra=("--sections",))

        assert cli.timeouts
        assert all(0 < timeout < float("inf") for timeout in cli.timeouts)


class TestTimeoutsAndProcessHandling:
    def test_timeout_of_a_command_becomes_exit_4(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def hang(args: Sequence[str], *, timeout: float, **_rest: object) -> None:
            raise subprocess.TimeoutExpired(list(args), timeout)

        monkeypatch.setattr(crt.subprocess, "run", hang)

        with pytest.raises(crt.CiTimingsError) as info:
            crt.run_command(["gh", "api", "x"], 5.0)

        assert info.value.exit_code == 4
        assert "timed out after 5s" in str(info.value)

    def test_missing_executable_becomes_exit_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def absent(args: Sequence[str], **_rest: object) -> None:
            raise FileNotFoundError(2, "No such file", args[0])

        monkeypatch.setattr(crt.subprocess, "run", absent)

        with pytest.raises(crt.CiTimingsError) as info:
            crt.run_command(["gh", "api", "x"], 5.0)

        assert info.value.exit_code == 2
        assert "cannot run gh api x" in str(info.value)

    def test_command_is_run_without_a_shell_and_with_the_given_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, object] = {}

        def record(args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            seen["args"] = args
            seen.update(kwargs)
            return subprocess.CompletedProcess(list(args), 0, "", "")

        monkeypatch.setattr(crt.subprocess, "run", record)

        crt.run_command(["gh", "api", "a; rm -rf /"], 7.5)

        assert seen["args"] == ["gh", "api", "a; rm -rf /"]
        assert seen["timeout"] == 7.5
        assert seen["check"] is False
        assert not seen.get("shell")

    def test_non_utf8_output_is_replaced_and_a_failing_exit_is_returned_not_raised(self) -> None:
        script = "import sys; sys.stdout.buffer.write(b'ok\\xff'); sys.exit(3)"

        result = crt.run_command([sys.executable, "-c", script], 30.0)

        assert result.returncode == 3
        assert result.stdout == "ok�"

    @pytest.mark.parametrize("hanging", ["auth", "api"])
    def test_timeout_in_main_exits_4_whichever_call_hangs(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], hanging: str
    ) -> None:
        def fake(
            args: Sequence[str], *, timeout: float, **_rest: object
        ) -> subprocess.CompletedProcess[str]:
            if args[0] == "git":
                return subprocess.CompletedProcess(list(args), 0, GITHUB_REMOTE + "\n", "")
            if args[1] == hanging:
                raise subprocess.TimeoutExpired(list(args), timeout)
            return subprocess.CompletedProcess(list(args), 0, '{"workflow_runs": []}', "")

        monkeypatch.setattr(crt.subprocess, "run", fake)

        code = crt.main(["history", "--branch", "main"], which=both)

        assert code == 4
        assert "timed out" in capsys.readouterr().err

    def test_timeout_on_one_run_is_counted_and_the_next_run_is_still_fetched(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        jobs = (GITHUB_DATA / "jobs-1002.json").read_text()
        run = (GITHUB_DATA / "run-1002.json").read_text()

        def fake(
            args: Sequence[str], *, timeout: float, **_rest: object
        ) -> subprocess.CompletedProcess[str]:
            if args[0] == "git":
                return subprocess.CompletedProcess(list(args), 0, GITHUB_REMOTE + "\n", "")
            if args[1] == "auth":
                return subprocess.CompletedProcess(list(args), 0, "", "")
            if args[-1] == github_run_path(1001):
                raise subprocess.TimeoutExpired(list(args), timeout)
            body = jobs if args[-1] == github_jobs_path(1002) else run
            return subprocess.CompletedProcess(list(args), 0, body, "")

        monkeypatch.setattr(crt.subprocess, "run", fake)

        code = crt.main(["fetch", "--out", str(tmp_path), "1001", "1002"], which=both)

        captured = capsys.readouterr()
        assert code == 4
        assert "run 1001" in captured.err
        assert "timed out" in captured.err
        assert "run 1002: 3 jobs stored" in captured.out


class TestSectionParsing:
    @staticmethod
    def marker(kind: str, stamp: int, name: str) -> str:
        return f"\x1b[0Ksection_{kind}:{stamp}:{name}\r\x1b[0K"

    def test_nested_sections_record_depth_and_duration_in_start_order(self) -> None:
        log = (
            self.marker("start", 100, "outer")
            + "text\n"
            + self.marker("start", 110, "inner")
            + self.marker("end", 130, "inner")
            + self.marker("end", 160, "outer")
        )

        assert crt.parse_sections(log) == [
            crt.Section(name="outer", start=100, end=160, depth=0),
            crt.Section(name="inner", start=110, end=130, depth=1),
        ]

    def test_sequential_sections_with_the_same_name_are_kept_apart(self) -> None:
        log = (
            self.marker("start", 10, "step_script")
            + self.marker("end", 20, "step_script")
            + self.marker("start", 30, "step_script")
            + self.marker("end", 55, "step_script")
        )

        sections = crt.parse_sections(log)

        assert [(s.start, s.end, s.depth) for s in sections] == [(10, 20, 0), (30, 55, 0)]

    def test_end_closes_the_innermost_open_section_of_that_name(self) -> None:
        log = (
            self.marker("start", 1, "a")
            + self.marker("start", 2, "a")
            + self.marker("end", 3, "a")
            + self.marker("end", 4, "a")
        )

        sections = crt.parse_sections(log)

        assert [(s.start, s.end, s.depth) for s in sections] == [(1, 4, 0), (2, 3, 1)]

    def test_interleaved_sections_close_independently(self) -> None:
        log = (
            self.marker("start", 1, "a")
            + self.marker("start", 2, "b")
            + self.marker("end", 5, "a")
            + self.marker("end", 9, "b")
        )

        sections = crt.parse_sections(log)

        assert [(s.name, s.start, s.end) for s in sections] == [("a", 1, 5), ("b", 2, 9)]

    def test_section_that_never_ends_stays_open(self) -> None:
        log = (
            self.marker("start", 1, "a") + self.marker("start", 2, "b") + self.marker("end", 4, "b")
        )

        assert [(s.name, s.end) for s in crt.parse_sections(log)] == [("a", None), ("b", 4)]

    def test_end_without_a_start_is_ignored(self) -> None:
        assert crt.parse_sections(self.marker("end", 5, "ghost")) == []

    def test_collapsed_option_after_the_name_is_not_part_of_the_name(self) -> None:
        log = "\x1b[0Ksection_start:1:build[collapsed=true]\r\x1b[0Kheader\n" + self.marker(
            "end", 8, "build"
        )

        assert [(s.name, s.end) for s in crt.parse_sections(log)] == [("build", 8)]

    @pytest.mark.parametrize("log", ["", "plain output\nno markers\n", "section_start:1:a"])
    def test_log_without_markers_has_no_sections(self, log: str) -> None:
        assert crt.parse_sections(log) == []


class TestReport:
    def test_github_report_pins_timeline_totals_and_slow_steps(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(GITHUB_DATA), "1001")

        assert result.code == 0
        assert result.err == ""
        assert result.out.splitlines() == [
            "== run 1001 abc1234 success wall 75s",
            "  start      0s  end      0s  dur      0s  skipped  deploy",
            "  start      2s  end     62s  dur     60s  failure  lint",
            "  start      7s  end    217s  dur    210s  success  test",
            "  start      5s  end     75s  dur     70s  success  lint (attempt 2)",
            "  start      -   end      -   dur      -   queued  never-started",
            "  runner time total 340s (5.7 min)",
            "  billed estimate 7 min (each job rounded up to a whole minute)",
            "  steps >= 30s:",
            "        48s  lint :: Run make lint",
            "        50s  lint (attempt 2) :: Run make lint",
            "       180s  test :: Run pytest",
        ]
        assert cli.calls == []

    def test_gitlab_report_pins_timeline_unrounded_minutes_and_sections(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(GITLAB_DATA), "2001")

        assert result.code == 0
        assert result.out.splitlines() == [
            "== run 2001 fedcba9 success wall 270s",
            "  start      2s  end     62s  dur     60s  success  build",
            "  start     70s  end    110s  dur     40s  failed  test",
            "  start     80s  end      -   dur      -   running  smoke",
            "  start    120s  end    270s  dur    150s  success  test (attempt 2)",
            "  start      -   end      -   dur      -   skipped  deploy",
            "  start      -   end      -   dur      -   created  notify",
            "  start      -   end      -   dur      -   manual  release",
            "  runner time total 250s (4.2 min)",
            "  billed estimate 4.17 compute min (duration / 60 x cost factor 1, not rounded)",
            "  sections >= 30s:",
            "        50s  build :: step_script",
            "        40s  build :: compile",
            "        33s  test :: step_script",
            "       130s  test (attempt 2) :: step_script",
            "       open  smoke :: step_script",
        ]
        assert cli.calls == []

    def test_cost_factor_scales_gitlab_minutes_linearly(
        self, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(GITLAB_DATA), "2001", "--cost-factor", "2")

        billed = "  billed estimate 8.33 compute min (duration / 60 x cost factor 2, not rounded)"
        assert billed in result.out.splitlines()

    def test_cost_factor_on_a_github_run_exits_2_and_prints_no_report(
        self, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(GITHUB_DATA), "1001", "--cost-factor", "2")

        assert result.code == 2
        assert "--cost-factor applies to GitLab compute minutes only" in result.err
        assert result.out == ""

    @pytest.mark.parametrize("factor", ["0", "-1", "nan", "inf", "abc", ""])
    def test_cost_factor_must_be_a_positive_finite_number(self, factor: str) -> None:
        argv = ["report", str(GITLAB_DATA), "2001", "--cost-factor", factor]

        with pytest.raises(SystemExit) as info:
            crt.main(argv, FakeCli(), both)

        assert info.value.code == 2

    @pytest.mark.parametrize("seconds", ["-1", "nan", "inf", "abc"])
    def test_min_step_seconds_must_be_a_non_negative_finite_number(self, seconds: str) -> None:
        argv = ["report", str(GITHUB_DATA), "1001", "--min-step-seconds", seconds]

        with pytest.raises(SystemExit) as info:
            crt.main(argv, FakeCli(), both)

        assert info.value.code == 2

    def test_step_threshold_is_inclusive_at_the_boundary(
        self, invoke: Callable[..., Result]
    ) -> None:
        at_48 = invoke("report", str(GITHUB_DATA), "1001", "--min-step-seconds", "48").out
        above = invoke("report", str(GITHUB_DATA), "1001", "--min-step-seconds", "48.5").out

        assert "        48s  lint :: Run make lint" in at_48.splitlines()
        assert "        48s  lint :: Run make lint" not in above.splitlines()
        assert "        50s  lint (attempt 2) :: Run make lint" in above.splitlines()

    def test_zero_threshold_lists_every_step_and_a_high_one_lists_none(
        self, invoke: Callable[..., Result]
    ) -> None:
        everything = invoke("report", str(GITHUB_DATA), "1001", "--min-step-seconds", "0").out
        nothing = invoke("report", str(GITHUB_DATA), "1001", "--min-step-seconds", "100000").out

        assert len(table_after(everything, "  steps >= 0s:")) == 18
        assert nothing.splitlines()[-1] == "  steps >= 100000s:"

    def test_gitlab_report_without_fetched_sections_says_none_were_recorded(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gl_run(5), [gl_job(1, "build", 0, 60)])

        result = invoke("report", str(tmp_path), "5")

        assert result.code == 0
        none = "  sections: none recorded (fetch --sections reads them from the job logs)"
        assert none in result.out.splitlines()

    def test_open_section_is_shown_as_open_not_as_a_duration(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        sections = {
            "1": [
                {"name": "step_script", "start": 1769904000, "end": None, "depth": 0},
                {"name": "after", "start": 1769904001, "end": 1769904100, "depth": 0},
            ]
        }
        write_run(tmp_path, gl_run(5), [gl_job(1, "build", 0, 120)], sections)

        result = invoke("report", str(tmp_path), "5")

        assert re.search(r"^\s+open  build :: step_script$", result.out, re.MULTILINE)
        assert "99s  build :: after" in result.out

    def test_github_step_without_a_completion_time_is_shown_as_open(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        job = gh_job(1, "build", 0, None, conclusion=None, steps=[gh_step(1, "Run make", 0, None)])
        write_run(tmp_path, gh_run(5), gh_jobs(job))

        result = invoke("report", str(tmp_path), "5")

        assert result.code == 0
        assert re.search(r"^\s+open  build :: Run make$", result.out, re.MULTILINE)

    def test_completed_step_without_timestamps_is_not_reported_as_open(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        steps = [gh_step(1, "Run make", 0, 60), gh_skipped_step(2, "Run deploy")]
        write_run(tmp_path, gh_run(5), gh_jobs(gh_job(1, "build", 0, 60, steps=steps)))

        result = invoke("report", str(tmp_path), "5")

        assert "open" not in result.out

    def test_run_without_any_jobs_reports_zero_without_failing(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gh_run(5), gh_jobs())

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert lines[0] == "== run 5 0123456 success wall -s"
        assert "  runner time total 0s (0.0 min)" in lines
        assert "  billed estimate 0 min (each job rounded up to a whole minute)" in lines

    def test_run_where_no_job_ever_started_lists_them_all_with_dashes(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        del run["created_at"], run["run_started_at"]
        jobs = gh_jobs(
            gh_job(1, "a", None, None, conclusion=None), gh_job(2, "b", None, None, conclusion=None)
        )
        write_run(tmp_path, run, jobs)

        result = invoke("report", str(tmp_path), "5")

        assert result.code == 0
        waiting = [line for line in result.out.splitlines() if line.startswith("  start")]
        assert len(waiting) == 2
        shape = r"  start      -   end      -   dur      -   queued  [ab]"
        assert all(re.fullmatch(shape, line) for line in waiting)

    def test_job_without_an_end_is_listed_with_dashes_and_costs_nothing(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        jobs = gh_jobs(gh_job(1, "running", 30, None, conclusion=None), gh_job(2, "done", 0, 61))
        write_run(tmp_path, gh_run(5), jobs)

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert "  start     30s  end      -   dur      -   queued  running" in lines
        assert "  runner time total 61s (1.0 min)" in lines

    @pytest.mark.parametrize(
        ("seconds", "billed"), [(1, 1), (59, 1), (60, 1), (61, 2), (119, 2), (120, 2), (121, 3)]
    )
    def test_github_job_minutes_are_rounded_up_per_job(
        self, tmp_path: Path, invoke: Callable[..., Result], seconds: int, billed: int
    ) -> None:
        write_run(tmp_path, gh_run(5), gh_jobs(gh_job(1, "j", 0, seconds)))

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert f"  billed estimate {billed} min (each job rounded up to a whole minute)" in lines

    def test_github_rounding_applies_to_each_job_before_summing(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        jobs = gh_jobs(gh_job(1, "a", 0, 30), gh_job(2, "b", 0, 30), gh_job(3, "c", 0, 30))
        write_run(tmp_path, gh_run(5), jobs)

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert "  runner time total 90s (1.5 min)" in lines
        assert "  billed estimate 3 min (each job rounded up to a whole minute)" in lines

    def test_skipped_job_costs_nothing_even_when_it_carries_a_duration(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        jobs = gh_jobs(gh_job(1, "skip", 0, 500, conclusion="skipped"), gh_job(2, "ok", 0, 10))
        write_run(tmp_path, gh_run(5), jobs)

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert "  runner time total 10s (0.2 min)" in lines
        assert "  billed estimate 1 min (each job rounded up to a whole minute)" in lines
        assert lines[0].endswith("wall 10s")

    def test_gitlab_retry_index_follows_job_id_not_the_order_of_the_listing(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        jobs = json.loads((GITLAB_DATA / "jobs-2001.json").read_text())
        write_run(tmp_path, json.loads((GITLAB_DATA / "run-2001.json").read_text()), jobs[::-1])

        lines = invoke("report", str(tmp_path), "2001").out.splitlines()

        assert "  start     70s  end    110s  dur     40s  failed  test" in lines
        assert "  start    120s  end    270s  dur    150s  success  test (attempt 2)" in lines

    @pytest.mark.parametrize(
        ("started", "created", "job_start", "offset"),
        [
            pytest.param(100, 0, 110, 10, id="run_started_at wins over created_at"),
            pytest.param(None, 50, 70, 20, id="created_at when the run has no start"),
            pytest.param(None, None, 70, 0, id="earliest job start when the run has no times"),
        ],
    )
    def test_offsets_are_measured_from_the_best_known_start_of_the_run(
        self,
        tmp_path: Path,
        invoke: Callable[..., Result],
        started: float | None,
        created: float | None,
        job_start: float,
        offset: int,
    ) -> None:
        run = gh_run(5)
        for key, value in (("run_started_at", started), ("created_at", created)):
            if value is None:
                del run[key]
            else:
                run[key] = at(value)
        later = gh_job(2, "later", job_start + 30, job_start + 40)
        write_run(tmp_path, run, gh_jobs(gh_job(1, "first", job_start, job_start + 10), later))

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        first = next(line for line in lines if line.endswith("  first"))
        assert first.split()[1] == f"{offset}s"

    def test_gitlab_timeline_is_in_start_order_across_retries(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        jobs = [
            gl_job(1, "test", 0, 20, status="failed"),
            gl_job(2, "lint", 60, 80),
            gl_job(3, "test", 50, 90),
        ]
        write_run(tmp_path, gl_run(5), jobs)

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert lines[1:4] == [
            "  start      0s  end     20s  dur     20s  failed  test",
            "  start     50s  end     90s  dur     40s  success  test (attempt 2)",
            "  start     60s  end     80s  dur     20s  success  lint",
        ]

    def test_github_timeline_is_grouped_by_attempt_not_by_start_offset(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_attempt"] = 2
        run["run_started_at"] = at(1000)
        jobs = gh_jobs(
            gh_job(1, "a", 0, 10),
            gh_job(2, "b", 100, 110),
            gh_job(3, "a", 1000, 1010, attempt=2),
        )
        write_run(tmp_path, run, jobs)

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert lines[1:4] == [
            "  start      0s  end     10s  dur     10s  success  a",
            "  start    100s  end    110s  dur     10s  success  b",
            "  start      0s  end     10s  dur     10s  success  a (attempt 2)",
        ]

    def test_rerun_attempts_are_measured_from_their_own_start_and_never_go_negative(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_attempt"] = 2
        run["created_at"] = at(0)
        run["run_started_at"] = at(1000)
        jobs = gh_jobs(
            gh_job(1, "build", 0, 60),
            gh_job(2, "test", 10, 30),
            gh_job(3, "build", 1010, 1050, attempt=2),
        )
        write_run(tmp_path, run, jobs)

        out = invoke("report", str(tmp_path), "5").out

        assert out.splitlines()[:4] == [
            "== run 5 0123456 success wall 50s",
            "  start      0s  end     60s  dur     60s  success  build",
            "  start     10s  end     30s  dur     20s  success  test",
            "  start     10s  end     50s  dur     40s  success  build (attempt 2)",
        ]
        assert not re.search(r"start\s+-\d", out)
        assert not re.search(r"end\s+-\d", out)

    def test_rerun_whose_jobs_start_before_run_started_at_is_measured_from_its_first_job(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_attempt"] = 2
        run["run_started_at"] = at(1020)
        write_run(
            tmp_path, run, gh_jobs(gh_job(1, "a", 0, 5), gh_job(2, "a", 1010, 1030, attempt=2))
        )

        out = invoke("report", str(tmp_path), "5").out.splitlines()

        assert out[0].endswith("wall 20s")
        assert "  start      0s  end     20s  dur     20s  success  a (attempt 2)" in out

    def test_attempts_after_the_first_never_borrow_the_run_start_of_an_earlier_one(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_attempt"] = 3
        run["run_started_at"] = at(2000)
        jobs = gh_jobs(
            gh_job(1, "a", 100, 160),
            gh_job(2, "a", 1100, 1130, attempt=2),
            gh_job(3, "a", 2100, 2110, attempt=3),
        )
        write_run(tmp_path, run, jobs)

        out = invoke("report", str(tmp_path), "5").out.splitlines()

        assert out[0].endswith("wall 110s")
        assert "  start      0s  end     60s  dur     60s  success  a" in out
        assert "  start      0s  end     30s  dur     30s  success  a (attempt 2)" in out
        assert "  start    100s  end    110s  dur     10s  success  a (attempt 3)" in out

    def test_an_earlier_attempt_ignores_run_started_at_even_when_it_precedes_its_jobs(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_attempt"] = 2
        run["run_started_at"] = at(50)
        jobs = gh_jobs(gh_job(1, "a", 100, 160), gh_job(2, "a", 1000, 1010, attempt=2))
        write_run(tmp_path, run, jobs)

        out = invoke("report", str(tmp_path), "5").out.splitlines()

        assert "  start      0s  end     60s  dur     60s  success  a" in out
        assert "  start    950s  end    960s  dur     10s  success  a (attempt 2)" in out

    def test_github_rerun_fixture_pins_each_attempt_origin_and_the_latest_wall_clock(
        self, invoke: Callable[..., Result]
    ) -> None:
        out = invoke("report", str(GITHUB_DATA), "1001").out.splitlines()

        attempt_one = [line for line in out if line.endswith(("deploy", "  lint", "  test"))]
        assert [line.split()[1] for line in attempt_one] == ["0s", "2s", "7s"]
        assert "  start      5s  end     75s  dur     70s  success  lint (attempt 2)" in out
        assert out[0].endswith("wall 75s")

    def test_gitlab_manual_and_running_jobs_are_listed_but_cost_nothing(
        self, invoke: Callable[..., Result]
    ) -> None:
        out = invoke("report", str(GITLAB_DATA), "2001").out.splitlines()

        assert "  start      -   end      -   dur      -   manual  release" in out
        assert "  start     80s  end      -   dur      -   running  smoke" in out
        assert "  runner time total 250s (4.2 min)" in out
        assert (
            "  billed estimate 4.17 compute min (duration / 60 x cost factor 1, not rounded)" in out
        )

    def test_gitlab_manual_and_running_jobs_are_not_executed_in_a_comparison(
        self, invoke: Callable[..., Result]
    ) -> None:
        out = invoke("compare", str(GITLAB_DATA), "2001", "2001").out

        assert value_of(out, "jobs executed") == "3 -> 3"
        assert value_of(out, "runner time, exact") == "4.2 min -> 4.2 min, +0.0 min (+0.0%)"
        assert table_after(out, PER_JOB_HEADER) == [
            "        60        60        +0  build",
            "       150       150        +0  test",
            "         -         -         -  deploy",
            "         -         -         -  notify",
            "         -         -         -  release",
            "         -         -         -  smoke",
        ]

    def test_report_is_identical_on_every_run(self, invoke: Callable[..., Result]) -> None:
        first = invoke("report", str(GITLAB_DATA), "2001")
        second = invoke("report", str(GITLAB_DATA), "2001")

        assert first == second

    def test_timestamps_with_offsets_and_fractions_are_compared_as_instants(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        run = gh_run(5)
        run["run_started_at"] = "2026-02-01T02:00:00+02:00"
        job = gh_job(1, "j", 0, 0)
        job["started_at"] = "2026-02-01T00:00:10.500Z"
        job["completed_at"] = "2026-02-01T00:01:10.500Z"
        write_run(tmp_path, run, gh_jobs(job))

        lines = invoke("report", str(tmp_path), "5").out.splitlines()

        assert "  start     10s  end     70s  dur     60s  success  j" in lines
        assert "  billed estimate 1 min (each job rounded up to a whole minute)" in lines


class TestReportInputErrors:
    def test_missing_run_file_exits_2_and_names_the_file(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "missing file" in result.err
        assert "run-42.json" in result.err
        assert "run fetch first" in result.err
        assert result.out == ""

    def test_missing_jobs_file_exits_2(self, tmp_path: Path, invoke: Callable[..., Result]) -> None:
        (tmp_path / "run-42.json").write_text(json.dumps(gh_run(42)))

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "jobs-42.json" in result.err

    @pytest.mark.parametrize("content", ["", "{not json"])
    def test_invalid_json_exits_2_and_names_the_file(
        self, tmp_path: Path, invoke: Callable[..., Result], content: str
    ) -> None:
        (tmp_path / "run-42.json").write_text(content)
        (tmp_path / "jobs-42.json").write_text(json.dumps(gh_jobs()))

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "run-42.json" in result.err

    def test_run_file_that_is_neither_github_nor_gitlab_exits_2(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, {"id": 42, "status": "completed"}, gh_jobs())

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "neither a GitHub workflow run nor a GitLab pipeline" in result.err

    @pytest.mark.parametrize(
        "run_doc", [[], "text", 5, None], ids=["array", "string", "number", "null"]
    )
    def test_run_file_that_is_not_an_object_exits_2(
        self, tmp_path: Path, invoke: Callable[..., Result], run_doc: object
    ) -> None:
        (tmp_path / "run-42.json").write_text(json.dumps(run_doc))
        (tmp_path / "jobs-42.json").write_text(json.dumps(gh_jobs()))

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "cannot read run 42" in result.err

    def test_job_timestamp_that_is_not_iso_exits_2_naming_the_field(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        job = gh_job(1, "j", 0, 10)
        job["started_at"] = "yesterday"
        write_run(tmp_path, gh_run(42), gh_jobs(job))

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "started_at" in result.err

    def test_job_without_an_id_exits_2(self, tmp_path: Path, invoke: Callable[..., Result]) -> None:
        job = gh_job(1, "j", 0, 10)
        del job["id"]
        write_run(tmp_path, gh_run(42), gh_jobs(job))

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2
        assert "'id'" in result.err

    def test_corrupt_sections_file_exits_2(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gl_run(42), [gl_job(1, "j", 0, 10)], sections=[1, 2])

        result = invoke("report", str(tmp_path), "42")

        assert result.code == 2

    def test_directory_that_does_not_exist_exits_2(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("report", str(tmp_path / "nope"), "1")

        assert result.code == 2

    @pytest.mark.parametrize("run_id", ["0", "-1", "abc", "1.5", "../1", ""])
    def test_run_id_must_be_a_positive_integer(self, tmp_path: Path, run_id: str) -> None:
        with pytest.raises(SystemExit) as info:
            crt.main(["report", str(tmp_path), run_id], FakeCli(), both)

        assert info.value.code == 2


class TestCompare:
    def test_difference_block_pins_totals_phases_and_per_job_table(
        self, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("compare", str(GITHUB_DATA), "1001", "1002")

        assert result.code == 0
        assert cli.calls == []
        assert table_after(result.out, "== difference 1001 -> 1002") == [
            "  wall clock:                           75s -> 152s, +77s (+102.7%)",
            "  runner time, exact:                   5.7 min -> 3.5 min, -2.2 min (-38.2%)",
            "  billed estimate:                      7 min -> 5 min, -2 min (-28.6%)",
            "  rounding slack (billed minus exact):  1.3 min -> 1.5 min, +0.2 min (+12.5%)",
            "  jobs executed:                        3 -> 3",
            "  jobs split into phases:               3 of 3 -> 2 of 3",
            "  set-up before the work:               42s -> 10s, -32s (-76.2%)",
            "  the work:                             278s -> 170s, -108s (-38.8%)",
            "  after the work:                       20s -> 10s, -10s (-50.0%)",
            "  per job (duration of the latest attempt):",
            PER_JOB_HEADER,
            "        70        40       -30  lint",
            "       210       150       -60  test",
            "         -         -         -  deploy",
            "         -         -         -  never-started",
            "         -        20         -  docs",
        ]

    def test_compare_prints_both_reports_before_the_difference(
        self, invoke: Callable[..., Result]
    ) -> None:
        compare = invoke("compare", str(GITHUB_DATA), "1001", "1002").out
        base = invoke("report", str(GITHUB_DATA), "1001").out
        new = invoke("report", str(GITHUB_DATA), "1002").out

        assert compare.startswith(base + new)

    def test_gitlab_phases_ignore_nested_sections_and_split_on_runner_sections(
        self, invoke: Callable[..., Result]
    ) -> None:
        out = invoke("compare", str(GITLAB_DATA), "2001", "2001").out

        assert value_of(out, "jobs split into phases") == "3 of 3 -> 3 of 3"
        assert value_of(out, "set-up before the work") == "18s -> 18s, +0s (+0.0%)"
        assert value_of(out, "the work") == "213s -> 213s, +0s (+0.0%)"
        assert value_of(out, "after the work") == "19s -> 19s, +0s (+0.0%)"
        assert value_of(out, "billed estimate") == "4.17 min -> 4.17 min, +0.00 min (+0.0%)"

    def test_nested_section_is_never_taken_for_the_work_of_a_job(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        start = int(ANCHOR.timestamp())
        sections = {
            "1": [
                {"name": "prepare_executor", "start": start, "end": start + 5, "depth": 0},
                {"name": "docker_pull", "start": start + 1, "end": start + 4, "depth": 1},
                {
                    "name": "cleanup_file_variables",
                    "start": start + 5,
                    "end": start + 10,
                    "depth": 0,
                },
            ]
        }
        write_run(tmp_path, gl_run(1), [gl_job(1, "build", 0, 10)], sections)

        out = invoke("compare", str(tmp_path), "1", "1").out

        assert phases_of(out) == (5, 0, 5)

    def test_phases_add_up_to_the_exact_runner_time(self, invoke: Callable[..., Result]) -> None:
        out = invoke("compare", str(GITHUB_DATA), "1001", "1001").out

        assert sum(phases_of(out)) == 340

    def test_job_is_matched_by_name_to_its_latest_attempt_whatever_the_order(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        attempt_one = gh_job(1, "lint", 0, 60, attempt=1, conclusion="failure")
        attempt_two = gh_job(2, "lint", 100, 170, attempt=2)
        write_run(tmp_path, gh_run(1), gh_jobs(attempt_two, attempt_one))
        write_run(tmp_path, gh_run(2), gh_jobs(gh_job(3, "lint", 0, 40)))

        result = invoke("compare", str(tmp_path), "1", "2")

        assert table_after(result.out, PER_JOB_HEADER) == ["        70        40       -30  lint"]

    def test_jobs_present_on_one_side_only_show_a_dash_on_the_other(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        base = gh_jobs(gh_job(1, "old-only", 0, 120), gh_job(2, "both", 0, 60))
        new = gh_jobs(gh_job(3, "both", 0, 90), gh_job(4, "new-only", 0, 30))
        write_run(tmp_path, gh_run(1), base)
        write_run(tmp_path, gh_run(2), new)

        out = invoke("compare", str(tmp_path), "1", "2").out

        assert table_after(out, PER_JOB_HEADER) == [
            "       120         -         -  old-only",
            "        60        90       +30  both",
            "         -        30         -  new-only",
        ]

    def test_skipped_or_unstarted_job_on_either_side_has_no_delta(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        base = gh_jobs(gh_job(1, "x", 0, 60), gh_job(2, "y", None, None, conclusion=None))
        new = gh_jobs(gh_job(3, "x", 0, 0, conclusion="skipped"), gh_job(4, "y", 0, 5))
        write_run(tmp_path, gh_run(1), base)
        write_run(tmp_path, gh_run(2), new)

        out = invoke("compare", str(tmp_path), "1", "2").out

        assert table_after(out, PER_JOB_HEADER) == [
            "        60         -         -  x",
            "         -         5         -  y",
        ]

    def test_comparing_a_run_with_itself_reports_zero_change(
        self, invoke: Callable[..., Result]
    ) -> None:
        out = invoke("compare", str(GITHUB_DATA), "1001", "1001").out

        assert value_of(out, "wall clock") == "75s -> 75s, +0s (+0.0%)"
        assert value_of(out, "billed estimate") == "7 min -> 7 min, +0 min (+0.0%)"
        assert "        70        70        +0  lint" in out.splitlines()

    def test_zero_baseline_has_no_percentage_and_does_not_divide_by_zero(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gh_run(1), gh_jobs())
        write_run(tmp_path, gh_run(2), gh_jobs(gh_job(1, "a", 0, 100)))

        result = invoke("compare", str(tmp_path), "1", "2")

        assert result.code == 0
        assert value_of(result.out, "wall clock") == "- -> 100s"
        assert value_of(result.out, "billed estimate") == "0 min -> 2 min, +2 min"
        assert value_of(result.out, "runner time, exact") == "0.0 min -> 1.7 min, +1.7 min"
        assert value_of(result.out, "jobs executed") == "0 -> 1"
        assert value_of(result.out, "jobs split into phases") == "0 of 0 -> 0 of 1"

    def test_comparing_across_providers_works_and_uses_two_billed_decimals(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gh_run(1), gh_jobs(gh_job(1, "a", 0, 100)))
        write_run(tmp_path, gl_run(2), [gl_job(1, "a", 0, 100)])

        result = invoke("compare", str(tmp_path), "1", "2")

        assert result.code == 0
        billed = value_of(result.out, "billed estimate")
        assert billed == "2.00 min -> 1.67 min, -0.33 min (-16.7%)"

    @pytest.mark.parametrize(
        ("steps", "expected"),
        [
            pytest.param(
                [
                    ("Set up job", 0, 5),
                    ("Run actions/checkout@v4", 5, 8),
                    ("Run make a", 8, 20),
                    ("Run actions/cache@v4", 20, 22),
                    ("Run make b", 22, 40),
                    ("Post Run actions/checkout@v4", 40, 41),
                    ("Complete job", 41, 45),
                ],
                (8, 32, 5),
                id="an action step between work steps belongs to the work",
            ),
            pytest.param(
                [
                    ("Run make b", 22, 40),
                    ("Complete job", 41, 45),
                    ("Set up job", 0, 5),
                    ("Run make a", 8, 20),
                    ("Run actions/checkout@v4", 5, 8),
                ],
                (8, 32, 5),
                id="steps listed out of order are sorted by start",
            ),
            pytest.param(
                [
                    ("Set up job", 0, 5),
                    ("Run make", 5, 40),
                    ("Run actions/upload-artifact@v4", 40, 43),
                    ("Complete job", 43, 45),
                ],
                (5, 35, 5),
                id="a trailing action step is after the work",
            ),
            pytest.param(
                [("Set up job", 0, 3), ("Run make", 10, 40), ("Complete job", 40, 45)],
                (10, 30, 5),
                id="a gap before the first work step counts as set-up",
            ),
        ],
    )
    def test_github_phases_split_a_job_at_its_work_steps(
        self,
        tmp_path: Path,
        invoke: Callable[..., Result],
        steps: list[tuple[str, int, int]],
        expected: tuple[int, int, int],
    ) -> None:
        write_run(tmp_path, gh_run(1), gh_jobs(gh_job(1, "j", 0, 45, steps=gh_steps(steps))))

        out = invoke("compare", str(tmp_path), "1", "1").out

        assert phases_of(out) == expected
        assert sum(expected) == 45

    @pytest.mark.parametrize(
        ("steps", "expected"),
        [
            pytest.param(
                [("Set up job", 0, 5), ("Complete job", 5, 45)],
                (5, 0, 40),
                id="set-up ends at the last set-up step, the rest is after the work",
            ),
            pytest.param(
                [
                    ("Set up job", 0, 5),
                    ("Run actions/checkout@v4", 5, 9),
                    ("Post Run actions/checkout@v4", 9, 10),
                    ("Complete job", 10, 45),
                ],
                (9, 0, 36),
                id="set-up includes leading action steps",
            ),
            pytest.param([("Run make", 0, 45)], (0, 45, 0), id="one step spanning the job"),
        ],
    )
    def test_phases_never_lose_or_invent_time(
        self,
        tmp_path: Path,
        invoke: Callable[..., Result],
        steps: list[tuple[str, int, int]],
        expected: tuple[int, int, int],
    ) -> None:
        write_run(tmp_path, gh_run(1), gh_jobs(gh_job(1, "j", 0, 45, steps=gh_steps(steps))))

        out = invoke("compare", str(tmp_path), "1", "1").out

        assert phases_of(out) == expected
        assert sum(expected) == 45

    def test_job_without_steps_is_not_split_into_phases(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        write_run(tmp_path, gh_run(1), gh_jobs(gh_job(1, "j", 0, 45)))

        out = invoke("compare", str(tmp_path), "1", "1").out

        assert value_of(out, "jobs split into phases") == "0 of 1 -> 0 of 1"
        assert sum(phases_of(out)) == 0

    def test_step_without_timestamps_does_not_distort_the_phases(
        self, tmp_path: Path, invoke: Callable[..., Result]
    ) -> None:
        steps = [
            gh_step(1, "Set up job", 0, 5),
            gh_step(2, "Run make", 5, 40),
            gh_skipped_step(3, "Run deploy"),
            gh_step(4, "Complete job", 40, 45),
        ]
        write_run(tmp_path, gh_run(1), gh_jobs(gh_job(1, "j", 0, 45, steps=steps)))

        out = invoke("compare", str(tmp_path), "1", "1").out

        assert phases_of(out) == (5, 35, 5)

    def test_missing_second_run_exits_2_and_prints_nothing(
        self, invoke: Callable[..., Result]
    ) -> None:
        result = invoke("compare", str(GITHUB_DATA), "1001", "9999")

        assert result.code == 2
        assert "run-9999.json" in result.err
        assert result.out == ""

    def test_both_runs_are_read_offline(self, cli: FakeCli, invoke: Callable[..., Result]) -> None:
        invoke("compare", str(GITLAB_DATA), "2001", "2001")

        assert cli.calls == []


class TestReadOnlyGuarantee:
    def test_every_subcommand_on_both_providers_issues_only_get_requests(
        self, tmp_path: Path, cli: FakeCli, invoke: Callable[..., Result]
    ) -> None:
        github_ready(cli)
        serve_github_run(cli, 1001)
        cli.on("gh", "api", stdout=TestHistory.github_page(1, 2))
        assert invoke("history", "--branch", "main", "--limit", "2").code == 0
        assert invoke("fetch", "--out", str(tmp_path / "gh"), "1001").code == 0
        assert invoke("report", str(GITHUB_DATA), "1001").code == 0
        assert invoke("compare", str(GITHUB_DATA), "1001", "1002").code == 0

        gitlab_cli = FakeCli()
        gitlab_ready(gitlab_cli)
        serve_gitlab_pipeline(gitlab_cli)
        gitlab_cli.on("glab", "api", stdout="[]")
        assert crt.main(["history", "--branch", "main"], gitlab_cli, both) == 0
        argv = ["fetch", "--sections", "--out", str(tmp_path / "gl"), "2001"]
        assert crt.main(argv, gitlab_cli, both) == 0

        api_calls = [call for fake in (cli, gitlab_cli) for call in fake.calls if call[1] == "api"]
        assert len(api_calls) >= 8
        assert_read_only(cli.calls)
        assert_read_only(gitlab_cli.calls)
        assert all(call[call.index("--method") + 1] == "GET" for call in api_calls)

    @pytest.mark.parametrize(
        "call",
        [
            ("gh", "run", "rerun", "1"),
            ("gh", "run", "cancel", "1"),
            ("gh", "run", "view", "1"),
            ("gh", "workflow", "run", "ci.yml"),
            ("glab", "ci", "run"),
            ("glab", "ci", "retry", "1"),
            ("gh", "api", "--hostname", "h", "repos/o/r/actions/runs/1/rerun"),
            ("gh", "api", "--hostname", "h", "--method", "POST", "repos/o/r/actions/runs/1/rerun"),
            ("gh", "api", "--hostname", "h", "--method", "GET", "--method", "POST", "x"),
            ("gh", "api", "--hostname", "h", "-X", "DELETE", "--method", "GET", "x"),
            ("glab", "api", "--hostname", "h", "--method", "GET", "-f", "a=b", "x"),
            ("glab", "api", "--hostname", "h", "--method", "GET", "--input", "f.json", "x"),
            ("git", "push", "origin", "main"),
            ("curl", "-X", "POST", "https://example.com"),
        ],
    )
    def test_the_guard_used_here_rejects_anything_that_could_change_remote_state(
        self, call: tuple[str, ...]
    ) -> None:
        with pytest.raises(AssertionError):
            assert_read_only([call])


class TestCommandLine:
    @staticmethod
    def run_script(*argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *argv],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_script_runs_standalone_and_prints_the_stored_report(self) -> None:
        result = self.run_script("report", str(GITHUB_DATA), "1001")

        assert result.returncode == 0
        assert result.stdout.splitlines()[0] == "== run 1001 abc1234 success wall 75s"
        assert result.stderr == ""

    def test_missing_file_exit_status_reaches_the_shell(self, tmp_path: Path) -> None:
        result = self.run_script("report", str(tmp_path), "1")

        assert result.returncode == 2
        assert result.stderr.startswith("ci_run_timings: error: missing file")

    @pytest.mark.parametrize("argv", [(), ("nonsense",), ("fetch",), ("report", "dir")])
    def test_bad_command_line_exits_2(self, argv: tuple[str, ...]) -> None:
        assert self.run_script(*argv).returncode == 2

    @pytest.mark.parametrize("command", ["history", "fetch", "report", "compare"])
    def test_help_of_every_subcommand_prints_and_exits_0(self, command: str) -> None:
        result = self.run_script(command, "--help")

        assert result.returncode == 0
        assert "usage:" in result.stdout

    def test_top_level_help_documents_the_exit_codes(self) -> None:
        result = self.run_script("--help")

        assert result.returncode == 0
        assert "Exit status" in result.stdout
