from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bash_decision_gate as bdg
from _claude_lib import hooks

if TYPE_CHECKING:
    pass


# Fixed working directory used in tests; resolves to itself so cwd-relative
# checks (write-escape) treat it as the workspace root.
TEST_CWD = "/Users/test/project"

# Settings.json allow patterns mirroring a representative subset of the real
# global config. Tests exercise both standalone and compound matching.
DEFAULT_ALLOW = [
    "grep *",
    "rg *",
    "cat *",
    "head *",
    "tail *",
    "ls *",
    "ls",
    "wc *",
    "find . *",
    "find .",
    "date",
    "echo *",
    "git status *",
    "git status",
    "git log *",
    "git diff *",
    "git diff",
    "git show *",
    "git commit *",
    "git add *",
    "git push origin *",
    "git -C *",
    "make *",
    "make",
    "mkdir *",
    "touch *",
    "rm *",
    "cp *",
    "mv *",
    "sed *",
    "go test *",
    "go build *",
    "pytest *",
]


@pytest.fixture(autouse=True)
def _stub_current_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin git branch to a non-protected name so commit/merge rules don't fire
    on the test environment's branch."""
    monkeypatch.setattr(bdg, "_current_branch", lambda: "feature-test")


@pytest.fixture(autouse=True)
def _silence_telemetry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect telemetry path to tmp_path so tests don't write to real $HOME."""
    out_root = tmp_path / "missed_approvals"

    def _fake_path() -> Path:
        return out_root / "2030" / "01" / "01" / "12.jsonl"

    monkeypatch.setattr(bdg, "_telemetry_path", _fake_path)
    return out_root


def _eval(cmd: str, *, allow: list[str] | None = None, cwd: str = TEST_CWD) -> bdg.Decision:
    return bdg.evaluate(
        cmd,
        cwd,
        allowed_dirs=[],
        settings_allow=allow if allow is not None else DEFAULT_ALLOW,
    )


# ============================================================
# Phase 1 — deny rules (smoke through evaluate)
# ============================================================


def test_rm_rf_outside_safe_denies() -> None:
    d = _eval("rm -rf /var/anywhere")
    assert d.behavior == "deny"
    assert d.rule == "rm-rf"


def test_rm_rf_inside_node_modules_passes_phase1() -> None:
    d = _eval("rm -rf ./node_modules")
    assert d.behavior == "allow"


def test_rm_rf_inside_tmp_passes_phase1() -> None:
    d = _eval("rm -rf /tmp/scratch")
    assert d.behavior == "allow"


def test_force_push_denies() -> None:
    d = _eval("git push --force origin feature-test")
    assert d.behavior == "deny"
    assert d.rule == "force-push"


def test_push_to_protected_denies() -> None:
    d = _eval("git push origin main")
    assert d.behavior == "deny"
    assert d.rule == "push-to-protected"


def test_reset_hard_denies() -> None:
    d = _eval("git reset --hard HEAD~1")
    assert d.behavior == "deny"
    assert d.rule == "git-reset-hard"


def test_commit_amend_denies() -> None:
    d = _eval("git commit --amend")
    assert d.behavior == "deny"
    assert d.rule == "amend"


def test_no_verify_denies() -> None:
    d = _eval('git commit --no-verify -m "fix"')
    assert d.behavior == "deny"
    assert d.rule == "no-verify"


def test_heredoc_denies() -> None:
    d = _eval("cat <<EOF\nhi\nEOF")
    assert d.behavior == "deny"
    assert d.rule == "heredoc"


def test_destructive_sql_denies() -> None:
    d = _eval("psql -c 'DROP TABLE users'")
    assert d.behavior == "deny"
    assert d.rule == "destructive-sql"


# ============================================================
# Phase 2(a) — interpreter inline-exec
# ============================================================


@pytest.mark.parametrize(
    "cmd",
    [
        "python -c 'print(1)'",
        "python3 -c 'print(1)'",
        "node -e 'console.log(1)'",
        "ruby -e 'p 1'",
        "perl -e 'print 1'",
        "python -m http.server",
    ],
)
def test_interp_inline_exec_denies(cmd: str) -> None:
    d = _eval(cmd)
    assert d.behavior == "deny"
    assert d.rule == "interp-inline-exec"
    assert "claude_written_scripts" in (d.reason or "")


@pytest.mark.parametrize("cmd", ['eval "$x"', "exec /bin/sh", "source ./script.sh", ". ./x.sh"])
def test_eval_exec_source_denies(cmd: str) -> None:
    d = _eval(cmd)
    assert d.behavior == "deny"
    assert d.rule == "interp-dot-source"


