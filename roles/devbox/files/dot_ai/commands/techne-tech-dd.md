---
description: Write or continue an initial technical due diligence from sell-side material (a deck plus public sources) for non-technical decision makers
argument-hint: "[deck or DD folder] [step=<n>]"
---

You are running an initial technical due diligence (DD) with the `tech-due-diligence` skill.

## Steps

### 1. Parse the arguments

`$ARGUMENTS` may name the deck file or an existing DD folder, and `step=<n>` to run one stage of
the skill and stop. An existing DD folder with a `decisions.md` means a DD in progress: read it
before asking anything.

### 2. Collect what is missing

Read the conversation and, for a DD in progress, `decisions.md`. Ask only for what neither gives,
in one batched round, each question with a recommended answer:

- **DD stage**: which phase of the deal the document serves, for example a first look before any
  access to systems. The skill covers the initial phase from sell-side material; for a later phase
  with access to systems or code, say that it is outside the skill's model and ask whether to
  proceed on the material alone.
- **Deal type**: investment, acquisition, vendor selection or partnership, because it sets which
  consequences matter to the business.
- **Reader**: who reads the document and what they must decide.

If the deck or the DD folder is not named either, ask for it in the same round. Do not ask for
anything the skill can derive.

### 3. Run the skill

Load the `tech-due-diligence` skill and follow it from "Start: the workspace", recording the
answers from step 2 in `decisions.md` with their date and source. With `step=<n>`, run that stage
and stop; otherwise continue from the first stage whose done condition is not met.

### 4. Report

Report once, after every dispatched agent has returned, in the form the skill's "Reporting and
delivery" section gives.
