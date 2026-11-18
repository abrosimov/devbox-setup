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

SHA = "3f9c2a7d1e4b8c06a5d2f7e91b3c4d5e6f708192"
BLOB = f"https://gitlab.com/g/orders-api/-/blob/{SHA}/app/x.py#L1-2"
JIRA = "https://example.atlassian.net/browse"
WIKI = "https://example.atlassian.net/wiki/spaces/SHOP/pages/123456789/Orders+Checkout#Order-limits"


def rules(text: str, **kwargs: object) -> list[str]:
    return [f.rule for f in cjt.check_text("draft.md", text, **kwargs)]


def lines_of(text: str, rule: str) -> list[int]:
    return [f.line for f in cjt.check_text("draft.md", text) if f.rule == rule]


class JiraKeyTest(unittest.TestCase):
    def test_unlinked_mention_is_reported(self) -> None:
        self.assertEqual(rules("See PROJ-123 for details."), ["unlinked-jira-key"])

    def test_linked_mention_passes(self) -> None:
        self.assertEqual(rules(f"See [PROJ-123]({JIRA}/PROJ-123) for details."), [])

    def test_later_bare_mention_after_a_link_is_reported(self) -> None:
        text = f"See [PROJ-123]({JIRA}/PROJ-123). Later PROJ-123 again."
        self.assertEqual(rules(text), ["unlinked-jira-key"])

    def test_every_bare_mention_is_reported(self) -> None:
        text = "Contradictions:\n- PROJ-1 one\n- PROJ-1 two and PROJ-1 three\n"
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [2, 3, 3])

    def test_every_linked_mention_passes(self) -> None:
        link = f"[PROJ-1]({JIRA}/PROJ-1)"
        self.assertEqual(rules(f"## One\n{link} and {link}\n- Source: {link}\n"), [])

    def test_link_text_naming_the_key_with_comment_url_passes(self) -> None:
        text = f"[Alice's decision on PROJ-12]({JIRA}/PROJ-12?focusedCommentId=10001#comment-10001)"
        self.assertEqual(rules(text), [])

    def test_key_in_link_text_pointing_elsewhere_is_reported(self) -> None:
        self.assertEqual(rules(f"[PROJ-123 notes]({JIRA}/PROJ-1)"), ["unlinked-jira-key"])

    def test_second_key_in_link_text_for_the_first_is_reported(self) -> None:
        self.assertEqual(rules(f"[PROJ-1 and PROJ-2]({JIRA}/PROJ-1)"), ["unlinked-jira-key"])

    def test_key_inside_url_is_not_a_mention(self) -> None:
        self.assertEqual(rules(f"[the ticket]({JIRA}/PROJ-123) and {JIRA}/PROJ-124"), [])

    def test_quoted_key_is_reported(self) -> None:
        self.assertEqual(rules('It says "(related: PROJ-101)".'), ["unlinked-jira-key"])

    def test_quoted_key_with_a_link_passes(self) -> None:
        self.assertEqual(rules(f'It says "(related: [PROJ-101]({JIRA}/PROJ-101))".'), [])

    def test_non_project_tokens_are_ignored(self) -> None:
        self.assertEqual(rules("UTF-8 and SHA-256 and A100-80GB slices."), [])

    def test_key_in_code_span_is_ignored(self) -> None:
        self.assertEqual(rules("The branch `PROJ-123_fix` exists."), [])


