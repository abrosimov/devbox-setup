import subprocess
import sys
from pathlib import Path

import pytest

from commit_topics import Topic, assign_files, main

STRAY_LOG = "tla/nvim/nvim.log"
TOPICS = (
    Topic("Add TLA", ("tla", f":(exclude){STRAY_LOG}")),
    Topic("Calibrate docs", ("docs",)),
    Topic("Everything else", (".", f":(exclude){STRAY_LOG}")),
)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def commit_changes(repo: Path, rev: str) -> list[str]:
    output = git(repo, "diff-tree", "--no-commit-id", "-r", "-M", "--name-status", rev)
    return sorted(output.splitlines())


def snapshot(repo: Path) -> tuple[str, str, str]:
    return (
        git(repo, "rev-parse", "HEAD"),
        git(repo, "status", "--porcelain", "--untracked-files=all"),
        git(repo, "diff", "--cached", "--name-status"),
    )


@pytest.fixture
def remote_and_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    global_config = tmp_path / "gitconfig"
    global_config.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")

    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", "--bare", "-b", "master", str(remote))
    git(tmp_path, "init", "-q", "-b", "master", str(repo))
    for relative in ("tla/a.txt", "docs/b.md", "other/old.txt", "other/gone.txt"):
        write(repo, relative, f"{relative}\n" * 5)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "initial")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "origin", "master")

    write(repo, "tla/a.txt", "changed\n")
    write(repo, "tla/nvim/new.lua", "lua\n")
    write(repo, "docs/b.md", "changed\n")
    write(repo, "docs/new.md", "new\n")
    write(repo, "other/c.txt", "c\n")
    git(repo, "mv", "other/old.txt", "other/new.txt")
    git(repo, "rm", "-q", "other/gone.txt")
    git(repo, "add", "-A")
    write(repo, STRAY_LOG, "log\n")

    monkeypatch.chdir(repo)
    return remote, repo


def test_assign_files_gives_each_path_to_first_matching_topic() -> None:
    assert assign_files([["a", "b"], ["b", "c"], ["a", "b", "c", "d"]]) == [
        ("a", "b"),
        ("c",),
        ("d",),
    ]


def test_run_creates_three_topic_commits_and_pushes(
    remote_and_repo: tuple[Path, Path],
) -> None:
    remote, repo = remote_and_repo

    assert main([], topics=TOPICS) == 0

    subjects = git(repo, "log", "--format=%s", "-4").splitlines()
    assert subjects == ["Everything else", "Calibrate docs", "Add TLA", "initial"]
    assert commit_changes(repo, "HEAD~2") == ["A\ttla/nvim/new.lua", "M\ttla/a.txt"]
    assert commit_changes(repo, "HEAD~1") == ["A\tdocs/new.md", "M\tdocs/b.md"]
    assert commit_changes(repo, "HEAD") == [
        "A\tother/c.txt",
        "D\tother/gone.txt",
        "R100\tother/old.txt\tother/new.txt",
    ]
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == f"?? {STRAY_LOG}\n"
    assert git(remote, "rev-parse", "master") == git(repo, "rev-parse", "HEAD")


def test_no_push_leaves_remote_untouched(remote_and_repo: tuple[Path, Path]) -> None:
    remote, repo = remote_and_repo
    remote_head = git(remote, "rev-parse", "master")

    assert main(["--no-push"], topics=TOPICS) == 0

    assert git(remote, "rev-parse", "master") == remote_head
    assert len(git(repo, "log", "--format=%s").splitlines()) == 4


def test_topic_without_changes_is_skipped(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, repo = remote_and_repo
    topics = (Topic("Nothing here", ("missing",)), *TOPICS)

    assert main(["--no-push"], topics=topics) == 0

    assert "skipped 'Nothing here'" in capsys.readouterr().out
    assert "Nothing here" not in git(repo, "log", "--format=%s")


def test_dry_run_changes_nothing(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    remote, repo = remote_and_repo
    before = snapshot(repo)
    remote_head = git(remote, "rev-parse", "master")

    assert main(["--dry-run"], topics=TOPICS) == 0

    assert snapshot(repo) == before
    assert git(remote, "rev-parse", "master") == remote_head
    out = capsys.readouterr().out
    assert "[1/3] 'Add TLA': 2 path(s)" in out
    assert "[2/3] 'Calibrate docs': 2 path(s)" in out
    assert "[3/3] 'Everything else': 4 path(s)" in out
    assert STRAY_LOG not in out


def test_refuses_on_other_branch(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, repo = remote_and_repo
    git(repo, "checkout", "-q", "-b", "feature")
    before = snapshot(repo)

    assert main([], topics=TOPICS) == 1

    assert snapshot(repo) == before
    assert "current branch is 'feature'" in capsys.readouterr().err


def test_refuses_when_nothing_staged(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, repo = remote_and_repo
    git(repo, "commit", "-q", "-m", "everything")

    assert main([], topics=TOPICS) == 1

    assert "nothing is staged" in capsys.readouterr().err


def test_refuses_when_tracked_file_has_unstaged_changes(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, repo = remote_and_repo
    write(repo, "docs/b.md", "unstaged edit\n")
    before = snapshot(repo)

    assert main([], topics=TOPICS) == 1

    assert snapshot(repo) == before
    assert "unstaged changes" in capsys.readouterr().err


def test_failing_commit_stops_and_leaves_rest_unstaged(
    remote_and_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    remote, repo = remote_and_repo
    remote_head = git(remote, "rev-parse", "master")
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        f"#!{sys.executable}\n"
        "import subprocess, sys\n"
        "staged = subprocess.run(['git', 'diff', '--cached', '--name-only'],"
        " capture_output=True, text=True).stdout\n"
        "sys.exit(1 if 'docs/' in staged else 0)\n"
    )
    hook.chmod(0o755)

    assert main([], topics=TOPICS) == 1

    err = capsys.readouterr().err
    assert "FAILED: git commit -m 'Calibrate docs'" in err
    assert "committed before the failure" in err
    assert "Nothing was pushed." in err
    assert git(repo, "log", "--format=%s", "-1") == "Add TLA\n"
    assert git(repo, "diff", "--cached", "--name-only") == ""
    assert "docs/new.md" in git(repo, "status", "--porcelain", "--untracked-files=all")
    assert git(remote, "rev-parse", "master") == remote_head
