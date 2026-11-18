---
name: jira-text
description: >
  Rules and a deterministic checker for any text that goes to Jira or Confluence: ticket
  descriptions, Jira comments, Confluence page edits, and MR descriptions that link Jira tickets,
  Confluence pages or pinned code. Covers one link format
  per kind (Jira ticket, Jira comment, spec rule such as ORD-BR-42, code pinned to a commit SHA,
  test, MR, commit), backticks for placeholders, API paths, payloads and literals, and the bans on
  semicolon-joined clauses, internal ledger labels and HTML entities. Use before handing over or
  posting any Jira or Confluence draft, when reviewing or verifying one, and when writing link
  text to code, tickets or spec rules. Also use for a short Jira comment or a one-line ticket
  edit, as the checker catches unlinked keys and unpinned code links that reviews miss.
version: 1
triggers:
  - jira comment
  - ticket description
  - confluence page
  - MR description with Jira links
  - spec rule link
  - permalink
  - pinned SHA
  - link format
problem: "Link and wording rules for Jira text lived only in agent briefs, so after three review rounds a spec rule (ORD-BR-42) was still mentioned without a link."
related: [commit-and-pr-text, writing-for-the-reader]
---

# Jira text

Text posted to Jira or Confluence is read by people who never saw the session, often weeks later,
by following its links. A prose rule such as "readable links" is easy to agree with and easy to
miss: after three review rounds a draft still mentioned ORD-BR-42 without a link. So the rules live
here with a checker that finds what a reader misses, and every writer and reviewer runs it.

