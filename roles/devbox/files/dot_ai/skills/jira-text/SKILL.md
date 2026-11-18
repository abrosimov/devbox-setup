---
name: jira-text
description: >
  Rules and a deterministic checker for any text that goes to Jira or Confluence: ticket
  descriptions, Jira comments, Confluence page edits and MR descriptions. Covers one link format
  per kind (Jira ticket, Jira comment, spec rule such as WS-BR-42, code pinned to a commit SHA,
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
  - MR description
  - spec rule link
  - permalink
  - pinned SHA
  - link format
problem: "Link and wording rules for Jira text lived only in agent briefs, so after three review rounds a spec rule (WS-BR-42) was still mentioned without a link."
related: [jira-ticket, commit-and-pr-text, writing-for-the-reader]
---

# Jira text

Text posted to Jira or Confluence is read by people who never saw the session, often weeks later,
by following its links. A prose rule such as "readable links" is easy to agree with and easy to
miss: after three review rounds a draft still mentioned WS-BR-42 without a link. So the rules live
here with a checker that finds what a reader misses, and every writer and reviewer runs it.

Contents: [Scope](#scope) · [Workflow](#workflow) · [Running the checker](#running-the-checker) ·
[What it checks](#what-it-checks) · [Vault notes](#vault-notes) ·
[What the checker cannot judge](#what-the-checker-cannot-judge)

## Scope

| This skill owns | Owned elsewhere |
| --- | --- |
| Link formats and link text for tickets, comments, spec rules, code, tests, MRs, commits | Ticket structure, templates, priority, readiness: `jira-ticket` |
| Backticks, semicolons, internal labels, HTML entities in Jira, Confluence and MR text | Commit and MR structure, and what stays out of them: `commit-and-pr-text` |
| The checker `scripts/check_jira_text.py` | Messages to the user in the chat: `writing-for-the-reader` |

For an MR description, `commit-and-pr-text` decides the sections and the length, and this skill
decides how links and identifiers inside it are written. The checker runs on both.

Where `jira-ticket`'s output rules say "no backticks", this skill's backtick rules apply to the
identifiers listed in the reference: a placeholder or a path without backticks is lost or misread
in Jira.

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

Options: `--whole` checks every line after the frontmatter and ignores the vault-note layout.
`--label-pattern REGEX` (repeatable) replaces the internal-label patterns.

Its own tests: `uv run --no-project python -I <skill-dir>/scripts/test_check_jira_text.py`.

## What it checks

Frontmatter, fenced code blocks, inline code spans and link URLs are never read as text.

| Rule id | Finds |
| --- | --- |
| `unlinked-jira-key` | A Jira key (`EF-9792`) whose first mention in a section is not a link to that key |
| `unlinked-spec-rule` | A spec rule id (`WS-BR-42`, `BR-69`) whose first mention in a section is not inside a Confluence link |
| `unpinned-blob` | A GitLab or GitHub blob link to `main`, a branch, a tag, or a SHA shorter than 40 characters |
| `pin-mismatch` | A blob SHA that starts with none of the SHAs in the pin header (skipped when there is none) |
| `unreadable-link-text` | Link text that starts with `:`, is only digits and punctuation, or is "here" or "link" |
| `bare-placeholder` | `<word>` outside backticks (HTML tags such as `<br>` excepted) |
| `bare-api-path` | A path starting `/v1`, `/v2`, `/v3` or `/admin` outside backticks |
| `bare-literal` | `true`, `false` or `null` used as a value outside backticks: after `:` or `=`, after "set to", "defaults to", "returns", "sends", "becomes", or alone in a table cell, list item or parentheses. Prose such as "true for both" passes |
| `semicolon` | A semicolon outside code, URLs, entities and quotations |
| `internal-label` | Ledger ids and decision numbers that mean nothing outside the session |
| `html-entity` | `&lt;` or `&gt;` |
| `wikilink` | An Obsidian `[[wikilink]]`, which does not render in Jira |

Mention rules in detail: a section starts at a Markdown heading or at a line that is bold from
end to end (`**1.2 Does lowering …?**`). A key inside a URL is part of the link, not a mention. A
key or rule inside a quotation is someone else's text and is not counted. A short form `BR-69`
after `TENRES-BR-69` in the same section counts as a later mention.

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
   - otherwise a line `Description:` (the `jira-ticket` layout): only the lines after it are
     checked, up to a line `Open items` or `Readiness`;
   - otherwise the whole body except H1 titles and paragraphs that start with "Revised",
     "Parent:" or "Before posting".
3. **A file without frontmatter** (an MR description, a plain draft) is checked whole.

The pin header is read anywhere in the file, including the vault-only parts, because that is
where drafts usually keep it.

## What the checker cannot judge

Check these by hand before handing over:

- **Link text says whose and about what**: "Frane's decision on EF-9205", not "comment 79613".
- **Links land where they claim**: the Confluence anchor opens the section that holds the rule,
  the code lines cover the claim, the test anchor is the line of its `def` or `func`.
- **Pins are current**: the pin header names the commit you meant (current main, the MR head, or
  a tag on purpose), and every repository with links has a line in it.
- **Backticks on identifiers the checker does not know**: field names, environment variables,
  payloads, our service names. Third-party products (Volcano, Kubernetes) stay without.
- **No cyclic links**: a ticket never links a comment that is not posted yet.
- **Placeholders are resolved**: a `[new bug: key]` or `[TBD …]` left in posted text.
- **Internal labels in other shapes**: labels with prefixes outside the default set, or a section
  number of a different document ("section 2.3 of the comment").
- **Mentions split across lines** and links whose text spans a line break are not seen.
