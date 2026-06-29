# `work-bureaucrat` agent — brainstorm snapshot

Status: **idea / brainstorm** — not implemented. Captured 2026-06-25 so it can
be picked up cold later. Pair this file with a fresh session via:

> "Read `future_projects/work-bureaucrat-agent.md`, recap the four open
> decisions, and let's resolve them before designing."

---

## 1. What we want to build

A work-only Claude Code agent that automates the bureaucracy around the
Jira-driven sprint cycle by managing the Obsidian vault at
`/Users/kabrosimov/Work/oiai-work-notes/`. Specifically:

- Pull tickets assigned to the user in the active sprint via the Atlassian
  MCP.
- Scaffold ticket directories in
  `Projects/Programming/{Epics,Tasks}/OICM-XXXX/` from canonical templates.
- Maintain the iteration-review pattern (`iterNN-review.md`) without the
  current pain points (duplicated open-question blocks, scattered ANSWER
  fields, F-items that depend on each other but are physically disjoint).
- Enforce vault conventions (no HTML-tag-on-its-own-line, no graphomania,
  cited claims only, no new terminology without approval, explicit
  Obsidian links, FPF lenses on non-trivial analysis).
- Verify against reality (code, specs, vendor docs) before suggesting
  anything.
- Restate task understanding and request confirmation before non-trivial
  action.

## 2. Hard constraints (non-negotiable)

- **Env guard.** First action every session: check `$MNEMOSYNE_PERISTASEOS`.
  If not `work`, refuse with a redirect to switch profile. Hard stop.
- **Vault root guard.** All write operations confined to
  `/Users/kabrosimov/Work/oiai-work-notes/`. Reads outside (e.g. the
  `oicm-grafana-dashboards/` repo for code refs) are fine via Read/Grep
  with `--add-dir`, but never writes.
- **British English everywhere except citations and explicit Russian
  fields.** Citations from Jira / chat / docs preserved verbatim.
- **No raw HTML on its own line.** `<word>\n...content...\n</word>` breaks
  Obsidian's renderer cumulatively. Wrap placeholders in backticks or
  fenced code blocks. Confirmed by the `mvp-layout.md §7` incident
  (2026-06-23, see OICM-8015 `process.md`).
- **Cite or link.** Every claim about code must cite `file:line`; every
  cross-reference uses `[[wikilinks]]` or relative markdown links.
- **No new terminology without approval.** The `refId A` example in
  `iter25-review.md F-27` introduced jargon with no glossary anchor —
  the agent must `AskUserQuestion` before coining a term.