class SpecRuleTest(unittest.TestCase):
    def test_unlinked_mention_is_reported(self) -> None:
        self.assertEqual(rules("2.2 on the wording of ORD-BR-42."), ["unlinked-spec-rule"])

    def test_linked_to_confluence_passes(self) -> None:
        self.assertEqual(rules(f"[ORD-BR-42 of Orders — Checkout]({WIKI}) holds it."), [])

    def test_later_bare_mention_after_a_link_is_reported(self) -> None:
        text = f"[ORD-BR-42 of Orders — Checkout]({WIKI}), and ORD-BR-42 again."
        self.assertEqual(rules(text), ["unlinked-spec-rule"])

    def test_several_rules_in_one_confluence_link_pass(self) -> None:
        self.assertEqual(rules(f"[PAY-BR-28 and PAY-BR-29]({WIKI})"), [])

    def test_spec_rule_linked_to_jira_is_reported(self) -> None:
        self.assertEqual(rules(f"[ORD-BR-42]({JIRA}/PROJ-1)"), ["unlinked-spec-rule"])

    def test_spec_rule_is_not_also_a_jira_key(self) -> None:
        self.assertEqual(rules("PAY-BR-27"), ["unlinked-spec-rule"])

    def test_short_form_after_full_form_is_reported(self) -> None:
        text = f"[PAY-BR-69]({WIKI}) and then BR-69 again."
        self.assertEqual(rules(text), ["unlinked-spec-rule"])

    def test_linked_short_form_passes(self) -> None:
        self.assertEqual(rules(f"Under [BR-69]({WIKI}) as written."), [])

    def test_quoted_rule_is_reported(self) -> None:
        self.assertEqual(rules('The page says "see PAY-BR-69".'), ["unlinked-spec-rule"])


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
            rules("[x.py:1](https://gitlab.com/g/r/-/blob/3f9c2a7d1/x.py#L1)"), ["unpinned-blob"]
        )

    def test_full_sha_passes(self) -> None:
        self.assertEqual(rules(f"[x.py:1-2]({BLOB})"), [])

    def test_bare_url_is_checked_too(self) -> None:
        self.assertEqual(rules("See https://gitlab.com/g/r/-/blob/main/x.py"), ["unpinned-blob"])


class PinTest(unittest.TestCase):
    HEADER = (
        "Code links are pinned to current main: `orders-api` `3f9c2a7d1`, "
        "tag `v1.19.0` (`a7b3c9d1e`).\n\n"
    )

    def test_sha_outside_header_is_reported(self) -> None:
        other = "1234567890abcdef1234567890abcdef12345678"
        text = self.HEADER + f"[x.py:1](https://gitlab.com/g/r/-/blob/{other}/x.py#L1)"
        self.assertEqual(rules(text), ["pin-mismatch"])

    def test_sha_listed_in_header_passes(self) -> None:
        tag = "a7b3c9d1e2f4058617a8b9c0d1e2f3a4b5c6d7e8"
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
        self.assertEqual(rules(f"[order_service.py:584-616]({BLOB})"), [])

    def test_test_name_passes(self) -> None:
        self.assertEqual(rules(f"[test_order_total]({BLOB})"), [])


class CodeInLinkTextTest(unittest.TestCase):
    MR = "https://gitlab.com/g/mlops-be/-/merge_requests/28"

    def test_backticked_test_name_is_reported(self) -> None:
        self.assertEqual(rules(f"[`test_order_total`]({BLOB})"), ["code-in-link-text"])

    def test_code_and_words_in_link_text_are_reported(self) -> None:
        self.assertEqual(rules(f"[`mlops-be` MR !28]({self.MR})"), ["code-in-link-text"])

    def test_code_outside_the_link_passes(self) -> None:
        text = f"`mlops-be` [MR !28]({self.MR}) and [mlops-be MR !28]({self.MR})"
        self.assertEqual(rules(text), [])

    def test_allow_code_links_passes(self) -> None:
        self.assertEqual(rules(f"[`mlops-be` MR !28]({self.MR})", allow_code_links=True), [])


class SecondPersonTest(unittest.TestCase):
    def test_off_without_document(self) -> None:
        self.assertEqual(rules("You object, and your reply stays yours."), [])

    def test_document_reports_each_word(self) -> None:
        text = "You object, and your reply stays yours."
        self.assertEqual(rules(text, document=True), ["second-person"] * 3)

    def test_document_reports_link_text(self) -> None:
        self.assertEqual(rules(f"[your reply]({BLOB})", document=True), ["second-person"])

    def test_quotation_code_and_longer_words_pass(self) -> None:
        text = 'He wrote "you decide", `your_field` stays, and yourself or youth pass.'
        self.assertEqual(rules(text, document=True), [])