# ============================================================
# Phase 2(b) — shell inline-exec (recursive)
# ============================================================


def test_bash_c_safe_inner_allows() -> None:
    d = _eval("bash -c 'grep foo file'")
    assert d.behavior == "allow"


def test_bash_c_secret_inner_denies() -> None:
    d = _eval("bash -c 'cat /etc/shadow'")
    assert d.behavior == "deny"
    assert d.rule == "secret-path"


def test_bash_c_write_escape_inner_denies() -> None:
    d = _eval("bash -c 'rm /etc/foo'")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_sh_c_safe_inner_allows() -> None:
    d = _eval("sh -c 'ls -la'")
    assert d.behavior == "allow"


def test_xargs_into_python_dash_c_denies() -> None:
    d = _eval("echo hi | xargs python -c 'print(1)'")
    assert d.behavior == "deny"
    assert d.rule == "interp-inline-exec"


def test_xargs_into_safe_sh_c_allows() -> None:
    d = _eval("echo hi | xargs sh -c 'echo {}'")
    # The inner `echo {}` should pass. Outer xargs may or may not be in allow.
    # If not in allow → defer; if defer that's also acceptable for this case.
    assert d.behavior in ("allow", "defer")


# ============================================================
# Phase 2(c) — system-protected paths
# ============================================================


@pytest.mark.parametrize(
    "cmd",
    [
        "cat /etc/shadow",
        "cat /etc/sudoers",
        "cat ~/.ssh/id_rsa",
        "grep root ~/.ssh/config",
        "head ~/.aws/credentials",
        "tail ~/.gnupg/private-keys-v1.d/0123.key",
        "cat ~/.password-store/foo.gpg",
    ],
)
def test_secret_paths_deny(cmd: str) -> None:
    d = _eval(cmd)
    assert d.behavior == "deny"
    assert d.rule == "secret-path"


def test_pem_files_deny() -> None:
    d = _eval("cat ./cert.pem")
    assert d.behavior == "deny"
    assert d.rule == "secret-path"


def test_etc_passwd_is_not_secret() -> None:
    # /etc/passwd is world-readable and not on the denylist.
    d = _eval("cat /etc/passwd")
    assert d.behavior == "allow"


# ============================================================
# Phase 2(d) — audit-dir protection
# ============================================================


def test_rm_in_audit_dir_denies() -> None:
    d = _eval("rm ./.claude/claude_written_scripts/old.py")
    assert d.behavior == "deny"
    assert d.rule == "audit-dir"


def test_redirect_into_audit_dir_denies() -> None:
    d = _eval("echo hi > ./.claude/claude_written_scripts/foo.sh")
    assert d.behavior == "deny"
    assert d.rule == "audit-dir"


def test_writing_new_file_to_audit_dir_via_tee_denies() -> None:
    d = _eval("echo content | tee ./.claude/claude_written_scripts/x.sh")
    assert d.behavior == "deny"
    assert d.rule == "audit-dir"


def test_creating_audit_dir_file_via_mkdir_outside_does_not_fire() -> None:
    # mkdir doesn't write a target inside audit dir; create unrelated dir.
    d = _eval("mkdir build")
    assert d.behavior == "allow"


# ============================================================
# Phase 2(e) — write-escape
# ============================================================


def test_rm_within_cwd_allows() -> None:
    d = _eval("rm file.txt")
    assert d.behavior == "allow"


def test_rm_outside_cwd_denies() -> None:
    d = _eval("rm /etc/foo")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_mkdir_outside_cwd_denies() -> None:
    d = _eval("mkdir /opt/x")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_mkdir_in_tmp_allows() -> None:
    d = _eval("mkdir /tmp/x")
    assert d.behavior == "allow"


def test_sed_inplace_within_cwd_allows() -> None:
    d = _eval("sed -i 's/x/y/' src/main.py")
    assert d.behavior == "allow"


def test_sed_inplace_outside_denies() -> None:
    d = _eval("sed -i 's/x/y/' /etc/hosts")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_find_delete_within_cwd_allows() -> None:
    d = _eval("find . -name '*.tmp' -delete")
    assert d.behavior == "allow"


def test_find_delete_outside_denies() -> None:
    d = _eval("find /etc -delete")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_redirect_outside_denies() -> None:
    d = _eval("echo hi > /etc/foo")
    assert d.behavior == "deny"
    assert d.rule == "write-escape"


def test_redirect_dev_null_allows() -> None:
    d = _eval("grep foo file > /dev/null 2>&1")
    assert d.behavior == "allow"


