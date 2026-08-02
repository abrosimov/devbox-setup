#!/usr/bin/env python3
"""Tests for the Phase-1 deny rules (originally in pre_bash_safety_gate).

The rules are now part of bash_decision_gate. This file uses
``evaluate_phase1_legacy`` for the pre-unification Decision shape so the
existing assertion patterns (``decision.blocked``, ``decision.rule_name``,
``decision.message``) work unchanged.

Run from any directory:
    pytest roles/devbox/files/dot_claude/bin/test_pre_bash_safety_gate.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bash_decision_gate as gate

# --- Heredoc ----------------------------------------------------------------


def test_blocks_heredoc() -> None:
    assert gate.evaluate_phase1_legacy("cat << EOF\nhi\nEOF").blocked


def test_blocks_here_string() -> None:
    # Preserves legacy substring-match: <<< also contains '<<'.
    assert gate.evaluate_phase1_legacy("cat <<< hello").blocked


def test_allows_plain_echo() -> None:
    assert not gate.evaluate_phase1_legacy("echo hello").blocked


def test_allows_redirect() -> None:
    assert not gate.evaluate_phase1_legacy("echo hi > file.txt").blocked


# --- Commit on main ---------------------------------------------------------


def test_blocks_commit_on_main() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="main"):
        d = gate.evaluate_phase1_legacy("git commit -m 'wip'")
    assert d.blocked
    assert d.rule_name == "commit-on-main"


def test_blocks_commit_on_master() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="master"):
        assert gate.evaluate_phase1_legacy("git commit").blocked


def test_commit_on_feature_denied_via_generic() -> None:
    # commit-on-main must not fire on a feature branch; git-commit catch-all does.
    with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
        d = gate.evaluate_phase1_legacy("git commit -m 'fix'")
    assert d.blocked
    assert d.rule_name == "git-commit"


# --- Merge on main ----------------------------------------------------------


def test_blocks_merge_into_main() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="main"):
        assert gate.evaluate_phase1_legacy("git merge feature/x").blocked


def test_allows_merge_into_feature() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
        assert not gate.evaluate_phase1_legacy("git merge main").blocked


# --- Force push -------------------------------------------------------------


def test_blocks_force() -> None:
    assert gate.evaluate_phase1_legacy("git push --force").blocked


def test_blocks_force_short_flag() -> None:
    assert gate.evaluate_phase1_legacy("git push -f").blocked


def test_blocks_force_with_origin() -> None:
    assert gate.evaluate_phase1_legacy("git push origin main --force").blocked


def test_blocks_force_equals() -> None:
    assert gate.evaluate_phase1_legacy("git push --force=origin").blocked


def test_force_with_lease_denied_via_generic_not_force_push() -> None:
    # force-push must not fire on --force-with-lease (safer variant); git-push
    # catch-all denies the push itself.
    d = gate.evaluate_phase1_legacy("git push --force-with-lease")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_normal_feature_push_denied_via_generic() -> None:
    d = gate.evaluate_phase1_legacy("git push origin feature/x")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_blocks_refspec_plus_prefix() -> None:
    # "+feature" = force semantics at the refspec layer.
    d = gate.evaluate_phase1_legacy("git push origin +feature")
    assert d.blocked
    assert d.rule_name == "force-push"


def test_blocks_refspec_local_colon_plus_remote() -> None:
    # "local:+main" = force on remote side.
    d = gate.evaluate_phase1_legacy("git push origin local:+main")
    assert d.blocked
    assert d.rule_name == "force-push"


def test_blocks_refspec_plus_local_colon_remote() -> None:
    # "+local:remote" — plus prefix on entire refspec.
    d = gate.evaluate_phase1_legacy("git push origin +feature:other")
    assert d.blocked
    assert d.rule_name == "force-push"


# --- Push mirror / all ------------------------------------------------------


def test_blocks_mirror() -> None:
    d = gate.evaluate_phase1_legacy("git push --mirror origin")
    assert d.blocked
    assert d.rule_name == "push-mirror-all"


def test_blocks_all() -> None:
    d = gate.evaluate_phase1_legacy("git push --all origin")
    assert d.blocked
    assert d.rule_name == "push-mirror-all"


def test_blocks_all_no_remote() -> None:
    assert gate.evaluate_phase1_legacy("git push --all").blocked


def test_normal_push_denied_via_generic() -> None:
    d = gate.evaluate_phase1_legacy("git push origin feature/x")
    assert d.blocked
    assert d.rule_name == "git-push"


# --- Push delete branch -----------------------------------------------------


def test_blocks_delete_flag() -> None:
    d = gate.evaluate_phase1_legacy("git push --delete origin feature/x")
    assert d.blocked
    assert d.rule_name == "push-delete-branch"


def test_blocks_colon_refspec() -> None:
    d = gate.evaluate_phase1_legacy("git push origin :feature/x")
    assert d.blocked
    assert d.rule_name == "push-delete-branch"


def test_blocks_colon_refs_heads_refspec() -> None:
    d = gate.evaluate_phase1_legacy("git push origin :refs/heads/feature/x")
    assert d.blocked
    assert d.rule_name == "push-delete-branch"


def test_normal_refspec_denied_via_generic_not_delete() -> None:
    # local:remote (both sides non-empty) is a normal push, not a delete —
    # push-delete-branch must not fire; git-push catch-all does.
    d = gate.evaluate_phase1_legacy("git push origin local:remote-feature")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_normal_push_denied_via_generic_not_delete() -> None:
    d = gate.evaluate_phase1_legacy("git push origin feature/x")
    assert d.blocked
    assert d.rule_name == "git-push"


# --- Push to protected branches ---------------------------------------------


def test_blocks_bare_main() -> None:
    d = gate.evaluate_phase1_legacy("git push origin main")
    assert d.blocked
    assert d.rule_name == "push-to-protected"
    assert "main" in (d.message or "")


def test_blocks_bare_master() -> None:
    d = gate.evaluate_phase1_legacy("git push origin master")
    assert d.blocked
    assert d.rule_name == "push-to-protected"


def test_blocks_local_colon_main() -> None:
    assert gate.evaluate_phase1_legacy("git push origin foo:main").blocked


def test_blocks_refs_heads_master() -> None:
    d = gate.evaluate_phase1_legacy("git push origin local:refs/heads/master")
    assert d.blocked
    assert d.rule_name == "push-to-protected"


def test_blocks_head_colon_main() -> None:
    d = gate.evaluate_phase1_legacy("git push origin HEAD:main")
    assert d.blocked
    assert d.rule_name == "push-to-protected"


def test_blocks_refs_remotes_origin_main() -> None:
    d = gate.evaluate_phase1_legacy("git push origin local:refs/remotes/origin/main")
    assert d.blocked
    assert d.rule_name == "push-to-protected"


def test_feature_branch_push_denied_via_generic() -> None:
    # Non-protected pushes are now denied by the generic git-push catch-all
    # (Claude never pushes). push-to-protected must NOT fire on a feature ref.
    d = gate.evaluate_phase1_legacy("git push origin feature/x")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_set_upstream_feature_denied_via_generic() -> None:
    # -u must not confuse positional parsing into hitting push-to-protected.
    d = gate.evaluate_phase1_legacy("git push -u origin feature/x")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_bare_push_denied_via_generic() -> None:
    d = gate.evaluate_phase1_legacy("git push")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_remote_only_push_denied_via_generic() -> None:
    d = gate.evaluate_phase1_legacy("git push origin")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_branch_with_main_substring_hits_generic_not_protected() -> None:
    # "mainline" is NOT main — push-to-protected must not fire; git-push does.
    d = gate.evaluate_phase1_legacy("git push origin mainline")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_branch_with_master_path_hits_generic_not_protected() -> None:
    # "feature/master-cleanup" is NOT master.
    d = gate.evaluate_phase1_legacy("git push origin feature/master-cleanup")
    assert d.blocked
    assert d.rule_name == "git-push"


def test_env_var_extends_protected() -> None:
    # User adds "develop" to protected list via env var.
    with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "main,master,develop"}):
        d = gate.evaluate_phase1_legacy("git push origin develop")
        assert d.blocked
        assert d.rule_name == "push-to-protected"


def test_env_var_wildcard_release() -> None:
    # Wildcard extends the push-to-protected pattern; non-matching branches
    # still get denied — but by the generic git-push catch-all, not the
    # push-to-protected rule.
    with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "main,master,release/*"}):
        d = gate.evaluate_phase1_legacy("git push origin release/1.0")
        assert d.blocked
        assert d.rule_name == "push-to-protected"
        non_matching = gate.evaluate_phase1_legacy("git push origin feature/x")
        assert non_matching.blocked
        assert non_matching.rule_name == "git-push"


def test_env_var_override_removes_default() -> None:
    # User explicitly sets only "develop" — main is no longer *protected*, so
    # push-to-protected does not fire on main; git-push catch-all does.
    with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "develop"}):
        main_push = gate.evaluate_phase1_legacy("git push origin main")
        assert main_push.blocked
        assert main_push.rule_name == "git-push"
        develop_push = gate.evaluate_phase1_legacy("git push origin develop")
        assert develop_push.blocked
        assert develop_push.rule_name == "push-to-protected"


# --- Amend / no-verify ------------------------------------------------------


def test_blocks_amend() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
        assert gate.evaluate_phase1_legacy("git commit --amend").blocked


def test_blocks_amend_with_message() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
        assert gate.evaluate_phase1_legacy("git commit --amend -m 'oops'").blocked


def test_blocks_no_verify() -> None:
    with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
        assert gate.evaluate_phase1_legacy("git commit --no-verify -m 'fix'").blocked


# --- Lint suppression -------------------------------------------------------


def test_blocks_echo_noqa() -> None:
    assert gate.evaluate_phase1_legacy("echo '# noqa: E501' >> file.py").blocked


def test_blocks_sed_ts_ignore() -> None:
    assert gate.evaluate_phase1_legacy("sed -i 's/.*/\\/\\/ ts-ignore/' file.ts").blocked


def test_blocks_cat_pipe_grep_eslint_disable() -> None:
    # Preserves legacy: cat in any pipeline that references suppression.
    assert gate.evaluate_phase1_legacy("cat file | grep eslint-disable").blocked


def test_allows_grep_only() -> None:
    assert not gate.evaluate_phase1_legacy("grep noqa file.py").blocked


def test_allows_clean_lint_run() -> None:
    assert not gate.evaluate_phase1_legacy("ruff check .").blocked


# --- rm -rf -----------------------------------------------------------------


def test_allows_node_modules() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf node_modules").blocked


def test_allows_dotvenv() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf .venv").blocked


def test_allows_dist_build() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf dist build").blocked


def test_allows_nested_node_modules() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf ./packages/app/node_modules").blocked


def test_allows_pycache() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf __pycache__").blocked


def test_allows_tmp() -> None:
    assert not gate.evaluate_phase1_legacy("rm -rf /tmp/foo").blocked


def test_allows_tmpdir_literal() -> None:
    assert not gate.evaluate_phase1_legacy('rm -rf "$TMPDIR/foo"').blocked


def test_blocks_etc() -> None:
    assert gate.evaluate_phase1_legacy("rm -rf /etc/passwd").blocked


def test_blocks_home() -> None:
    assert gate.evaluate_phase1_legacy('rm -rf "$HOME"').blocked


def test_blocks_root() -> None:
    assert gate.evaluate_phase1_legacy("rm -rf /").blocked


def test_blocks_mixed_safe_and_unsafe() -> None:
    # Any unsafe target -> block.
    assert gate.evaluate_phase1_legacy("rm -rf node_modules /etc/foo").blocked


def test_allows_rm_without_force() -> None:
    # rm without both -r and -f is outside this rule's scope.
    assert not gate.evaluate_phase1_legacy("rm node_modules").blocked


def test_allows_rm_r_only() -> None:
    assert not gate.evaluate_phase1_legacy("rm -r node_modules").blocked


def test_allows_rm_f_only() -> None:
    assert not gate.evaluate_phase1_legacy("rm -f file.txt").blocked


# --- Project tmp ------------------------------------------------------------


@pytest.fixture
def project_root(tmp_path: Path) -> Iterator[Path]:
    """Stub project tree with a .git dir, tmp/, and a symlink-escape attack.

    Patches gate.Path.cwd to point at the project root.
    """
    root = tmp_path / "myproj"
    (root / ".git").mkdir(parents=True)
    (root / "tmp").mkdir()
    (root / "tmp" / "render-out").mkdir()
    # Symlink escape attack: tmp/escape -> /etc
    (root / "tmp" / "escape").symlink_to("/etc")
    with mock.patch.object(gate.Path, "cwd", return_value=root):
        yield root
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_allows_rm_inside_project_tmp(project_root: Path) -> None:
    _ = project_root
    d = gate.evaluate_phase1_legacy("rm -rf tmp/render-out")
    assert not d.blocked, d.message


def test_allows_rm_glob_inside_project_tmp(project_root: Path) -> None:
    _ = project_root
    # rm -rf tmp/* expands at shell level; we exercise a concrete child.
    d = gate.evaluate_phase1_legacy("rm -rf tmp/render-out/intermediate")
    assert not d.blocked, d.message


def test_blocks_rm_of_tmp_itself(project_root: Path) -> None:
    _ = project_root
    # We allow contents, not the tmp/ dir itself.
    d = gate.evaluate_phase1_legacy("rm -rf tmp")
    # rm-rf rule may still allow if "tmp" basename happens to match a safe
    # name, but it should NOT match via the project-tmp rule for the dir itself.
    # Confirm: with no .cache/.venv/etc basename, plain "tmp" is unsafe.
    assert d.blocked, d.message


def test_blocks_symlink_escape(project_root: Path) -> None:
    _ = project_root
    # tmp/escape is a symlink to /etc — realpath should defeat this.
    d = gate.evaluate_phase1_legacy("rm -rf tmp/escape")
    assert d.blocked, d.message


def test_blocks_path_traversal(project_root: Path) -> None:
    _ = project_root
    d = gate.evaluate_phase1_legacy("rm -rf tmp/../../../etc")
    assert d.blocked, d.message


def test_blocks_mixed_tmp_and_unsafe(project_root: Path) -> None:
    _ = project_root
    d = gate.evaluate_phase1_legacy("rm -rf tmp/ok /etc/foo")
    assert d.blocked, d.message


def test_no_project_root_falls_back() -> None:
    # Outside a git checkout the project-tmp rule does not apply.
    with mock.patch.object(gate, "_project_root_from_cwd", return_value=None):
        d = gate.evaluate_phase1_legacy("rm -rf tmp/foo")
        # Falls back to old behaviour — "tmp/foo" is not in SAFE_RM_BASENAMES so blocked.
        assert d.blocked, d.message


# --- git reset --hard -------------------------------------------------------


def test_blocks_reset_hard() -> None:
    assert gate.evaluate_phase1_legacy("git reset --hard").blocked


def test_blocks_reset_hard_with_ref() -> None:
    assert gate.evaluate_phase1_legacy("git reset --hard HEAD~1").blocked


def test_allows_reset_soft() -> None:
    assert not gate.evaluate_phase1_legacy("git reset --soft HEAD~1").blocked


def test_allows_plain_reset() -> None:
    assert not gate.evaluate_phase1_legacy("git reset HEAD").blocked


# --- git clean --------------------------------------------------------------


def test_blocks_clean_fd() -> None:
    assert gate.evaluate_phase1_legacy("git clean -fd").blocked


def test_blocks_clean_df() -> None:
    assert gate.evaluate_phase1_legacy("git clean -df").blocked


def test_blocks_clean_force() -> None:
    assert gate.evaluate_phase1_legacy("git clean --force").blocked


def test_allows_clean_dry_run() -> None:
    assert not gate.evaluate_phase1_legacy("git clean -n").blocked


def test_allows_clean_interactive() -> None:
    assert not gate.evaluate_phase1_legacy("git clean -i").blocked


# --- wholesale checkout / restore -------------------------------------------


def test_blocks_checkout_dot() -> None:
    assert gate.evaluate_phase1_legacy("git checkout .").blocked


def test_blocks_checkout_dash_dot() -> None:
    assert gate.evaluate_phase1_legacy("git checkout -- .").blocked


def test_blocks_restore_dot() -> None:
    assert gate.evaluate_phase1_legacy("git restore .").blocked


def test_blocks_restore_staged_dot() -> None:
    assert gate.evaluate_phase1_legacy("git restore --staged .").blocked


def test_allows_checkout_branch() -> None:
    assert not gate.evaluate_phase1_legacy("git checkout main").blocked


def test_allows_restore_named_file() -> None:
    assert not gate.evaluate_phase1_legacy("git restore file.py").blocked


def test_allows_checkout_named_file() -> None:
    assert not gate.evaluate_phase1_legacy("git checkout -- file.py").blocked


def test_allows_checkout_new_branch() -> None:
    assert not gate.evaluate_phase1_legacy("git checkout -b feature/x").blocked


# --- branch force-delete ----------------------------------------------------


def test_blocks_branch_force_delete() -> None:
    assert gate.evaluate_phase1_legacy("git branch -D feature/x").blocked


def test_allows_branch_d() -> None:
    assert not gate.evaluate_phase1_legacy("git branch -d feature/x").blocked


def test_allows_branch_list() -> None:
    assert not gate.evaluate_phase1_legacy("git branch").blocked


# --- destructive SQL --------------------------------------------------------


def test_blocks_psql_drop_table() -> None:
    assert gate.evaluate_phase1_legacy('psql -c "DROP TABLE users"').blocked


def test_blocks_psql_drop_database() -> None:
    assert gate.evaluate_phase1_legacy('psql -c "DROP DATABASE prod"').blocked


def test_blocks_mysql_truncate() -> None:
    assert gate.evaluate_phase1_legacy('mysql -e "TRUNCATE TABLE logs"').blocked


def test_blocks_sql_case_insensitive() -> None:
    assert gate.evaluate_phase1_legacy('psql -c "drop table foo"').blocked


def test_blocks_sql_command_equals() -> None:
    assert gate.evaluate_phase1_legacy("psql --command='DROP TABLE foo'").blocked


def test_allows_grep_drop_table() -> None:
    # grep is not a SQL CLI tool -> no SQL rule applies.
    assert not gate.evaluate_phase1_legacy("grep 'DROP TABLE' migration.sql").blocked


def test_allows_select() -> None:
    assert not gate.evaluate_phase1_legacy('psql -c "SELECT * FROM users"').blocked


def test_allows_psql_file_input() -> None:
    # File-driven input is not inspected; user can audit the SQL file.
    assert not gate.evaluate_phase1_legacy("psql -f migration.sql").blocked


# --- Safe common operations (smoke) -----------------------------------------


def test_smoke_ls() -> None:
    assert not gate.evaluate_phase1_legacy("ls -la").blocked


def test_smoke_cd() -> None:
    assert not gate.evaluate_phase1_legacy("cd /tmp").blocked


def test_smoke_git_status() -> None:
    assert not gate.evaluate_phase1_legacy("git status").blocked


def test_smoke_git_diff() -> None:
    assert not gate.evaluate_phase1_legacy("git diff").blocked


def test_smoke_git_log() -> None:
    assert not gate.evaluate_phase1_legacy("git log --oneline -10").blocked


def test_smoke_go_test() -> None:
    assert not gate.evaluate_phase1_legacy("go test ./...").blocked


def test_smoke_npm_install() -> None:
    assert not gate.evaluate_phase1_legacy("npm install").blocked


def test_smoke_uv_run() -> None:
    assert not gate.evaluate_phase1_legacy("uv run pytest").blocked


# --- Edge cases -------------------------------------------------------------


def test_empty_command() -> None:
    assert not gate.evaluate_phase1_legacy("").blocked


def test_unparseable_command_with_heredoc() -> None:
    # Unbalanced quote -> shlex fails -> only raw-string rules can fire.
    # The heredoc rule still catches '<<' via substring.
    assert gate.evaluate_phase1_legacy('cat << EOF\nbad "quote').blocked


def test_unparseable_command_no_match() -> None:
    assert not gate.evaluate_phase1_legacy('echo "unterminated').blocked