Contents: [Scope](#scope) · [Workflow](#workflow) · [Running the checker](#running-the-checker) ·
[What it checks](#what-it-checks) · [Vault notes](#vault-notes) ·
[Publishing to Confluence](#publishing-to-confluence) ·
[What the checker cannot judge](#what-the-checker-cannot-judge)

## Scope

| This skill owns | Owned elsewhere |
| --- | --- |
| Link formats and link text for tickets, comments, spec rules, code, tests, MRs, commits | Ticket structure, templates, priority, readiness: `jira-ticket` (local overlay, when installed) |
| Backticks, semicolons, internal labels, HTML entities in Jira and Confluence text, and in MR descriptions that link Jira, Confluence or pinned code | Commit and MR structure, and what stays out of them: `commit-and-pr-text` |
| The checker `scripts/check_jira_text.py` and the converter `scripts/md_to_confluence_html.py` | Messages to the user in the chat: `writing-for-the-reader` |

An MR description is in scope only when it links Jira tickets, Confluence pages or pinned code.
There `commit-and-pr-text` decides the sections and the length, and this skill decides the link
formats and the text rules (`references/link-formats.md` § Text rules) for the whole description,
as the checker reads all of it. An ordinary PR or MR without such links follows
`commit-and-pr-text` alone.

The output rules of `jira-ticket` (local overlay, when installed) defer to this skill for inline
code: a placeholder or a path without backticks is lost or misread in Jira.

## Workflow

1. **Write** with the formats in `references/link-formats.md`: one entry per link kind (Jira
   ticket, Jira comment, spec rule, code, test, MR, commit and pin header) and the text rules.
2. **Before handing over a draft, run the checker and fix every finding.** A draft with findings
   is not ready. If a finding is wrong, say so in the hand-over with the line, rather than leaving
   it unexplained.
3. **Reviewers and verifying agents run the checker too**, on the same files, and treat each
   finding as a defect in the draft.
4. **Then check by hand what the checker cannot judge** (below).

## Running the checker

`<skill-dir>` is the directory that holds this `SKILL.md` (`${CLAUDE_SKILL_DIR}` in Claude Code).

```bash
uv run --no-project python -I <skill-dir>/scripts/check_jira_text.py FILE...
```

Output is one line per finding, `path:line: rule-id: message`. Exit status 0 means no findings, 1
means findings, 2 a usage or read error. Standard library only: `--no-project` keeps it out of the
current repository's environment, and `-I` keeps the working directory off the import path.

Options: `--whole` checks every line after the frontmatter and ignores the vault-note layout
(markers still apply).
`--label-pattern REGEX` (repeatable) replaces the internal-label patterns.
`--allow-code-links` turns `code-in-link-text` off, for a PR or MR description that will not be
pasted into Jira: GitLab and GitHub both render a link around inline code.
`--document` turns `second-person` on, for text published as a document such as a Confluence
page. Jira comments may address people, so it is off by default.

Tests of both scripts: `uv run --no-project python -I -m unittest discover -s <skill-dir>/scripts`.

## What it checks

Frontmatter, fenced code blocks, inline code spans and link URLs are never read as text, except
by `html-entity`, which also reads inside code, because an entity shows literally there too.

| Rule id | Finds |
| --- | --- |
| `unlinked-jira-key` | A mention of a Jira key (`PROJ-123`) that is not a link to that key |
| `unlinked-spec-rule` | A mention of a spec rule id (`ORD-BR-42`, `BR-69`) that is not inside a Confluence link |
| `unpinned-blob` | A GitLab or GitHub blob link to `main`, a branch, a tag, or a SHA shorter than 40 characters |
| `pin-mismatch` | A blob SHA that starts with none of the SHAs in the pin header (skipped when there is none) |
| `unreadable-link-text` | Link text that starts with `:`, is only digits and punctuation, or is "here", "link", "this", "this link" or "click here" |
| `code-in-link-text` | Link text with inline code (``[`TestName`](…)``, ``[`orders-api` MR !28](…)``): Jira's Markdown-to-ADF converter drops the link and keeps only the code. Off with `--allow-code-links` |
| `bare-placeholder` | `<word>` outside backticks (HTML tags such as `<br>` excepted) |
| `bare-api-path` | A path starting `/v1`, `/v2`, `/v3` or `/admin` outside backticks |
| `bare-literal` | `true`, `false` or `null` used as a value outside backticks: after `:` or `=`, after "set to", "defaults to", "returns", "sends", "becomes", or alone in a table cell, list item or parentheses. Prose such as "true for both" passes |
| `semicolon` | A semicolon outside code, URLs, entities and quotations |
| `internal-label` | Ledger ids and decision numbers that mean nothing outside the session |
| `html-entity` | `&lt;` or `&gt;` |
| `wikilink` | An Obsidian `[[wikilink]]`, which does not render in Jira |
| `second-person` | `you`, `your` or `yours` outside quotations and code. Only with `--document` |

Mention rules in detail: a Jira key or spec rule id is linked at every mention, wherever it
stands: in a heading of the posted text, a list, a table, under a label, or inside a quotation
(`"(related: [PROJ-160](…/browse/PROJ-160))"`). A mention inside longer link text counts as
linked when the link goes to that key's `/browse/` page, or to a `/wiki/` page for a rule. A key
inside a URL is part of the link, not a mention. A short form `BR-69` is a mention like the full
id.

**Internal labels.** The defaults are `\b[BDEIQR]\d{1,2}[a-z]?\b` (B5, D3, E7, Q9f, R1, I1 to I9)
and `\b[Dd]ecision \d+(?:\.\d+)+\b` ("decision 1.4"). The letter set and the two-digit limit keep
H100, A100, B200, T4, L1159 and V064 out, and F1 is not flagged because F is not a ledger prefix in
use. Q1 to Q4 followed by a year are quarters and pass. If a draft uses other ledger prefixes,
pass them with `--label-pattern`.

## Vault notes

Drafts often live in an Obsidian vault note that mixes Jira text with vault-only parts: the
frontmatter, a "Revised …" preamble, "Before posting" steps, "Jira fields", "Open items". The
checker decides what to read in this order:

1. **Markers.** If the file has `<!-- jira-text: off -->` or `%% jira-text: off %%` lines, checking
   stops there and resumes at the next `<!-- jira-text: on -->` or `%% jira-text: on %%`. Checking
   starts on. Both forms are hidden in Obsidian's reading view. Use markers in new drafts: they
   are exact.
2. **Without markers, a file with YAML frontmatter is read as a vault note:**
   - a heading that starts "Comment on" or "Jira comment": only its section is checked;
   - otherwise a line `Description:` (the `jira-ticket` layout, from the local overlay when installed): only the lines after it are
     checked, up to a line `Open items` or `Readiness`;
   - otherwise the whole body except H1 titles and paragraphs that start with "Revised",
     "Parent:" or "Before posting".
3. **A file without frontmatter** (an MR description, a plain draft) is checked whole.

The pin header is read anywhere in the file, including the vault-only parts, because that is
where drafts usually keep it.

## Publishing to Confluence

- **Publish the body as HTML when the page links other Confluence pages.** Replacing a page body
  in Markdown is refused when the page already holds such links, because Confluence stores them
  as resources. Copy only the page body into its own file first: no frontmatter (the converter
  stops on it) and no vault-only parts, because it ignores `jira-text` markers and would publish
  them and the text between them as paragraphs. Then convert it:
  `uv run --no-project python -I <skill-dir>/scripts/md_to_confluence_html.py IN_MD OUT_HTML [--toc]`.
  It handles the subset these drafts use: `##` and `###` headings, paragraphs, flat `- ` and `1. `
  lists, pipe tables with a header row, inline code and `[text](https://…)` links. Any other block
  syntax stops it with the line number, so no block is dropped silently. Bold and italics are not
  converted: `**bold**` and `_italics_` appear literally on the page. `--toc` puts a Table of
  Contents macro before the first `##` heading. It prints the link counts in and out: compare
  them before publishing, as a difference means a link did not convert.
- **A document on a page is not addressed to one person.** Write "Alice's comment on PROJ-120",
  not "your reply", and "product objects", not "you object". Run the checker with `--document` on
  page text: `second-person` flags `you`, `your` and `yours`.

## What the checker cannot judge

Check these by hand before handing over:

- **Link text says whose and about what**: "Alice's decision on PROJ-120", not "comment 10001".
- **Links land where they claim**: the Confluence anchor opens the section that holds the rule,
  the code lines cover the claim, the test anchor is the line of its `def` or `func`.
- **Pins are current**: the pin header names the commit you meant (current main, the MR head, or
  a tag on purpose), and every repository with links has a line in it.
- **Backticks on identifiers the checker does not know**: field names, environment variables,
  payloads, our service names. Third-party products (Kubernetes, PostgreSQL) stay without.
- **No cyclic links**: a ticket never links a comment that is not posted yet.
- **Placeholders are resolved**: a `[new bug: key]` or `[TBD …]` left in posted text.
- **Internal labels in other shapes**: labels with prefixes outside the default set, or a section
  number of a different document ("section 2.3 of the comment").
- **Mentions split across lines** and links whose text spans a line break are not seen.