def test_redirect_in_tmp_allows() -> None:
    d = _eval("ls -la > /tmp/listing.txt")
    assert d.behavior == "allow"


# ============================================================
# cwd shifts
# ============================================================


def test_cd_prefix_shifts_cwd_for_following_commands() -> None:
    # cd /tmp && rm file → effective_cwd for rm = /tmp → write within /tmp ok
    d = _eval("cd /tmp && rm subdir/file")
    assert d.behavior == "allow"


def test_git_dash_c_shifts_cwd_for_that_command() -> None:
    d = _eval("git -C /tmp/other-repo log")
    # log is read — passes (e) regardless of cwd, but must match allow pattern.
    # `git -C *` is in DEFAULT_ALLOW.
    assert d.behavior == "allow"


# ============================================================
# Pipe / list / recursion
# ============================================================


def test_pipe_of_safe_commands_allows() -> None:
    d = _eval("grep foo file | head -20")
    assert d.behavior == "allow"


def test_multi_pipe_allows() -> None:
    d = _eval("cat file | grep foo | sort | uniq -c | head")
    # uniq -c lacks an explicit allow pattern in our minimal set → may defer.
    # Accept allow OR defer (the point is no deny on what's clearly read-only).
    assert d.behavior in ("allow", "defer")


def test_pipe_with_one_unsafe_segment_denies() -> None:
    d = _eval("grep foo file | python -c 'print(1)'")
    assert d.behavior == "deny"
    assert d.rule == "interp-inline-exec"


def test_command_subst_safe_allows() -> None:
    d = _eval('grep "$(date)" log')
    assert d.behavior == "allow"


def test_command_subst_unsafe_inner_denies() -> None:
    d = _eval('grep "$(cat /etc/shadow)" log')
    assert d.behavior == "deny"
    assert d.rule == "secret-path"


def test_process_subst_safe_allows() -> None:
    d = _eval("diff <(cat a) <(cat b)")
    # diff isn't in DEFAULT_ALLOW. Should defer (not deny).
    assert d.behavior in ("allow", "defer")


# ============================================================
# Phase 3 — positive allow / defer
# ============================================================


def test_unknown_command_defers() -> None:
    d = _eval("apt list --installed")
    assert d.behavior == "defer"


def test_safe_command_without_allow_pattern_defers() -> None:
    # 'jq' not in our minimal allow list → defer (not deny).
    d = _eval("jq '.foo' data.json")
    assert d.behavior == "defer"


# ============================================================
# Parse errors → defer
# ============================================================


def test_unterminated_quote_defers() -> None:
    d = _eval("grep 'unterminated file")
    assert d.behavior == "defer"


def test_arithmetic_expansion_defers() -> None:
    # bashlex raises NotImplementedError on $(()).
    d = _eval("echo $((1+2))")
    assert d.behavior == "defer"


def test_empty_command_defers_via_parse_failure() -> None:
    # Empty string short-circuits in main(), not evaluate(); evaluate() with
    # empty input goes through parse and returns defer.
    d = _eval("")
    assert d.behavior == "defer"


# ============================================================
# Telemetry
# ============================================================


def test_deny_writes_telemetry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "tele.jsonl"
    monkeypatch.setattr(bdg, "_telemetry_path", lambda: out)
    bdg.log_miss("rm /etc/foo", TEST_CWD, "deny", "write-escape")
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["cmd"] == "rm /etc/foo"
    assert rec["reason"] == "deny"
    assert rec["details"] == "write-escape"
    assert rec["cwd"] == TEST_CWD


def test_telemetry_path_shards_by_utc_hour() -> None:
    p = bdg._telemetry_path()
    # state/missed_approvals/YYYY/MM/DD/HH.jsonl
    parts = p.parts
    assert "missed_approvals" in parts
    idx = parts.index("missed_approvals")
    assert len(parts[idx + 1]) == 4  # YYYY
    assert len(parts[idx + 2]) == 2  # MM
    assert len(parts[idx + 3]) == 2  # DD
    assert parts[idx + 4].endswith(".jsonl")
    assert len(parts[idx + 4].removesuffix(".jsonl")) == 2  # HH


def test_telemetry_failure_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    # Point at a path that can't be created (under /proc on linux, or under a file).
    monkeypatch.setattr(bdg, "_telemetry_path", lambda: Path("/proc/cannot/write/here.jsonl"))
    # Should not raise.
    bdg.log_miss("x", "y", "deny", "z")


