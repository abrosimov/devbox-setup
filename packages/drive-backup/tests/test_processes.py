from __future__ import annotations

from drive_backup.processes import Process, find_busy, list_processes

PROCS = [
    Process(10, "/Users/u/.local/bin/claude --resume"),
    Process(11, "node /opt/homebrew/bin/gemini"),
    Process(12, "/usr/bin/vim claude.md"),
    Process(13, "claude-helper"),
    Process(99, "/x/drive-backup run claude"),
]


def test_matches_argv0_and_interpreted_script() -> None:
    busy = find_busy(["claude", "gemini"], lambda: PROCS, own_pid=99)
    assert [p.pid for p in busy] == [10, 11]


def test_argv1_of_editor_is_a_false_positive_only_for_exact_names() -> None:
    # `vim claude.md` has argv[1] "claude.md", which is not "claude".
    assert find_busy(["claude"], lambda: PROCS[2:4], own_pid=99) == []


def test_empty_names_never_lists() -> None:
    def boom() -> list[Process]:
        raise AssertionError("lister must not be called")

    assert find_busy([], boom) == []


def test_real_ps_lists_this_process() -> None:
    import os

    assert any(p.pid == os.getpid() for p in list_processes())
