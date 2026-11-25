# Document skeleton and formatting rules

Fixed in stage 2, before any prose. A shape decided late costs a rework of everything above it.

## Contents

- [Order of the parts](#order-of-the-parts)
- [The top block](#the-top-block)
- [The findings table](#the-findings-table)
- [The body](#the-body)
- [Appendices](#appendices)
- [Formatting rules](#formatting-rules)

## Order of the parts

1. **Header**: date, the question the document answers, the material it rests on (deck file and
   its last-saved date, public sources), scope (technology only). No version number, no "draft".
2. **What the business needs to know**: the top block, on page one.
3. **Summary**: the findings table with a two-line legend.
4. **Who reads what**: a table of parts and readers, then a checklist for the next phase.
5. **Contents.**
6. **Body.**
7. **Appendices**, as working material by reader.

## The top block

- A short numbered list of the points a decision maker needs, each with its business consequence,
  then a "can start now" line naming what can begin without waiting for the seller.
- Each point links to the body section that carries its evidence.
- Every statement keeps the qualifier of its source ("the deck names", "the maker gives as
  tentative"). The top block is checked statement by statement in stage 6.
- No remedies. A point ends at what to check, ask or start first.

## The findings table

Columns: Finding | Kind | Rating | First step.

- Sorted by rating, always (Red, Amber, No data), and re-sorted after every change.
- Each row keeps the "named in the deck" qualifier where the finding rests on the deck, and
  carries its business consequence in plain words.
- The rating colour matches the rating word in every cell.
- The legend gives the rating definitions in two lines (`vocabulary.md`).

## The body

1. The platform in plain words: what the material says it is and runs on.
2. How to read the findings: the kinds, the ratings and the "named, shown, working" levels.
3. Confirmed facts and problems.
4. Blank spots, in priority order.
5. Claims that say less than they seem to.
6. Next steps: checks, requests and questions, each doable at its stage.

Each finding is written as **What we see / Why it matters / Not known / First step**.

## Appendices

Working material, each addressed to its reader in the "who reads what" table. Typical set:
components named; outdated components with sources; where data goes; errors in the deck;
on-screen checks; background notes; data requests; questions for the developers; glossary. Use
only those the material fills; an empty appendix is dropped, not padded.

## Formatting rules

Decide these in stage 2 and record them in `decisions.md`:

- space before every heading; each appendix starts on a new page; a lead-in sentence stays with
  its list;
- table text size and column widths chosen so the summary table fits one page;
- rating colours, applied the same way everywhere;
- the first mention of each glossary term links to the glossary, and only the first;
- internal links point at headings, so a renamed heading is a link check (stage 9).

Pagination cannot be seen in the markdown; check it in the delivery format by rendering pages.