- **No assumptions.** Verify against code first, then specs, then vendor
  docs, then a targeted WebSearch (pin to the user's library version).
- **Confirm understanding.** First reply on any non-trivial task: disclosure
  block (Restated intent / Assumptions / Open questions), mirroring the
  user's global User Authority Protocol.

## 3. Source material reviewed

Files read during this brainstorm session:

- `Projects/Programming/Epics/OICM-8015/process.md` — most evolved
  layout (phases/, iters, decisions D-NN, corrections C-NN).
- `Projects/Programming/Epics/OICM-8015/iter25-review.md` — the
  pain-point exhibit.
- `Projects/Programming/Epics/OICM-7860/process.md` — slightly different
  layout (api-contract.md, milestones.md).
- Directory listings for both epics' `exploration/`, the `phases/` subdir,
  and `Tasks/` (MLOPS-5777, OICM-6890, OICM-8077).

Patterns observed in both epics:
- `exploration/` (immutable raw discovery, never edited).
- `findings.md` (synthesis, append-only).
- `decisions.md` with stable `D-NN` ids (append-only; supersede via
  `~~strikethrough~~` + forward pointer).
- `process.md` as a resume-protocol document.
- `todo.md` / deferred items.

Pain points concentrated in OICM-8015's iter-review flow:
- One monolithic `iter25-review.md` of ~33 KB.
- ANSWER fields exist twice: once inline at each F-NN, once again in a
  duplicated "Open questions for user (Q-8..)" block at the bottom.
- F-27 and F-28 are logically coupled (the fix to F-27 makes F-28's
  symptom disappear) but live as separate top-level sections with no
  formal link.
- `refId A`, `refId B`, `refId C` used as if they were defined terms; no
  glossary anchor.
- The "open questions" block grew organically because ANSWER fields per
  F were not the source of truth.

## 4. Design dimensions

### 4.1 Iteration model — main pain point

| # | Approach | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | `iterNN/` directory: `_index.md` (auto-generated MoC with summary table + reading order) + one file per finding (`F-26.md`..`F-30.md`). Frontmatter declares `depends-on: [F-NN]` and `blocks: [F-NN]`. No separate "open questions" block — ANSWER lives only inline. A script (`work-iter-status`) parses ANSWER blocks and reports completion. | F-27↔F-28 link is explicit. Zero duplication. Files are readable in isolation. MoC regenerates deterministically. | More files, more navigation. Requires script-generated templates to stay disciplined. |
| B | Monolithic `iterNN-review.md` + template-generator + linter. Drop the separate "Open questions" block; ANSWER always inline. | Fewer files, familiar navigation. | F-27↔F-28 stays flat. File size keeps growing. |
| C | Hybrid: per-F file only when `depends-on`/`blocks` is non-empty, otherwise stays in the monolith. | Flexibility. | Unpredictable structure, breaks the MoC generator. |

If **A**: each F file follows this template (script-generated, not edited
by hand):

```markdown
## F-NN — <short title>

**Selectors / Context.** <filters, cluster, time range>

**User report.** > <verbatim chat quote>

**Observed.** <facts cited as file:line or links; no inference>

**Inferred.** <conclusions drawn from Observed, explicitly separated>

**Assumptions.** <not yet verified; each item has a verification hook>

**Unknown / Needs verification.** <gaps + how to close them>

**Options.** <table: # | What | Pros | Cons>

**Recommended.** <X — one line with the why>

**Depends on / Blocks.** <F-NN, ...>

**ANSWER:** <empty, awaits user>
```

The FPF separation (Observed / Inferred / Assumptions / Unknown) is
baked into the template, not left to the agent's discretion.

### 4.2 Agent shape

| # | Approach | Pros | Cons |
|---|---|---|---|
| **A (recommended)** | Single `work-bureaucrat` agent + 2-3 deterministic CLI scripts (`work-jira-sync`, `work-iter-new`, `work-vault-lint`) + one enforcement skill `work-vault-conventions`. | Less decomposition, one mind keeps project context. Scripts do the deterministic heavy lifting. | Wider responsibility surface = higher drift risk. |
| B | Three specialised agents: `work-jira-puller`, `work-iter-reviewer`, `work-decision-synth` + slash commands `/work-*`. | Narrow specialisation. | Coordination falls on the user. |
| C | No agent — only scripts + an `alwaysApply` skill. | Minimal infrastructure. | No "persona" that remembers the protocol; enforcement leans entirely on hooks. |

### 4.3 Language convention in vault files

| # | Approach | Notes |
|---|---|---|
| **A (recommended)** | Mixed: Russian for `User report`, `ANSWER`, `Inferred`, summary/navigation prose. English for code / PromQL / SQL / Jira citations / vendor doc quotes. Technical terms introduced in English on first mention, then linked to a vault-level glossary. | Reduces cognitive load while preserving citation fidelity. |
| B | Russian only; English terms in backticks. | Most comfortable to read; risk of distorting citations. |
| C | English only (current state). | The user has explicitly rejected this for cognitive load reasons. |

### 4.4 Enforcement strength

| # | Layer | Mechanism |
|---|---|---|
| **A (recommended)** | 3-layer: (1) script-generated templates so a malformed file cannot be produced in the first place; (2) `PostToolUse` hook on `*.md` writes inside the vault — lints HTML-on-newline, broken wikilinks, undeclared terms, orphan ANSWER without a question; (3) skill encoding the qualitative rules for the agent. | Templates make the right thing default. The hook catches manual edits. The skill teaches the agent. |
| B | Scripts + skill, no hook. | Lighter; lint is opt-in via a `make` target. |
| C | Skill only. | Minimal infra; depends entirely on agent discipline. |

## 5. Architecture defaults (no objection expected)

Adopt these unless explicitly overridden when resuming this brainstorm:

- **Env guard** as specified in §2.
- **Vault root guard** as specified in §2.
- **F-block template** (per §4.1) is the canonical shape; scripts generate
  it, the agent fills it in, the linter checks it.
- **No "Open questions" duplication.** ANSWER is the only place an answer
  is captured. The script `work-iter-status iterNN` reports outstanding
  ANSWERs.
- **Auto-generated MoC** (`iterNN/_index.md`) — parsed from frontmatter of
  the F-files. The user does not hand-edit it.
- **Anti-HTML linter rule.** Regex: an opening `<word>` (or `<word
  attr=...>`) on its own line that is not inside a fenced code block.
  Suggestion: wrap in backticks or fence.
- **Anti-graphomania + linking rules** in the skill:
  - Every code reference is `path:line` or `[[anchor]]`.
  - Every borrowed-vocab term (`refId B`, `volcano scheduler`, etc.) is
    either wrapped in `[[glossary#term]]` or has an inline explanation in
    parentheses on first mention in the file.
  - No new terminology without `AskUserQuestion`.
  - Reality check before assertion: code first, then specs, then vendor
    docs (pinned to the relevant library version), then targeted
    WebSearch.
- **Confirm-understanding rule.** First reply to any non-trivial request is
  a disclosure block (Restated intent / Assumptions / Open questions).
- **FPF lenses.** Observed vs Inferred vs Assumption vs Unknown is part of
  the template; the skill references the existing `fpf-thinking` skill for
  trade-off analysis.

## 6. Jira → vault sync (sketch — pull-only, idempotent)

1. `work-bureaucrat sprint-list` — reads the active sprint, lists the
   user's tickets in chat as a table (key / type / status / epic /
   summary). No writes.
