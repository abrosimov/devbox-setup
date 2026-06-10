#!/usr/bin/env python3
"""Tests for pre_bash_safety_gate.

Run from any directory:
    python3 bin/pre_bash_safety_gate_test.py
or via unittest discovery:
    python3 -m unittest bin.pre_bash_safety_gate_test
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pre_bash_safety_gate as gate  # noqa: E402


class TestHeredoc(unittest.TestCase):
    def test_blocks_heredoc(self):
        self.assertTrue(gate.evaluate("cat << EOF\nhi\nEOF").blocked)

    def test_blocks_here_string(self):
        # Preserves legacy substring-match: <<< also contains '<<'.
        self.assertTrue(gate.evaluate("cat <<< hello").blocked)

    def test_allows_plain_echo(self):
        self.assertFalse(gate.evaluate("echo hello").blocked)

    def test_allows_redirect(self):
        self.assertFalse(gate.evaluate("echo hi > file.txt").blocked)


class TestCommitOnMain(unittest.TestCase):
    @mock.patch.object(gate, "_current_branch", return_value="main")
    def test_blocks_on_main(self, _):
        d = gate.evaluate("git commit -m 'wip'")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "commit-on-main")

    @mock.patch.object(gate, "_current_branch", return_value="master")
    def test_blocks_on_master(self, _):
        self.assertTrue(gate.evaluate("git commit").blocked)

    @mock.patch.object(gate, "_current_branch", return_value="feature/x")
    def test_allows_on_feature(self, _):
        self.assertFalse(gate.evaluate("git commit -m 'fix'").blocked)


class TestMergeOnMain(unittest.TestCase):
    @mock.patch.object(gate, "_current_branch", return_value="main")
    def test_blocks_merge_into_main(self, _):
        self.assertTrue(gate.evaluate("git merge feature/x").blocked)

    @mock.patch.object(gate, "_current_branch", return_value="feature/x")
    def test_allows_merge_into_feature(self, _):
        self.assertFalse(gate.evaluate("git merge main").blocked)


class TestForcePush(unittest.TestCase):
    def test_blocks_force(self):
        self.assertTrue(gate.evaluate("git push --force").blocked)

    def test_blocks_f(self):
        self.assertTrue(gate.evaluate("git push -f").blocked)

    def test_blocks_force_with_origin(self):
        self.assertTrue(gate.evaluate("git push origin main --force").blocked)

    def test_blocks_force_equals(self):
        self.assertTrue(gate.evaluate("git push --force=origin").blocked)

    def test_allows_force_with_lease(self):
        # Intentional tightening from the legacy hook: safer variant is allowed.
        self.assertFalse(gate.evaluate("git push --force-with-lease").blocked)

    def test_allows_normal_feature_push(self):
        self.assertFalse(gate.evaluate("git push origin feature/x").blocked)

    def test_blocks_refspec_plus_prefix(self):
        # "+feature" = force semantics at the refspec layer.
        d = gate.evaluate("git push origin +feature")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "force-push")

    def test_blocks_refspec_local_colon_plus_remote(self):
        # "local:+main" = force on remote side.
        d = gate.evaluate("git push origin local:+main")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "force-push")

    def test_blocks_refspec_plus_local_colon_remote(self):
        # "+local:remote" — plus prefix on entire refspec.
        d = gate.evaluate("git push origin +feature:other")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "force-push")


class TestPushMirrorAll(unittest.TestCase):
    def test_blocks_mirror(self):
        d = gate.evaluate("git push --mirror origin")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-mirror-all")

    def test_blocks_all(self):
        d = gate.evaluate("git push --all origin")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-mirror-all")

    def test_blocks_all_no_remote(self):
        self.assertTrue(gate.evaluate("git push --all").blocked)

    def test_allows_normal_push(self):
        self.assertFalse(gate.evaluate("git push origin feature/x").blocked)


class TestPushDeleteBranch(unittest.TestCase):
    def test_blocks_delete_flag(self):
        d = gate.evaluate("git push --delete origin feature/x")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-delete-branch")

    def test_blocks_colon_refspec(self):
        d = gate.evaluate("git push origin :feature/x")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-delete-branch")

    def test_blocks_colon_refs_heads_refspec(self):
        d = gate.evaluate("git push origin :refs/heads/feature/x")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-delete-branch")

    def test_allows_normal_refspec(self):
        # local:remote (both sides non-empty) is a normal push, not a delete.
        self.assertFalse(gate.evaluate("git push origin local:remote-feature").blocked)

    def test_allows_normal_push(self):
        self.assertFalse(gate.evaluate("git push origin feature/x").blocked)


class TestPushToProtected(unittest.TestCase):
    def test_blocks_bare_main(self):
        d = gate.evaluate("git push origin main")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-to-protected")
        self.assertIn("main", d.message or "")

    def test_blocks_bare_master(self):
        d = gate.evaluate("git push origin master")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-to-protected")

    def test_blocks_local_colon_main(self):
        self.assertTrue(gate.evaluate("git push origin foo:main").blocked)

    def test_blocks_refs_heads_master(self):
        d = gate.evaluate("git push origin local:refs/heads/master")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-to-protected")

    def test_blocks_head_colon_main(self):
        d = gate.evaluate("git push origin HEAD:main")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-to-protected")

    def test_blocks_refs_remotes_origin_main(self):
        d = gate.evaluate("git push origin local:refs/remotes/origin/main")
        self.assertTrue(d.blocked)
        self.assertEqual(d.rule_name, "push-to-protected")

    def test_allows_feature_branch(self):
        self.assertFalse(gate.evaluate("git push origin feature/x").blocked)

    def test_allows_set_upstream_feature(self):
        # -u must not confuse positional parsing.
        self.assertFalse(gate.evaluate("git push -u origin feature/x").blocked)

    def test_allows_bare_push(self):
        # Bare `git push` is safe — rule_commit_on_main prevents new commits
        # on main/master in the first place.
        self.assertFalse(gate.evaluate("git push").blocked)

    def test_allows_remote_only(self):
        # `git push origin` (no refspec) = current branch -> upstream. Same
        # reasoning as bare `git push`.
        self.assertFalse(gate.evaluate("git push origin").blocked)

    def test_allows_branch_with_main_substring(self):
        # "mainline" is NOT main — exact match only.
        self.assertFalse(gate.evaluate("git push origin mainline").blocked)

    def test_allows_branch_with_master_path(self):
        # "feature/master-cleanup" is NOT master.
        self.assertFalse(gate.evaluate("git push origin feature/master-cleanup").blocked)

    def test_env_var_extends_protected(self):
        # User adds "develop" to protected list via env var.
        with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "main,master,develop"}):
            d = gate.evaluate("git push origin develop")
            self.assertTrue(d.blocked)
            self.assertEqual(d.rule_name, "push-to-protected")

    def test_env_var_wildcard_release(self):
        with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "main,master,release/*"}):
            d = gate.evaluate("git push origin release/1.0")
            self.assertTrue(d.blocked)
            # And a non-matching branch is still allowed.
            self.assertFalse(gate.evaluate("git push origin feature/x").blocked)

    def test_env_var_override_removes_default(self):
        # User explicitly sets only "develop" — main is no longer protected here.
        with mock.patch.dict("os.environ", {"CC_PROTECTED_BRANCHES": "develop"}):
            self.assertFalse(gate.evaluate("git push origin main").blocked)
            self.assertTrue(gate.evaluate("git push origin develop").blocked)


class TestAmend(unittest.TestCase):
    def test_blocks_amend(self):
        with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
            self.assertTrue(gate.evaluate("git commit --amend").blocked)

    def test_blocks_amend_with_message(self):
        with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
            self.assertTrue(gate.evaluate("git commit --amend -m 'oops'").blocked)


class TestNoVerify(unittest.TestCase):
    def test_blocks_no_verify(self):
        with mock.patch.object(gate, "_current_branch", return_value="feature/x"):
            self.assertTrue(gate.evaluate("git commit --no-verify -m 'fix'").blocked)


class TestLintSuppression(unittest.TestCase):
    def test_blocks_echo_noqa(self):
        self.assertTrue(gate.evaluate("echo '# noqa: E501' >> file.py").blocked)

    def test_blocks_sed_ts_ignore(self):
        self.assertTrue(gate.evaluate("sed -i 's/.*/\\/\\/ ts-ignore/' file.ts").blocked)

    def test_blocks_cat_pipe_grep_eslint_disable(self):
        # Preserves legacy: cat in any pipeline that references suppression.
        self.assertTrue(gate.evaluate("cat file | grep eslint-disable").blocked)

    def test_allows_grep_only(self):
        self.assertFalse(gate.evaluate("grep noqa file.py").blocked)

    def test_allows_clean_lint_run(self):
        self.assertFalse(gate.evaluate("ruff check .").blocked)


class TestRmRf(unittest.TestCase):
    def test_allows_node_modules(self):
        self.assertFalse(gate.evaluate("rm -rf node_modules").blocked)

    def test_allows_dotvenv(self):
        self.assertFalse(gate.evaluate("rm -rf .venv").blocked)

    def test_allows_dist_build(self):
        self.assertFalse(gate.evaluate("rm -rf dist build").blocked)

    def test_allows_nested_node_modules(self):
        self.assertFalse(gate.evaluate("rm -rf ./packages/app/node_modules").blocked)

    def test_allows_pycache(self):
        self.assertFalse(gate.evaluate("rm -rf __pycache__").blocked)

    def test_allows_tmp(self):
        self.assertFalse(gate.evaluate("rm -rf /tmp/foo").blocked)

    def test_allows_tmpdir_literal(self):
        self.assertFalse(gate.evaluate('rm -rf "$TMPDIR/foo"').blocked)

    def test_blocks_etc(self):
        self.assertTrue(gate.evaluate("rm -rf /etc/passwd").blocked)

    def test_blocks_home(self):
        self.assertTrue(gate.evaluate('rm -rf "$HOME"').blocked)

    def test_blocks_root(self):
        self.assertTrue(gate.evaluate("rm -rf /").blocked)

    def test_blocks_mixed_safe_and_unsafe(self):
        # Any unsafe target -> block.
        self.assertTrue(gate.evaluate("rm -rf node_modules /etc/foo").blocked)

    def test_allows_rm_without_force(self):
        # rm without both -r and -f is outside this rule's scope.
        self.assertFalse(gate.evaluate("rm node_modules").blocked)

    def test_allows_rm_r_only(self):
        self.assertFalse(gate.evaluate("rm -r node_modules").blocked)

    def test_allows_rm_f_only(self):
        self.assertFalse(gate.evaluate("rm -f file.txt").blocked)


class TestProjectTmp(unittest.TestCase):
    """rm -rf is allowed for paths under <project-root>/tmp/ (realpath-validated)."""

    def setUp(self) -> None:
        import tempfile
        self._tmpdir = tempfile.mkdtemp(prefix="gate-test-")
        self._project_root = Path(self._tmpdir) / "myproj"
        (self._project_root / ".git").mkdir(parents=True)
        (self._project_root / "tmp").mkdir()
        (self._project_root / "tmp" / "render-out").mkdir()
        # Symlink escape attack: tmp/escape -> /etc
        (self._project_root / "tmp" / "escape").symlink_to("/etc")
        # Pretend cwd is the project root.
        self._cwd_patch = mock.patch.object(
            gate.Path, "cwd", return_value=self._project_root
        )
        self._cwd_patch.start()

    def tearDown(self) -> None:
        import shutil
        self._cwd_patch.stop()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_allows_rm_inside_project_tmp(self):
        d = gate.evaluate("rm -rf tmp/render-out")
        self.assertFalse(d.blocked, d.message)

    def test_allows_rm_glob_inside_project_tmp(self):
        # rm -rf tmp/* expands at shell level; we exercise a concrete child.
        d = gate.evaluate("rm -rf tmp/render-out/intermediate")
        self.assertFalse(d.blocked, d.message)

    def test_blocks_rm_of_tmp_itself(self):
        # We allow contents, not the tmp/ dir itself.
        d = gate.evaluate("rm -rf tmp")
        # rm-rf rule may still allow if "tmp" basename happens to match a safe
        # name, but it should NOT match via the project-tmp rule for the dir itself.
        # Confirm: with no .cache/.venv/etc basename, plain "tmp" is unsafe.
        self.assertTrue(d.blocked, d.message)

    def test_blocks_symlink_escape(self):
        # tmp/escape is a symlink to /etc — realpath should defeat this.
        d = gate.evaluate("rm -rf tmp/escape")
        self.assertTrue(d.blocked, d.message)

    def test_blocks_path_traversal(self):
        d = gate.evaluate("rm -rf tmp/../../../etc")
        self.assertTrue(d.blocked, d.message)

    def test_blocks_mixed_tmp_and_unsafe(self):
        d = gate.evaluate("rm -rf tmp/ok /etc/foo")
        self.assertTrue(d.blocked, d.message)

    def test_no_project_root_falls_back(self):
        # Outside a git checkout the project-tmp rule does not apply.
        with mock.patch.object(gate, "_project_root_from_cwd", return_value=None):
            d = gate.evaluate("rm -rf tmp/foo")
            # Falls back to old behaviour — "tmp/foo" is not in SAFE_RM_BASENAMES so blocked.
            self.assertTrue(d.blocked, d.message)


class TestGitResetHard(unittest.TestCase):
    def test_blocks_reset_hard(self):
        self.assertTrue(gate.evaluate("git reset --hard").blocked)

    def test_blocks_reset_hard_with_ref(self):
        self.assertTrue(gate.evaluate("git reset --hard HEAD~1").blocked)

    def test_allows_reset_soft(self):
        self.assertFalse(gate.evaluate("git reset --soft HEAD~1").blocked)

    def test_allows_plain_reset(self):
        self.assertFalse(gate.evaluate("git reset HEAD").blocked)


class TestGitClean(unittest.TestCase):
    def test_blocks_clean_fd(self):
        self.assertTrue(gate.evaluate("git clean -fd").blocked)

    def test_blocks_clean_df(self):
        self.assertTrue(gate.evaluate("git clean -df").blocked)

    def test_blocks_clean_force(self):
        self.assertTrue(gate.evaluate("git clean --force").blocked)

    def test_allows_clean_dry_run(self):
        self.assertFalse(gate.evaluate("git clean -n").blocked)

    def test_allows_clean_interactive(self):
        self.assertFalse(gate.evaluate("git clean -i").blocked)


class TestWholesaleCheckoutRestore(unittest.TestCase):
    def test_blocks_checkout_dot(self):
        self.assertTrue(gate.evaluate("git checkout .").blocked)

    def test_blocks_checkout_dash_dot(self):
        self.assertTrue(gate.evaluate("git checkout -- .").blocked)

    def test_blocks_restore_dot(self):
        self.assertTrue(gate.evaluate("git restore .").blocked)

    def test_blocks_restore_staged_dot(self):
        self.assertTrue(gate.evaluate("git restore --staged .").blocked)

    def test_allows_checkout_branch(self):
        self.assertFalse(gate.evaluate("git checkout main").blocked)

    def test_allows_restore_named_file(self):
        self.assertFalse(gate.evaluate("git restore file.py").blocked)

    def test_allows_checkout_named_file(self):
        self.assertFalse(gate.evaluate("git checkout -- file.py").blocked)

    def test_allows_checkout_new_branch(self):
        self.assertFalse(gate.evaluate("git checkout -b feature/x").blocked)


class TestBranchForceDelete(unittest.TestCase):
    def test_blocks_branch_D(self):
        self.assertTrue(gate.evaluate("git branch -D feature/x").blocked)

    def test_allows_branch_d(self):
        self.assertFalse(gate.evaluate("git branch -d feature/x").blocked)

    def test_allows_branch_list(self):
        self.assertFalse(gate.evaluate("git branch").blocked)


class TestDestructiveSql(unittest.TestCase):
    def test_blocks_psql_drop_table(self):
        self.assertTrue(gate.evaluate('psql -c "DROP TABLE users"').blocked)

    def test_blocks_psql_drop_database(self):
        self.assertTrue(gate.evaluate('psql -c "DROP DATABASE prod"').blocked)

    def test_blocks_mysql_truncate(self):
        self.assertTrue(gate.evaluate('mysql -e "TRUNCATE TABLE logs"').blocked)

    def test_blocks_case_insensitive(self):
        self.assertTrue(gate.evaluate('psql -c "drop table foo"').blocked)

    def test_blocks_command_equals(self):
        self.assertTrue(gate.evaluate("psql --command='DROP TABLE foo'").blocked)

    def test_allows_grep_drop_table(self):
        # grep is not a SQL CLI tool -> no SQL rule applies.
        self.assertFalse(gate.evaluate("grep 'DROP TABLE' migration.sql").blocked)

    def test_allows_select(self):
        self.assertFalse(gate.evaluate('psql -c "SELECT * FROM users"').blocked)

    def test_allows_psql_file_input(self):
        # File-driven input is not inspected; user can audit the SQL file.
        self.assertFalse(gate.evaluate("psql -f migration.sql").blocked)


class TestSafeCommonOperations(unittest.TestCase):
    """Smoke tests — everyday commands must pass cleanly."""

    def test_ls(self):
        self.assertFalse(gate.evaluate("ls -la").blocked)

    def test_cd(self):
        self.assertFalse(gate.evaluate("cd /tmp").blocked)

    def test_git_status(self):
        self.assertFalse(gate.evaluate("git status").blocked)

    def test_git_diff(self):
        self.assertFalse(gate.evaluate("git diff").blocked)

    def test_git_log(self):
        self.assertFalse(gate.evaluate("git log --oneline -10").blocked)

    def test_go_test(self):
        self.assertFalse(gate.evaluate("go test ./...").blocked)

    def test_npm_install(self):
        self.assertFalse(gate.evaluate("npm install").blocked)

    def test_uv_run(self):
        self.assertFalse(gate.evaluate("uv run pytest").blocked)


class TestEdgeCases(unittest.TestCase):
    def test_empty_command(self):
        self.assertFalse(gate.evaluate("").blocked)

    def test_unparseable_command_with_heredoc(self):
        # Unbalanced quote -> shlex fails -> only raw-string rules can fire.
        # The heredoc rule still catches '<<' via substring.
        self.assertTrue(gate.evaluate('cat << EOF\nbad "quote').blocked)

    def test_unparseable_command_no_match(self):
        self.assertFalse(gate.evaluate('echo "unterminated').blocked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
