"""Tests for md_to_confluence_html: each block kind, escaping, links, refusals and the TOC."""

# ruff: noqa: PT009 -- stdlib unittest on purpose, so the tests run with no packages installed.

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Loaded by path because `python -I` keeps the script directory off sys.path.
_SPEC = importlib.util.spec_from_file_location(
    "md_to_confluence_html", Path(__file__).with_name("md_to_confluence_html.py")
)
assert _SPEC is not None
assert _SPEC.loader is not None
mch = importlib.util.module_from_spec(_SPEC)
sys.modules["md_to_confluence_html"] = mch
_SPEC.loader.exec_module(mch)

URL = "https://example.atlassian.net/browse/PROJ-1?focusedCommentId=1&x=2#comment-1"


def convert(text: str, *, toc: bool = False) -> str:
    return mch.convert(text, toc=toc)


def refusal(text: str, *, toc: bool = False) -> mch.ConversionError:
    try:
        mch.convert(text, toc=toc)
    except mch.ConversionError as err:
        return err
    msg = f"converted without refusal: {text!r}"
    raise AssertionError(msg)


class BlockTest(unittest.TestCase):
    def test_headings(self) -> None:
        self.assertEqual(convert("## One\n### Two\n"), "<h2>One</h2>\n<h3>Two</h3>\n")

    def test_paragraphs_join_lines_and_split_on_blank_lines(self) -> None:
        self.assertEqual(convert("a\nb\n\nc\n"), "<p>a b</p>\n<p>c</p>\n")

    def test_bullet_list(self) -> None:
        self.assertEqual(convert("- a\n- b\n"), "<ul><li><p>a</p></li><li><p>b</p></li></ul>\n")

    def test_numbered_list(self) -> None:
        self.assertEqual(convert("1. a\n2. b\n"), "<ol><li><p>a</p></li><li><p>b</p></li></ol>\n")

    def test_numbered_list_keeps_its_start(self) -> None:
        self.assertEqual(convert("3. c\n"), '<ol start="3"><li><p>c</p></li></ol>\n')

    def test_table_with_header_row(self) -> None:
        self.assertEqual(
            convert("| A | B |\n| --- | :-: |\n| 1 | `x` |\n"),
            "<table><thead><tr><th><p>A</p></th><th><p>B</p></th></tr></thead>"
            "<tbody><tr><td><p>1</p></td><td><p><code>x</code></p></td></tr></tbody></table>\n",
        )

    def test_blocks_follow_each_other_without_blank_lines(self) -> None:
        self.assertEqual(
            convert("## H\ntext\n- a\n1. b\n"),
            "<h2>H</h2>\n<p>text</p>\n<ul><li><p>a</p></li></ul>\n<ol><li><p>b</p></li></ol>\n",
        )


class InlineTest(unittest.TestCase):
    def test_placeholder_in_code_is_escaped(self) -> None:
        self.assertEqual(
            convert("Use `GET /v3/<order_id>?a&b`.\n"),
            "<p>Use <code>GET /v3/&lt;order_id&gt;?a&amp;b</code>.</p>\n",
        )

    def test_plain_text_is_escaped(self) -> None:
        self.assertEqual(convert("a < b & c > d\n"), "<p>a &lt; b &amp; c &gt; d</p>\n")

    def test_double_backtick_span_holds_a_backtick(self) -> None:
        self.assertEqual(convert("`` a`b ``\n"), "<p><code>a`b</code></p>\n")

    def test_link_href_is_escaped_once(self) -> None:
        self.assertEqual(
            convert(f"See [PROJ-1]({URL}).\n"),
            '<p>See <a href="https://example.atlassian.net/browse/PROJ-1'
            '?focusedCommentId=1&amp;x=2#comment-1">PROJ-1</a>.</p>\n',
        )

    def test_code_inside_link_text(self) -> None:
        self.assertEqual(
            convert("[`a<b>` notes](https://e.io/x)\n"),
            '<p><a href="https://e.io/x"><code>a&lt;b&gt;</code> notes</a></p>\n',
        )

    def test_link_syntax_inside_code_stays_code(self) -> None:
        self.assertEqual(
            convert("`[a](https://e.io)`\n"), "<p><code>[a](https://e.io)</code></p>\n"
        )

    def test_unbalanced_backticks_are_refused(self) -> None:
        self.assertEqual(refusal("ok\n\nan `open span\n").line, 3)


class RefusalTest(unittest.TestCase):
    def test_unsupported_lines_are_refused_with_their_line(self) -> None:
        for line in (
            "# Title",
            "#### Deep",
            "> quoted",
            "```",
            "~~~",
            "* star",
            "+ plus",
            "1) paren",
            "  - nested",
            "\tindented",
            "---",
        ):
            with self.subTest(line=line):
                self.assertEqual(refusal(f"fine\n\n{line}\n").line, 3)

    def test_table_without_separator_is_refused(self) -> None:
        self.assertIn("separator", refusal("| A |\n| 1 |\n").message)

    def test_bold_and_version_numbers_are_paragraphs(self) -> None:
        self.assertEqual(convert("**Objective**\n1.5 GiB\n"), "<p>**Objective** 1.5 GiB</p>\n")


class TocTest(unittest.TestCase):
    def test_toc_goes_before_the_first_h2(self) -> None:
        out = convert("intro\n### Sub\n## First\n## Second\n", toc=True)
        expected = ["<p>intro</p>", "<h3>Sub</h3>", mch.TOC_MACRO, "<h2>First</h2>"]
        self.assertEqual(out.splitlines(), [*expected, "<h2>Second</h2>"])

    def test_no_toc_without_the_flag(self) -> None:
        self.assertNotIn(mch.TOC_MACRO, convert("## First\n"))

    def test_toc_without_h2_is_refused(self) -> None:
        self.assertIsNone(refusal("### Only\n", toc=True).line)

    def test_macro_is_the_confluence_toc_extension(self) -> None:
        self.assertEqual(
            mch.TOC_MACRO,
            '<div data-type="extension" data-extension-key="toc" '
            'data-extension-type="com.atlassian.confluence.macro.core" '
            'data-parameters=\'{"macroParams":{"minLevel":{"value":"2"},"maxLevel":{"value":"3"}},'
            '"macroMetadata":{"schemaVersion":{"value":"1"},"title":"Table of Contents"}}\'></div>',
        )


class MainTest(unittest.TestCase):
    def test_writes_html_and_prints_equal_link_counts(self) -> None:
        source = (
            f"## A [PROJ-1]({URL})\n\n- [x](https://e.io/1) and [y](https://e.io/2)\n\n"
            "| L |\n| - |\n| [z](https://e.io/3) |\n\n1. [w](https://e.io/4)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, "in.md"), Path(tmp, "out.html")
            src.write_text(source, encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(mch.main([str(src), str(dst), "--toc"]), 0)
            self.assertEqual(out.getvalue(), "links in: 5, links out: 5, toc: inserted\n")
            self.assertEqual(dst.read_text(encoding="utf-8").count("<a href="), 5)

    def test_refusal_exits_2_names_the_line_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp, "in.md"), Path(tmp, "out.html")
            src.write_text("ok\n> quote\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(mch.main([str(src), str(dst)]), 2)
            self.assertRegex(err.getvalue(), r"in\.md:2: unsupported block quote")
            self.assertFalse(dst.exists())

    def test_missing_input_exits_2(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(mch.main(["/nonexistent/in.md", "/nonexistent/out.html"]), 2)


if __name__ == "__main__":
    unittest.main()