2. `work-bureaucrat ticket-init OICM-XXXX` — creates
   `Epics/OICM-XXXX/` or `Tasks/OICM-XXXX/` (chooses by Jira issue type)
   with the minimal canonical structure: `OICM-XXXX.md` with frontmatter
   and the Jira summary + description embedded as an **immutable
   initial-brief section**, plus `process.md` adapted to the ticket
   archetype (epic-with-iterations vs design-epic vs standalone-task).
3. `work-bureaucrat ticket-refresh OICM-XXXX` — re-reads Jira, updates
   **only** sections marked with HTML-comment boundaries:
   `<!-- jira:status -->` ... `<!-- /jira:status -->`. User-authored
   content is never touched.

Three archetypes seen so far:

| Archetype | Example | Layout |
|---|---|---|
| Epic with iterations | OICM-8015 | `phases/`, `iterNN-review.md`, `mvp-layout.md`, `decisions.md`, `findings.md`. |
| Design epic | OICM-7860 | `api-contract.md`, `milestones.md`, `decisions.md`, `findings.md`. |
| Standalone task | OICM-8077 | Minimal: just `OICM-XXXX.md` + a few notes. |

## 7. Concrete artefacts to build

If A / A / A / A is the final decision across the four dimensions:

- **Agent:** `roles/devbox/files/dot_claude/agents/work-bureaucrat.md`
- **Skill:** `roles/devbox/files/dot_claude/skills/work-vault-conventions/SKILL.md`
- **Scripts** (in `roles/devbox/files/dot_claude/bin/`):
  - `work-jira-sync` — sprint-list / ticket-init / ticket-refresh subcommands
  - `work-iter-new` — scaffold `iterNN/` + F-files from a Jira issue + chat dump
  - `work-iter-status` — parse ANSWER blocks, report outstanding
  - `work-vault-lint` — run all vault-wide checks (HTML-newline, broken wikilinks, undeclared terms, orphan ANSWER, missing citations)