class BareTextTest(unittest.TestCase):
    def test_placeholder_is_reported(self) -> None:
        self.assertEqual(rules("Use the <order_id> of the order."), ["bare-placeholder"])

    def test_backticked_placeholder_and_html_tag_pass(self) -> None:
        self.assertEqual(rules("Use `<order_id>`.<br>Done."), [])

    def test_api_path_is_reported(self) -> None:
        self.assertEqual(rules("Call GET /v3/orders now."), ["bare-api-path"])

    def test_admin_path_is_reported(self) -> None:
        self.assertEqual(rules("Call /admin/v3/clusters now."), ["bare-api-path"])

    def test_backticked_path_and_non_api_slash_pass(self) -> None:
        self.assertEqual(rules("Call `GET /v3/orders`. N/A or and/or, 2/v3."), [])

    def test_literal_after_colon_is_reported(self) -> None:
        self.assertEqual(rules("Send discount_code: null to clear it."), ["bare-literal"])

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
        self.assertEqual(rules("See [[PROJ-87 Jira comment draft]]."), ["wikilink"])


class RegionTest(unittest.TestCase):
    def test_frontmatter_and_fenced_code_are_skipped(self) -> None:
        text = "---\ntags: [PROJ-1; B5]\n---\n```\nPROJ-2; /v3/x <id>\n```\nclean\n"
        self.assertEqual(rules(text), [])

    def test_markers_switch_checking_off_and_on(self) -> None:
        text = "PROJ-1\n<!-- jira-text: off -->\nPROJ-2\n%% jira-text: on %%\nPROJ-3\n"
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [1, 5])

    def test_vault_comment_heading_limits_the_check(self) -> None:
        text = "\n".join(
            [
                *("---", "tags: []", "---", "# PROJ-1 draft", "Before posting: PROJ-2"),
                *("## Comment on PROJ-3", "PROJ-4", "## Ticket drafts", "PROJ-5", ""),
            ]
        )
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [7])

    def test_vault_description_block_limits_the_check(self) -> None:
        text = "\n".join(
            [
                *("---", "t: 1", "---", "Jira fields", "- Parent: PROJ-1", "Title: x"),
                *("Description:", "", "**Summary**", "PROJ-2", "", "Open items", "- PROJ-3", ""),
            ]
        )
        self.assertEqual(lines_of(text, "unlinked-jira-key"), [10])

    def test_vault_preamble_and_title_are_skipped(self) -> None:
        text = "\n".join(
            [
                *("---", "t: 1", "---", "# PROJ-1 notes", "", "Parent: [[PROJ-1]]. Revised."),
                *("", "Revised 2026 for PROJ-2.", "", "PROJ-3 body", ""),
            ]
        )
        self.assertEqual([f.line for f in cjt.check_text("d.md", text)], [10])

    def test_whole_flag_ignores_vault_layout(self) -> None:
        text = "---\nt: 1\n---\n# PROJ-1 notes\n"
        self.assertEqual(rules(text, whole=True), ["unlinked-jira-key"])

    def test_plain_file_without_frontmatter_is_checked_whole(self) -> None:
        self.assertEqual(rules("Revised for PROJ-1\n"), ["unlinked-jira-key"])


class MainTest(unittest.TestCase):
    def test_output_format_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad, good = Path(tmp, "bad.md"), Path(tmp, "good.md")
            bad.write_text("x\nSee PROJ-1.\n", encoding="utf-8")
            good.write_text("clean text\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cjt.main([str(bad)]), 1)
            self.assertRegex(out.getvalue(), r"^.*bad\.md:2: unlinked-jira-key: ")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cjt.main([str(good)]), 0)

    def test_flags_switch_code_links_and_second_person(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp, "draft.md")
            draft.write_text("[`x`](https://e.io/a) for you\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(cjt.main([str(draft)]), 1)
                self.assertEqual(cjt.main(["--allow-code-links", str(draft)]), 0)
                self.assertEqual(cjt.main(["--allow-code-links", "--document", str(draft)]), 1)
            found = [line.split(": ")[1] for line in out.getvalue().splitlines()]
            self.assertEqual(found, ["code-in-link-text", "second-person"])

    def test_missing_file_exits_2(self) -> None:
        self.assertEqual(cjt.main(["/nonexistent/draft.md"]), 2)


if __name__ == "__main__":
    unittest.main()
