# Text rules for the posted comment

Rules for any text that goes on the ADR page. They apply to the comment, its replies, inline
comments and ticket drafts. Working files are exempt except where a rule says otherwise.

## Contents

- [Stance](#stance)
- [Claims and evidence](#claims-and-evidence)
- [Words](#words)
- [Sentences and structure](#sentences-and-structure)
- [Voice and tone](#voice-and-tone)
- [What stays out](#what-stays-out)
- [Publishing format](#publishing-format)

## Stance

- The review is a second pair of eyes that helps the ADR land. Every criticism comes with a
  proposal the author can adopt or adapt.
- Out of scope: defending the reviewer's own earlier decisions, and arguing against the approach
  the ADR chose. Related ADRs are context; they are cited only where the reviewed ADR relies on
  them.
- Propose what the committee decides; put design detail behind a link (C.42).

## Claims and evidence

- Ground every claim: ADR section links, tickets and MRs linked, documentation by anchor, and
  code links pinned to a commit SHA where the ADR's kind allows them (next rule). Never assert what
  was not verified.
- **The ADR's kind decides whether the comment cites code.** An ADR is an architecture
  document, and code citations are natural only when the ADR covers something already
  implemented. The goal records whether the ADR describes or changes an implemented system,
  proposes something not yet built, or is mixed, and which parts are which; for a mixed ADR, the
  kind of the part a passage concerns decides. In an implemented ADR or part, code links pinned to
  a commit are fine. In a proposal ADR or part, the comment cites design-level sources (the ADR,
  related ADRs, specifications, tickets, documentation), and the behaviour of existing code,
  including libraries the proposal would use, is cited through that code's documentation, not
  through code links. Code may still be read to verify a fact; the pinned code reference stays in
  `facts.md`.
- Before writing a point, check whether the ADR already makes it. If it does, quote the ADR's
  sentence verbatim with its section link and argue from it ("the ADR says …; the design must
  carry it through"), instead of rebuilding the argument.
- Mark an inference as an inference: "as written", "if", "the ADR does not say how …". A reading
  of the ADR that the author could contest becomes a question that covers both readings.
- Quotes are verbatim and checked against the snapshot. A term the ADR does not use is not put in
  quotation marks as if it did.
- Link to ADR sections, not to diagram or figure numbers. An inline comment links to the section
  of the main comment that carries its argument.

## Words

- Use the ADR's own vocabulary (`vocabulary-review.md`). Do not import terms from related ADRs or
  from the working files.
- Define a term on first use; spell out abbreviations; name concrete components instead of
  categories.
- Put identifiers, paths, settings and literal values in backticks.
- No unexplained symbols, arrows or shorthand.

## Sentences and structure

- One claim per paragraph; one problem per sentence when listing problems, each with its effect.
- No chains of clauses joined by semicolons; no nested parentheses.
- Human prose: concrete, with an example where an example carries the point. No filler, no
  ceremonial summaries, no stacked hedges.
- Asks are visible as asks, each with its deadline (before acceptance, before a named phase).
  The summary of asks at the top matches the asks in the sections one to one.

## Voice and tone

- First person singular for the reviewer: "I", "I'd suggest". "We" and "our" only for the team
  or company ("our pipeline", "our release process"), and inside verbatim quotes.
- Open with thanks to the author; add an apology when the review is late. No list of the ADR's
  strengths. Respect stays implicit in how points are made.
- Turn "contradicts" into a question or "does not match"; one sharp sentence is fine if it is
  fair and grounded.
- `@mention` the author once in the top comment.

## What stays out

- Session artefacts: working labels (finding numbers, check names, ask numbers, slugs), stage
  names, pattern IDs and FPF terms, file names of the working folder, word or character counts.
- Security-sensitive mechanics (how to reach an exposed system, credentials, exact
  misconfigurations): one line saying the issue exists and is tracked, with the ticket link. A
  decision in `decisions.md` may keep such a passage in the comment; then it is protected text.
- Companion documents: the comment is one file per version; detail goes to links or tickets.

## Publishing format

- ADR quotes as Confluence quote blocks or inline quotation marks with the section link.
- The paste note at the top of `40-comment.md` is not posted. It says where each part goes (top
  comment, reply, inline comment and its anchor text) and anything to fill in after posting.
- Confluence HTML is produced with the `jira-text` skill's converter when that skill is installed;
  otherwise the Markdown is pasted and the paste note says so.
