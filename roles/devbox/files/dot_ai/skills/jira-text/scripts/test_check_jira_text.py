"""Tests for check_jira_text: one positive and one negative case per rule, plus regions."""

# ruff: noqa: PT009 -- stdlib unittest on purpose, so the tests run with no packages installed.

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

# Loaded by path because `python -I` keeps the script directory off sys.path.
_SPEC = importlib.util.spec_from_file_location(
    "check_jira_text", Path(__file__).with_name("check_jira_text.py")
)
assert _SPEC is not None
assert _SPEC.loader is not None
cjt = importlib.util.module_from_spec(_SPEC)
sys.modules["check_jira_text"] = cjt
_SPEC.loader.exec_module(cjt)

SHA = "7ff63b71a08f867690360c577c6779c64f9742fa"
BLOB = f"https://gitlab.com/g/mlops-be/-/blob/{SHA}/app/x.py#L1-2"
JIRA = "https://openinnovationai.atlassian.net/browse"
WIKI = "https://openinnovationai.atlassian.net/wiki/spaces/EF/pages/1615691920/Workspace+Monitor#Capacity-and-use"


def rules(text: str, **kwargs: object) -> list[str]:
    return [f.rule for f in cjt.check_text("draft.md", text, **kwargs)]


def lines_of(text: str, rule: str) -> list[int]:
    return [f.line for f in cjt.check_text("draft.md", text) if f.rule == rule]


class JiraKeyTest(unittest.TestCase):
    def test_unlinked_first_mention_is_reported(self) -> None:
        self.assertEqual(rules("See EF-9792 for details."), ["unlinked-jira-key"])

    def test_linked_first_mention_and_later_bare_mention_pass(self) -> None:
        self.assertEqual(rules(f"See [EF-9792]({JIRA}/EF-9792). Later EF-9792 again."), [])

    def test_link_text_naming_the_key_with_comment_url_passes(self) -> None:
        text = f"[Frane's decision on EF-9205]({JIRA}/EF-9205?focusedCommentId=79613#comment-79613)"
        self.assertEqual(rules(text), [])

    def test_key_in_link_text_pointing_elsewhere_is_reported(self) -> None:
        self.assertEqual(rules(f"[EF-9792 notes]({JIRA}/EF-1)"), ["unlinked-jira-key"])

    def test_key_inside_url_is_not_a_mention(self) -> None:
        self.assertEqual(rules(f"[the ticket]({JIRA}/EF-9792) and {JIRA}/EF-9793"), [])

    def test_each_section_needs_its_own_link(self) -> None:
        text = f"**One**\n[EF-1]({JIRA}/EF-1)\n\n**Two**\nEF-1 again\n"
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [5])

    def test_heading_starts_a_section(self) -> None:
        text = f"## One\n[EF-1]({JIRA}/EF-1)\n## Two\nEF-1\n"
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [4])

    def test_partly_bold_line_does_not_start_a_section(self) -> None:
        text = f"[EF-1]({JIRA}/EF-1)\n**A** and **B**\nEF-1\n"
        self.assertEqual(rules(text), [])

    def test_quoted_mention_does_not_count(self) -> None:
        text = f'It says "related: EF-8160". [EF-8160]({JIRA}/EF-8160) is a child.'
        self.assertEqual(rules(text), [])

    def test_non_project_tokens_are_ignored(self) -> None:
        self.assertEqual(rules("UTF-8 and SHA-256 and A100-80GB slices."), [])

    def test_key_in_code_span_is_ignored(self) -> None:
        self.assertEqual(rules("The branch `EF-9792_fix` exists."), [])


class SpecRuleTest(unittest.TestCase):
    def test_unlinked_first_mention_is_reported(self) -> None:
        self.assertEqual(rules("2.2 on the wording of WS-BR-42."), ["unlinked-spec-rule"])

    def test_linked_to_confluence_passes(self) -> None:
        self.assertEqual(
            rules(f"[WS-BR-42 of Workspace — Monitor]({WIKI}), and WS-BR-42 again."), []
        )

    def test_spec_rule_linked_to_jira_is_reported(self) -> None:
        self.assertEqual(rules(f"[WS-BR-42]({JIRA}/EF-1)"), ["unlinked-spec-rule"])

    def test_spec_rule_is_not_also_a_jira_key(self) -> None:
        self.assertEqual(rules("TENRES-BR-27"), ["unlinked-spec-rule"])

    def test_short_form_after_full_form_passes(self) -> None:
        self.assertEqual(rules(f"[TENRES-BR-69]({WIKI}) and then BR-69 again."), [])

    def test_short_form_alone_is_reported(self) -> None:
        self.assertEqual(rules("Under BR-69 as written."), ["unlinked-spec-rule"])