- **Hook:** add a `PostToolUse` entry in
  `roles/devbox/files/dot_claude/hooks.json` that calls `work-vault-lint`
  on writes inside `oiai-work-notes/`.
- **Slash command (optional):** `/techne-work-init`, `/techne-work-iter`,
  `/techne-work-status` if A.2 (agent) is chosen and pipeline-style
  invocation is preferred.
- **Templates** committed alongside scripts (script reads them):
  - `templates/work-vault/process-epic-iterations.md`
  - `templates/work-vault/process-epic-design.md`
  - `templates/work-vault/process-task.md`
  - `templates/work-vault/iter-finding.md` (the F-NN template)
  - `templates/work-vault/iter-index.md` (the MoC template)

## 8. Locked decisions (2026-06-29)

1. **Iteration model — A.** Per-F files (`iterNN/F-NN.md`) plus an
   auto-generated `_index.md` MoC. `depends-on` / `blocks` in frontmatter.
   ANSWER lives only inline; the separate "Open questions" block is
   forbidden. `work-iter-status` parses ANSWERs and reports completion.
2. **Agent shape — A.** One `work-bureaucrat` agent + CLI scripts
   (`work-jira-sync`, `work-iter-new`, `work-iter-status`,
   `work-vault-lint`) + one skill `work-vault-conventions`.
3. **Language convention — A.** Mixed: Russian for `User report`,
   `ANSWER`, `Inferred`, summary/navigation prose. English for code /
   PromQL / SQL / Jira citations / vendor doc quotes. Technical terms in
   English on first mention, linked to a vault glossary.
4. **Enforcement strength — A.** Three layers: script-generated templates,
   `PostToolUse` hook on `*.md` writes inside the vault, and the skill
   for qualitative rules.

## 9. Implementation outline (rough)

Order of work once decisions are locked:

1. Lock decisions in `decisions.md` adjacent to this file (or in the
   chat that follows the resume prompt — then back-propagate here).
2. Write templates first (Markdown only, deterministic).
3. Write `work-vault-lint` second (it defines the contract).
4. Write `work-iter-new` and `work-iter-status` (they emit
   linter-compliant output).
5. Write `work-jira-sync` (Atlassian MCP integration, idempotent).
6. Write the skill (`work-vault-conventions`) — qualitative rules + how
   the agent invokes the scripts.
7. Write the agent (`work-bureaucrat`) — pulls skill, knows scripts,
   knows the env / vault guards.
8. Wire the hook in `hooks.json` (only after lint is stable on the
   existing vault — run it against current files first to size the
   backlog).
9. Migrate existing iter-review files to the new shape opportunistically
   (not as a single big-bang refactor — touch what you visit).

## 10. Glossary the agent must populate over time

Establish a top-level vault note (`Projects/Programming/glossary.md`)
that the linter cross-references. Initial seed entries needed (from
already-observed jargon in OICM-8015):

- `refId` (Grafana panel query reference letter)
- `joinByField` (Grafana transformation)
- `excludeByName` / `renameByName` / `indexByName` (Grafana organize
  transformation)
- `DCGM` (NVIDIA Data Center GPU Manager exporter)
- `volcano scheduler` (batch scheduler used in the platform)
- `GPU_I_PROFILE` (DCGM label for MIG profile)

The skill rule is: if an undefined term is detected by the linter on
write, the agent must add it to the glossary in the same edit and link
the first mention.

---

## Appendix — example of the current pain point

Excerpt from `OICM-8015/iter25-review.md` showing the ANSWER duplication
that the new model eliminates:

> Each F-block (F-26..F-30) ends with `**ANSWER (for next session):**`
> as an inline placeholder.
> Then a separate `## Open questions for user (Q-8..)` section at the
> end of the file repeats each F's open question as `Q-8`..`Q-15` with
> its own `**ANSWER**:` field. The user filled in the latter, leaving
> the former empty — the file ended up with two parallel answer
> surfaces and no single source of truth.
