# Stage contracts and checker briefs

What each stage receives, produces and counts as done; the two briefs for the `statement-checker`
agent; the formats of the working files.

## Contents

- [Workspace](#workspace)
- [FPF texts](#fpf-texts)
- [Stage contracts](#stage-contracts)
- [Brief: statement check](#brief-statement-check)
- [Brief: fresh eyes](#brief-fresh-eyes)
- [Working file formats](#working-file-formats)

## Workspace

The DD folder holds client material: never a tracked path in a repository.

```
<DD folder>/
  decisions.md          owner's decisions, each with date and source; outrank every criterion
  dd.md                 the document; source of truth for the text
  sources.md            public sources: link, read date, page opened yes/no, what it supports
  changes.md            every change with its kind and basis
  corrected-claims.md   register of corrected claims
  checks.md             check record: yes / no / unknown / not checked
  source/
    <deck file>         as received, unchanged
    deck-meta.md        file name, last-saved date and where it was read, slide count
    slides/s-NN.png     one rendered image per slide
    media/              pictures embedded in the deck
    visuals.md          per slide: expected visuals, seen yes/no
  reviews/
    NN-statement-check-rN.md, NN-fresh-eyes-rN.md      checker reports
    NN-<kind>-rN-triage.md   checker verdict + accept / partial / reject per finding
```

## FPF texts

The checker cannot preload the `fpf-thinking` skill, so briefs carry the absolute path. Resolve
the folder once, in this order: the sibling `../fpf-thinking/references/` of this skill's own
directory (skills are deployed side by side); `~/.claude/skills/fpf-thinking/references/`;
`~/.agents/skills/fpf-thinking/references/`. If none exists, say so in the brief. Letter IDs
are in `FPF-Spec.md`; NOT IDs in `DPFs/Foundational Thinking DPF Suite/NOTATIONAL-ENGINEERING-DPF.md`;
NSTD IDs in `DPFs/Narrativization-and-Narrative-Studies-Principles-Framework.md`. Recipe:
`grep -n '^## <ID> ' <file>`, then read to the next `^## `. Read the patterns; do not restate them
in the document.

## Stage contracts

### 1. Read the deck

**Does**: renders every slide to an image (for example the deck to PDF with LibreOffice, then
pages to PNG with `pdftoppm`); extracts embedded pictures (a `.pptx` is a zip: `ppt/media/`);
reads the last-saved date from the file's metadata (`docProps/core.xml` in a `.pptx`, `pdfinfo`
for a PDF); looks at every image. **Done when** every slide has an image that was viewed, and
`visuals.md` lists each slide's expected visuals with "seen" marked.

### 2. Fix the skeleton and formatting rules

**Patterns**: NSTD.1, NSTD.2. **Does**: writes the headings of `dd.md` from
`document-skeleton.md`, the rating definitions from `vocabulary.md` adapted to this document, and
the formatting rules as `decisions.md` rows. **Done when** the owner has the skeleton, or the
conversation already settles it.

### 3. Draft the top block and findings table

**Patterns**: A.10, A.6.3.CSC. **Does**: drafts the top block, the "can start now" line and the
findings table, each statement labelled `[S1]`, `[S2]`… for the checker; records every public
source in `sources.md` as it is read. **Done when** every statement has a source or is marked as
a blank spot.

### 4. Draft the body and appendices

**Patterns**: A.10, NSTD.2. **Does**: writes the body and the appendices the material fills, each
finding as What we see / Why it matters / Not known / First step, and links the top block to the
body sections that carry its evidence. **Done when** every top-block point has a body section and
every appendix has its reader in the "who reads what" table.

### 5. Claim-to-source and rating-definition passes

**Patterns**: A.10, A.7, B.5.2. **Does**: for every sentence, names what it rests on and checks
its strength against `evidence-rules.md`; runs the "words to distrust" checklist; reads every
rating against the document's own definition. **Done when** every sentence has a source at its
strength and every rating fits its definition as written.

### 6. Statement check (checker)

**Patterns** in the brief: A.10, A.7. Brief below. **Done when** every label has the checker's
verdict and every finding has the main session's accept, partial or reject in the triage file.

### 7. Tables and formulas reconciliation

**Patterns**: NOT.Reference:4, NOT.6. **Does**: re-runs every calculation from its stated inputs;
recounts table rows and every counter in the text; checks formula variables against the data
requests; checks the findings table's sort and colours. Repeats after every fix round. **Done
when** every figure reproduces and every count matches.

### 8. Fresh eyes (checker)

**Patterns** in the brief: A.10, NSTD.6. Brief below. A separate dispatch from stage 6. **Done
when** every finding has a triage verdict and each "missed" item is either used or recorded as
not material with its reason.

### 9. Links and the top

**Patterns**: C.41.UA. **Does**: opens every external link and confirms the read date; follows
every internal link; confirms each critical point of the body appears in the top block or is
linked from it, and that the top block makes sense alone. **Done when** all three answer yes.

## Brief: statement check

Fill the angle-bracketed parts; remove nothing else.

```
Mode: statement check.

You are an independent checker. A block of text is about to be placed at the top of an initial
technical due-diligence document, read by <reader>; many will read nothing else. Check every
statement in it, one by one. Write only your report.

Files (read-only):
- The statements: <labelled block file>. Each carries a label [S1] … [Sn].
- The document they summarise: <dd.md>. Pointers such as "(4.1)" or "(Appendix C)" refer to its
  headings.
- The deck: <deck file>; rendered slides <source/slides/s-01.png … s-NN.png> (look at them:
  diagrams and screenshots are not in the text layer); embedded pictures <source/media/>.
  Last saved <date>.
- Public sources read so far: <sources.md>.
- Claims already corrected: <corrected-claims.md>. Flag any statement, and any wording you
  propose, that reintroduces an old wording from it.
- Owner's decisions bearing on this check: <quoted rows>.
- FPF texts: <folder>; read A.10 and A.7 with the recipe <recipe>.

Today is <date>. Write the report to <report path> and return its content.

For each statement:
1. What it rests on: a slide (number and exact words), a public source, a document section, or
   nothing.
2. Is it true as worded? Open the primary evidence yourself. For "does not say", search all
   slides, text and images. For public facts, search, then open the page, and record the read
   date. Statements that need a public source, and the distinction that matters for each:
   <list, e.g. "promise of fixes ended" versus "no fixes released">.
   App store and other regional pages: name the storefront or regional address you read. The
   same relative timestamp ("15 hr ago") on reads days apart is a cached copy: mark it could not
   verify. Before confirming "not updated", read a second storefront; the later date wins.
3. Is it stronger than its source: "named in the deck" turned into a fact about the system; a
   "so" that does not follow; no / nothing / all / both / only / one without proof; a dropped
   qualifier?
4. Does it agree with the document's own section on the point? If the section is wrong or
   stronger than its source, quote it with its location.
5. Would <reader> understand it without the glossary, and does it say why it matters?

For the block as a whole: anything outside technology; any remedy; contradictions between
statements; at most three serious items of the document missing from the block, with sections.

Report:
1. Summary: verdict counts and the most serious problem.
2. Table: Label | Rests on | Verdict | What is wrong | Strongest wording the source supports.
   Verdicts: confirmed (true as worded); weaker form (the source supports only a weaker claim);
   wrong (the source contradicts it); could not verify (the source does not settle it, or could
   not be opened).
3. Disagreements with the document itself.
4. The block as a whole.
5. What could not be verified, what was tried, and when.
```

## Brief: fresh eyes

```
Mode: fresh eyes.

You have not seen this document before. Compare the deck with the initial technical
due-diligence document built from it, for <reader>. Write only your report.

Files (read-only): the document <dd.md>; the deck <deck file>, slides <source/slides/>,
pictures <source/media/>, last saved <date>; <sources.md>; <corrected-claims.md> (claims already
corrected: do not propose their old wording again). Owner's decisions: <quoted rows>.
FPF texts: <folder>; read A.10 and NSTD.6 with the recipe <recipe>.

Today is <date>. Write the report to <report path> and return its content.

1. Deck against document: every statement the document attributes to a slide, checked against
   the slide image. Verdict per statement: confirmed (true as worded); weaker form (the slide
   supports only a weaker claim); wrong (the slide contradicts it); could not verify (the slide
   does not settle it, or could not be read), with the slide's exact words.
2. Missed from the deck: go slide by slide, images included, and list what the slides show about
   the technology that the document does not use, with slide numbers. Say for each why a reader
   of the document might need it, or that it is likely immaterial.
3. Reading cold: places where <reader> could not follow, or where a rating does not match its
   words or the document's own definition.
Do not rewrite for style. Any new fact you bring must cite where you read it and when.
```

## Working file formats

**`decisions.md`**: Decision | Date | Source (conversation date, message) | Applies to.

**`<kind>-rN-triage.md`**: Finding | Checker's verdict (confirmed / weaker form / wrong / could
not verify), copied as reported | Triage (accept / partial / reject), the main session's |
What was opened (slide image, URL with read date, section) | Resulting change, or none. A claim
from a reviewer's memory is rejected as unverified.

**`changes.md`**: Where (section, label) | Kind (changed / added / removed / weakened /
strengthened) | Before | After | Basis | Propagated to (summary, table, body, appendix, glossary,
counters). A "strengthened" row names the owner's go.

**`corrected-claims.md`**: Old wording | Corrected wording | Basis | Date. New text from any
source, reviewers' drafts included, is checked against it before it goes in.

**`checks.md`**: Check | Stage | Answer (yes / no / unknown / not checked) | Evidence | Date.
"Words to distrust" and "deadline facts re-read" each get a row per edit day.