class BlobTest(unittest.TestCase):
    def test_branch_pin_is_reported(self) -> None:
        self.assertEqual(
            rules("[x.py:1](https://gitlab.com/g/r/-/blob/main/x.py#L1)"), ["unpinned-blob"]
        )

    def test_github_branch_pin_is_reported(self) -> None:
        self.assertEqual(
            rules("[x.go:1](https://github.com/o/r/blob/master/x.go#L1)"), ["unpinned-blob"]
        )

    def test_short_sha_is_reported(self) -> None:
        self.assertEqual(
            rules("[x.py:1](https://gitlab.com/g/r/-/blob/7ff63b71a/x.py#L1)"), ["unpinned-blob"]
        )

    def test_full_sha_passes(self) -> None:
        self.assertEqual(rules(f"[x.py:1-2]({BLOB})"), [])

    def test_bare_url_is_checked_too(self) -> None:
        self.assertEqual(rules("See https://gitlab.com/g/r/-/blob/main/x.py"), ["unpinned-blob"])


class PinTest(unittest.TestCase):
    HEADER = (
        "Code links are pinned to current main: `mlops-be` `7ff63b71a`, "
        "tag `v1.19.0` (`2bdbf7160`).\n\n"
    )

    def test_sha_outside_header_is_reported(self) -> None:
        other = "1234567890abcdef1234567890abcdef12345678"
        text = self.HEADER + f"[x.py:1](https://gitlab.com/g/r/-/blob/{other}/x.py#L1)"
        self.assertEqual(rules(text), ["pin-mismatch"])

    def test_sha_listed_in_header_passes(self) -> None:
        tag = "2bdbf7160ecf3e9c6b498f465c15d5e2bf3eb24f"
        text = (
            self.HEADER + f"[x.py:1]({BLOB}) [y.go:2](https://gitlab.com/g/w/-/blob/{tag}/y.go#L2)"
        )
        self.assertEqual(rules(text), [])

    def test_no_header_skips_the_check(self) -> None:
        other = "1234567890abcdef1234567890abcdef12345678"
        self.assertEqual(rules(f"[x.py:1](https://gitlab.com/g/r/-/blob/{other}/x.py#L1)"), [])


class LinkTextTest(unittest.TestCase):
    def test_colon_lines_text_is_reported(self) -> None:
        self.assertEqual(rules(f"[:493-499]({BLOB})"), ["unreadable-link-text"])

    def test_bare_number_is_reported(self) -> None:
        self.assertEqual(rules(f"[584]({BLOB})"), ["unreadable-link-text"])

    def test_here_is_reported(self) -> None:
        self.assertEqual(rules(f"see [here]({BLOB})"), ["unreadable-link-text"])

    def test_file_and_lines_passes(self) -> None:
        self.assertEqual(rules(f"[ResourceAllocationService.py:584-616]({BLOB})"), [])

    def test_backticked_test_name_passes(self) -> None:
        self.assertEqual(rules(f"[`test_total_counts_node`]({BLOB})"), [])


class BareTextTest(unittest.TestCase):
    def test_placeholder_is_reported(self) -> None:
        self.assertEqual(rules("Use the <workspace_id> of the workspace."), ["bare-placeholder"])

    def test_backticked_placeholder_and_html_tag_pass(self) -> None:
        self.assertEqual(rules("Use `<workspace_id>`.<br>Done."), [])

    def test_api_path_is_reported(self) -> None:
        self.assertEqual(rules("Call GET /v3/workspaces now."), ["bare-api-path"])

    def test_admin_path_is_reported(self) -> None:
        self.assertEqual(rules("Call /admin/v3/clusters now."), ["bare-api-path"])

    def test_backticked_path_and_non_api_slash_pass(self) -> None:
        self.assertEqual(rules("Call `GET /v3/workspaces`. N/A or and/or, 2/v3."), [])

    def test_literal_after_colon_is_reported(self) -> None:
        self.assertEqual(rules("Send mig_profile: null to clear it."), ["bare-literal"])

    def test_literal_after_defaults_to_is_reported(self) -> None:
        self.assertEqual(rules("The entity defaults to true."), ["bare-literal"])

    def test_literal_alone_in_a_cell_is_reported(self) -> None:
        self.assertEqual(rules("| flag | false |"), ["bare-literal"])

    def test_literal_in_prose_passes(self) -> None:
        self.assertEqual(
            rules("This is true for both cases, and false hopes are null and void."), []
        )

    def test_backticked_literal_passes(self) -> None:
        self.assertEqual(rules("It defaults to `true`."), [])


