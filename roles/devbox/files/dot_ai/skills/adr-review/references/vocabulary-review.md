# Vocabulary review

The comment speaks the reviewed ADR's language. A term imported from a related ADR or from the
working files makes the author translate, and can suggest a design the ADR did not choose.

## The file

`AI/vocabulary.md`, written by the goal setter on the first version and on each new ADR page
version (F.2: harvest the source's own words and what they mean there, then stop before
comparing with other sources).

| Term | What it means in the ADR | Where (section link) | First use in the comment defines it? |
|---|---|---|---|
| render queue | the queue of thumbnail requests that the worker pool takes jobs from; a request leaves it only when its thumbnail is stored | Glossary | no: the ADR defines it |

A second table lists **terms not to use**, each with where it comes from and the ADR's own term
to use instead, or "no equivalent: describe it".

| Do not use | Comes from | Use instead |
|---|---|---|
| job runner | a related ADR | the ADR's "render queue" and "worker pool" |

The example rows illustrate the format; each review harvests its own.

## Rules

1. Every domain term in the comment is either in the first table or defined on first use in
   plain words. A term the ADR defines is used with the ADR's meaning.
2. No term from the second table appears in posted text, except inside a verbatim quote.
3. Working names (point and fact slugs, check names, stage names, pattern IDs) never appear.
4. When the ADR renames a term between page versions, use the new name and keep the old reading
   recoverable where an earlier comment used it (F.13): "the worker pool (called *renderers* in the
   earlier version)". Do not rewrite quotes from the earlier page.
5. One concept, one word, throughout the comment set.

## Who checks

- Editor: writes in the first table's terms.
- Reviewer: lists each domain term not in the first table and not defined on first use, and each
  hit from the second table, with the replacement.
- Checks stage: scans the comment for every entry of the second table (`checks.md`).
