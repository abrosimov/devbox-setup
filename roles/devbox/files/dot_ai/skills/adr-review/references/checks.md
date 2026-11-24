# Checks before the user sees a draft

Run by the main session after acceptance (and again after any later fix). Record each check in
`vNN/70-checks.md` as **yes**, **no**, **unknown** or **not checked**, with the command or the
basis (C.41.UA). "Not checked" is never written as passed (A.7).

## Contents

- [Deterministic scans](#deterministic-scans)
- [Fact retention](#fact-retention)
- [Aliases](#aliases)
- [The jira-text checker](#the-jira-text-checker)
- [Manual checks](#manual-checks)

## Deterministic scans

Run with the Grep tool over the posted parts of `vNN/40-comment.md` (everything after the paste
note). Each hit is reviewed by hand; a hit inside a verbatim ADR quote or a link target is not a
defect.

Patterns are in ripgrep syntax, one per line; each is followed by what a hit means.

```text
Working labels        \b[A-Z]-?\d{1,2}\b
                      \b(ask|item|point) \d+\b
  a finding number, check name or ask number leaked; a real name (a storage service, a phase)
  can also match, so judge each hit
Register slugs        each slug from points.md and facts.md, as a literal
  a working name leaked
Pattern IDs           \b[A-G]\.\d+(\.[A-Z0-9]+)*\b
                      \b(GOALS|NSTD|PSDA|FPF)\b
  framework terms leaked
Imported terms        each entry of the "do not use" table in vocabulary.md, as a literal
  a term from another document
Reviewer "we"         \b(we|We|us|our|Our)\b
  judge each: the team's "we/our" and verbatim quotes stay
Semicolon chains      ;
  outside code spans and link targets: a joined clause to split
Code links            /-/blob/|/blob/|@[0-9a-f]{7,40}:
  one scan for every code link, pinned or not; judge each hit in this order:
  1. the code-citation rule (text-rules.md, "Claims and evidence") rules it out: report it as a
     code link to replace with documentation, whether or not it is pinned;
  2. it is allowed but points at a branch (/-/blob/(main|master|develop)/, /blob/(main|master)/):
     report it as unpinned; pin it to a 40-hex commit
Counts                \b\d+ (words?|characters?)\b
  a size count in posted text
Security markers      the strings decisions.md names as Jira-only, as literals
  a mechanic that belongs in the ticket
```

## Fact retention

For each review point whose status in this version is adopted or adapted, and for each must-keep fact
it names in `points.md`:

- the fact's statement is present in the comment in some wording, and its reference link is
  present (search the comment for the URL or the pinned path), or its design-level source is
  present where the ADR's kind rules out the code link; that replacement is not a loss;
- or `41-changes.md` records its loss with the reason and the decision that allows it.

A must-keep fact missing without a recorded loss is a **no**, and goes back to the editor.

## Aliases

For every Markdown file in `vNN/` (and any shared file created in this version), the frontmatter
`aliases:` list has an entry that starts with the ADR id and contains `vNN` or `vMM` per
`workspace-layout.md`, "Aliases". Patterns: version files
`^\s*-\s*"?ADR-\d{3,} (v\d{2} |feedback on v\d{2})`; shared files
`^\s*-\s*"?ADR-\d{3,} .+ \(from v\d{2}\)"?\s*$`. A missing alias is fixed by the main session in
place.

## The jira-text checker

When the `jira-text` skill is installed, run its checker `scripts/check_jira_text.py` on the
comment file (the skill's `SKILL.md` gives the command) and record every finding; its
`scripts/md_to_confluence_html.py` produces the paste-ready HTML. Known false positives (for example, an ADR id the checker reads as an unlinked Jira key)
are listed by line with the reason. When it is not installed, write "not checked: `jira-text` not
available" and rely on the scans above plus the manual checks below.

## Manual checks

- Every ADR quote matches the snapshot verbatim (compare each quoted string).
- Every summary line at the top has exactly one ask in its section, with the same deadline, and
  every ask in a section appears in the summary.
- Every inline comment's anchor text exists in the ADR snapshot.
- The length budget's reader task holds (`length-budget.md`).
- Protected passages are byte-identical to their source (exact string search).
- Links opened in this version are listed with the date; links not re-opened are listed as not
  re-checked.