class SemicolonTest(unittest.TestCase):
    def test_semicolon_in_prose_is_reported(self) -> None:
        self.assertEqual(rules("The check runs; the save fails."), ["semicolon"])

    def test_semicolon_in_code_url_entity_or_quote_passes(self) -> None:
        text = 'Run `a; b` at https://x.io/a;b and &amp; then "one; two".'
        self.assertEqual(rules(text), [])


class InternalLabelTest(unittest.TestCase):
    def test_ledger_ids_are_reported(self) -> None:
        self.assertEqual(rules("As B5 and Q9f say, see I1."), ["internal-label"] * 3)

    def test_decision_number_is_reported(self) -> None:
        self.assertEqual(rules("Open as comment decision 1.4."), ["internal-label"])

    def test_hardware_line_and_migration_names_pass(self) -> None:
        self.assertEqual(rules("H100, A100, B200, T4, F1, V064 and #L1159 and Q4 2026."), [])

    def test_custom_pattern_replaces_defaults(self) -> None:
        self.assertEqual(rules("B5 and X12", label_patterns=[r"\bX\d+\b"]), ["internal-label"])


class EntityTest(unittest.TestCase):
    def test_entity_is_reported(self) -> None:
        self.assertEqual(rules("Use `&lt;id&gt;` here."), ["html-entity", "html-entity"])

    def test_plain_angle_brackets_in_code_pass(self) -> None:
        self.assertEqual(rules("Use `<id>` here."), [])


class WikilinkTest(unittest.TestCase):
    def test_wikilink_is_reported_and_key_inside_is_not_a_mention(self) -> None:
        self.assertEqual(rules("See [[EF-8073 Jira comment draft]]."), ["wikilink"])


class RegionTest(unittest.TestCase):
    def test_frontmatter_and_fenced_code_are_skipped(self) -> None:
        text = "---\ntags: [EF-1; B5]\n---\n```\nEF-2; /v3/x <id>\n```\nclean\n"
        self.assertEqual(rules(text), [])

    def test_markers_switch_checking_off_and_on(self) -> None:
        text = "EF-1\n<!-- jira-text: off -->\nEF-2\n%% jira-text: on %%\nEF-3\n"
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [1, 5])

    def test_vault_comment_heading_limits_the_check(self) -> None:
        text = "\n".join(
            [
                *("---", "tags: []", "---", "# EF-1 draft", "Before posting: EF-2"),
                *("## Comment on EF-3", "EF-4", "## Ticket drafts", "EF-5", ""),
            ]
        )
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [7])

    def test_vault_description_block_limits_the_check(self) -> None:
        text = "\n".join(
            [
                *("---", "t: 1", "---", "Jira fields", "- Parent: EF-1", "Title: x"),
                *("Description:", "", "**Summary**", "EF-2", "", "Open items", "- EF-3", ""),
            ]
        )
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [10])

    def test_vault_preamble_and_title_are_skipped(self) -> None:
        text = "\n".join(
            [
                *("---", "t: 1", "---", "# EF-1 notes", "", "Parent: [[EF-1]]. Revised."),
                *("", "Revised 2026 for EF-2.", "", "EF-3 body", ""),
            ]
        )
        self.assertEqual([f.line for f in cjt.check_text("d.md", text)], [10])

    def test_whole_flag_ignores_vault_layout(self) -> None:
        text = "---\nt: 1\n---\n# EF-1 notes\n"
        self.assertEqual(rules(text, whole=True), ["unlinked-jira-key"])

    def test_plain_file_without_frontmatter_is_checked_whole(self) -> None:
        self.assertEqual(rules("Revised for EF-1\n"), ["unlinked-jira-key"])


class MainTest(unittest.TestCase):
    def test_output_format_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad, good = Path(tmp, "bad.md"), Path(tmp, "good.md")
            bad.write_text("x\nSee EF-1.\n", encoding="utf-8")
            good.write_text("clean text\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cjt.main([str(bad)]), 1)
            self.assertRegex(out.getvalue(), r"^.*bad\.md:2: unlinked-jira-key: ")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cjt.main([str(good)]), 0)

    def test_missing_file_exits_2(self) -> None:
        self.assertEqual(cjt.main(["/nonexistent/draft.md"]), 2)


if __name__ == "__main__":
    unittest.main()
