# Length budget

People do not read walls of text, and sometimes length is needed. The budget is therefore about
what a reader can do with the comment, not about a count.

## The budget

- **One to three Confluence comments**, plus inline comments anchored to the ADR sections they
  concern. More than three needs a decision in `decisions.md`.
- **The top comment stands alone**: a reader who stops after it knows every ask and its deadline,
  and why the review supports the ADR landing. The asks come right after the opening, one line
  each, grouped by deadline, with a pointer that each is explained below.
- **Each further comment carries one theme** and can be read on its own; it repeats the asks of
  its theme at its end. That repetition is the price of independent reading and is kept.
- **Detail goes behind links**: code, tickets, documentation. Security mechanics go to Jira.

## How it is judged

- The reader task above, checked by the acceptor's cold read and recorded in `70-checks.md`.
- Where a part reads as dense, look for cuts that keep the result (C.42): an argument the ADR
  already makes (quote it instead), a proposal detail the committee does not decide, a repeated
  example. Then look at the split (EXD.3): a claim and its decisive condition stay in the same
  comment.
- Internal size signals (for example, a top comment that takes more than a minute to read aloud)
  may prompt that look. They are never must-fix on their own, never override a decision, and are
  never reported to the user. Talk to the user about comments, parts and what the reader can do.

## Severity

| Situation | Severity |
|---|---|
| The top comment does not carry every ask with its deadline | must fix |
| More than three comments without a decision allowing it | should fix, with a structural proposal (merge, move to inline, move to Jira) |
| A dense passage with a cut that loses nothing the reader needs | consider, with the exact cut |
| Any finding that rests only on a count | not a finding |