# ============================================================
# Main entry point — JSON IO
# ============================================================


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
) -> tuple[int, str, str]:
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    rc = bdg.main()
    return rc, stdout.getvalue(), stderr.getvalue()


def test_main_non_bash_tool_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, stdout, stderr = _run_main(monkeypatch, {"tool_name": "Read"})
    assert rc == hooks.ALLOW
    assert stdout == ""


def test_main_empty_command_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    rc, stdout, _ = _run_main(
        monkeypatch,
        {"tool_name": "Bash", "tool_input": {"command": ""}},
    )
    assert rc == hooks.ALLOW
    assert stdout == ""


def test_main_safe_command_emits_allow_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Stub the settings loaders to provide a known allow set.
    monkeypatch.setattr(bdg, "_load_bash_allow_patterns", lambda: DEFAULT_ALLOW)
    monkeypatch.setattr(bdg, "_load_allowed_dirs", list)
    rc, stdout, _ = _run_main(
        monkeypatch,
        {
            "tool_name": "Bash",
            "tool_input": {"command": "grep foo file | head -20"},
            "cwd": TEST_CWD,
        },
    )
    assert rc == hooks.ALLOW
    payload = json.loads(stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_main_unsafe_command_emits_deny_json_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bdg, "_load_bash_allow_patterns", lambda: DEFAULT_ALLOW)
    monkeypatch.setattr(bdg, "_load_allowed_dirs", list)
    rc, stdout, stderr = _run_main(
        monkeypatch,
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python -c 'print(1)'"},
            "cwd": TEST_CWD,
        },
    )
    assert rc == hooks.BLOCK
    assert "BLOCKED" in stderr
    payload = json.loads(stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "claude_written_scripts" in payload["hookSpecificOutput"]["permissionDecisionReason"]


# ============================================================
# settings.json loaders
# ============================================================


def test_load_bash_allow_patterns_extracts_bash_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "permissions": {
                    "allow": [
                        "Bash(grep *)",
                        "Bash(ls)",
                        "Read",
                        "WebSearch",
                        "mcp__*",
                    ],
                    "deny": ["Bash(rm *)"],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(fake_home))
    patterns = bdg._load_bash_allow_patterns()
    assert "grep *" in patterns
    assert "ls" in patterns
    assert "Read" not in patterns
    assert "rm *" not in patterns


def test_load_allowed_dirs_returns_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "permissions": {
                    "allowedDirectories": ["/Users/me/scratch", "~/Downloads"],
                    "allow": [],
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(fake_home))
    dirs = bdg._load_allowed_dirs()
    assert dirs == ["/Users/me/scratch", "~/Downloads"]


def test_load_allowed_dirs_empty_when_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert bdg._load_allowed_dirs() == []


def test_allowed_dirs_extend_writable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    d = bdg.evaluate(
        "mkdir " + str(scratch / "new"),
        TEST_CWD,
        allowed_dirs=[str(scratch)],
        settings_allow=DEFAULT_ALLOW,
    )
    assert d.behavior == "allow"


# ============================================================
# walk_commands traversal details
# ============================================================


def test_walk_commands_yields_one_segment_per_simple_command() -> None:
    trees, err = bdg.parse_safely("grep foo file")
    assert err is None and trees is not None
    segs = list(bdg.walk_commands(trees[0], Path(TEST_CWD)))
    assert len(segs) == 1


def test_walk_commands_yields_three_for_pipeline() -> None:
    trees, err = bdg.parse_safely("a | b | c")
    assert err is None and trees is not None
    segs = list(bdg.walk_commands(trees[0], Path(TEST_CWD)))
    assert len(segs) == 3


def test_walk_commands_recurses_into_command_substitution() -> None:
    trees, err = bdg.parse_safely('echo "$(date +%Y)"')
    assert err is None and trees is not None
    segs = list(bdg.walk_commands(trees[0], Path(TEST_CWD)))
    argv_heads = [bdg._extract_argv(s)[0] for s, _ in segs if bdg._extract_argv(s)]
    assert "echo" in argv_heads
    assert "date" in argv_heads


def test_walk_commands_cd_shift_applies_to_next_command() -> None:
    trees, err = bdg.parse_safely("cd /opt && rm /opt/foo")
    assert err is None and trees is not None
    segs = list(bdg.walk_commands(trees[0], Path("/start")))
    # First segment (cd) — cwd is the starting cwd
    # Second segment (rm) — cwd shifted to /opt
    assert len(segs) == 2
    _cd_node, cd_cwd = segs[0]
    rm_node, rm_cwd = segs[1]
    assert str(cd_cwd) == "/start"
    assert str(rm_cwd) == "/opt"
