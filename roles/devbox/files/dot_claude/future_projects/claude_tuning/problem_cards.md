# Problem Cards — Claude Tuning

**Status:** pre-articulation cues, not routes.
**Date:** 2026-07-21.
**FPF grounding:** shaped as `U.PreArticulationCuePack` (A.16.1). Each card preserves a cue nucleus with anchors, witnesses, contrasts, and directional hints — it deliberately does **not** decide the route. Route selection is the next step (see B.4.1 / follow-up to `synthesis_and_proposal.md`).

## How to read a card

- **Nucleus** — the minimum preserved core: what exactly is kept visible.
- **Anchor** — where in the current `dot_claude/` config the cue sits.
- **Witnesses** — evidence sources that ground the cue.
- **Contrasts** — adjacent problems this card is NOT about.
- **Directional hints** — early candidate directions for a fix; explicitly not selected.

## Card set (v1)

Five cards. Derived from the five distilled requirements in `README.md`, with one addition (PC3, surfaced in the 2026-07-21 conversation) and one merge (original verbosity + placement → PC5).

---

### PC1 — Evidence-seeking gap

- **Nucleus.** The model makes claims about the repo, code behaviour, or user intent without probing first. The discipline needed is **seek**, not **display**.
- **Anchor.** `USER_AUTHORITY_PROTOCOL.md` §Inquiry — "zero assumptions". Declares intent but mandates *showing* assumptions in the Disclosure block; imposes no duty to *find* them.
- **Witnesses.** `evidence_log_mining.md` §3.1 (wrong root cause built on unverified assumption); §3.2 (self-admission of haste).
- **Contrasts.** NOT PC2 — PC1 is about facts verifiable in repo/docs/web; PC2 is about parsing the user's ask itself.
- **Directional hints.** Retire the "Assumptions I am making" slot. A passive "Evidence I gathered" replacement just renames the slot. Closer: an obligation *"if a claim is verifiable in one grep / read / LSP call, verify before asserting"* — with no mandatory in-reply slot.

---

### PC2 — Intent verification (understanding-check, not paraphrase)

- **Nucleus.** The model paraphrases the ask and drifts from its letter. What is needed is a check *"did I parse the task correctly?"* — not literary reformulation.
- **Anchor.** `USER_AUTHORITY_PROTOCOL.md` §Inquiry — "Restated intent — one sentence". The word *restated* invites reformulation.
- **Witnesses.** User verbatim (`README.md` §"User refinement"): *«частенько бывает так, что в restate ты прям перевираешь мои слова»*.
- **Contrasts.** NOT self-reflection, NOT display of attentiveness. Functional contract: *"here is my parse — correct me before I act on it"*.
- **Directional hints.** Rename "Restated intent" → **"Understood ask"**: quote-back of the imperative part + a short concrete parse (*"→ file X gains method Y"*). Fires only when the parse is non-trivial; skip on trivial asks (single-file rename, obvious one-liner).

---

### PC3 — Role-boundary violation (model does agent's work)

- **Nucleus.** The model edits `.go` / `.py` / `.ts` / `.tsx` directly instead of routing through `/techne-implement`. Consequence: both overreach *and* underreach — an agent would enforce standards and scope; the raw model has neither.
- **Anchor.** `CLAUDE.md` §Agent Pipeline: *«For ANY modification to .go, .py, .ts, .tsx files ... use /techne-implement. NEVER use Edit/Write/MultiEdit directly»*. Rule exists; compliance is weak.
- **Witnesses.** User's 2026-07-21 turn: *«часто он делает лишнее или недостаточное — в т.ч. потому что не запускает агентов, а сам пытается править код»*. **Evidence gap** — this pattern was NOT surfaced in `evidence_log_mining.md`; the miner should re-run with a new filter targeting Edit / Write on code extensions outside a subagent context.
- **Contrasts.** NOT PC4 (scope closure). PC4 asks *"did the model finish the ask?"*; PC3 asks *"was the model even the right actor?"*. Orthogonal.
- **Directional hints.** Prompt-level rule already exists and is ignored → a mechanical brake is needed. `bin/bash_decision_gate.py`-style: PreToolUse hook on Edit / Write / MultiEdit for code extensions that denies unless the invocation is inside a subagent chain. Prompt reinforcement alone is insufficient.

---

### PC4 — Scope closure ambiguity

- **Nucleus.** The model delivers part of the ask and asks about the remainder — where the remainder was in the original ask. No explicit *"match reply scope to ask scope"* rule exists.
- **Anchor.** `USER_AUTHORITY_PROTOCOL.md` §Core Rule: Proposal ≠ Approval — focused on *don't start without approval*; silent on *once started, close all items in the ask*.
- **Witnesses.** `evidence_log_mining.md` §2.1 (compound ask split); §2.2 (diagnosis-then-options instead of fix).
- **Contrasts.** NOT PC3 (that's about delegation choice). NOT PC5 (that's about reply layout, this is about work content).
- **Directional hints.** The persistence clause from `synthesis_and_proposal.md` §4 is the right direction. Extend it: before end-of-turn, the model builds a checklist from the ask and self-checks completeness. Any incomplete item is either finished, or explicitly surfaced in Open questions with a reason.

---

### PC5 — Response geometry (reader ergonomics)

- **Nucleus.** Reply format optimises for *"look thorough"*, not *"reader convenience"*. Symptoms: verbose preamble, ceremony sections, answer to a compound ask floats *above* the tool-call log instead of after it.
- **Anchor.** Three sources of ceremony, each demanding early real-estate: `USER_AUTHORITY_PROTOCOL.md` §Voice, §Inquiry disclosure block, §Checkpoint format.
- **Witnesses.** User verbatim: *«ответ ты мне выдаешь не в самом конце, а в самом начале, а дальше бесконечный лог из tool-calls»*. Also `evidence_log_mining.md` §1.2 (DSS overkill), §1.3 (46-sentence review).
- **Contrasts.** NOT PC1 / PC2 (those are about content). Purely about layout + brevity.
- **Directional hints.** Three parallel treatments (independent):
  1. Compound-ask placement rule (keep `synthesis_and_proposal.md` §3).
  2. Retire the checkpoint-format template — `**[Awaiting your decision]**` currently appears as ornament, including where the choice is obvious.
  3. The ban-list from `synthesis_and_proposal.md` §1 is suspect (theatre-against-theatre). Replace with one line: *"Reader sees results, not process."*

---

### PC6 — Cross-link discoverability gap

- **Nucleus.** Rules exist in isolation. When one fires, the model has no structural way to discover related rules. Alexander's *related-patterns* slot — the single element of his framework that survives modern scrutiny — is the one thing our current config lacks.
- **Anchor.** 40 skills + 28 agents + 22 commands + hooks — none link to each other structurally. Prose mentions (*"see X skill"*) exist, but there is no typed graph and no validated connections. `make validate-claude` checks existence, not topology.
- **Witnesses.** `research_pattern_language.md` §Bucket 1 (Salingaros: *"connections make a language rather than a catalogue"* [13]); §Practical middle-grounds (Cursor `.mdc` `applyTo` [30], Continue.dev `config.yaml rules:` [59] — both support structural linking; ours does not).
- **Contrasts.** NOT PC1 (facts, not rules). NOT PC7 (count, not connections).
- **Directional hints.** Routes R1 + R2 from `research_pattern_language.md` — add `related: [...]` to skill/agent frontmatter; generate `SKILLS-INDEX.md`. Extend `make validate-claude` to validate `related:` references (drift protection).

---

### PC7 — Instruction budget invisible

- **Nucleus.** Frontier models reliably follow ~150-200 instructions ([research 45]). Our config has ~90 artefacts (40 skills + 28 agents + 22 commands), each carrying several embedded rules. **Nobody counts.** The config may already be silently over-budget — in which case rule-loss occurs not because a rule is badly written, but because it is the N+1-th.
- **Anchor.** `USER_AUTHORITY_PROTOCOL.md` has ~15 sections each with multiple rules; every skill carries its own ruleset; commands encode flows; hooks encode rules mechanically. No aggregate count exists anywhere in the repo.
- **Witnesses.** Anthropic CLAUDE.md guidance ([research 45]): *"150-200 instructions"*. IFScale ([research 32, 33]): 68% accuracy at 500 concurrent instructions. The existence of `make eval-skills` indirectly attests that some skills already misfire — poor triggers vs over-budget cannot be distinguished without accounting.
- **Contrasts.** NOT PC5 (verbosity of a single output). PC7 concerns aggregate rule-count in always-on context.
- **Directional hints.** Instrument — a script counting imperative statements per artefact; publish a rules-budget report. If over-budget, migrate always-on skills to trigger-loaded (progressive disclosure per Anthropic Skills [research 26]).

---

### PC8 — Always-on load asymmetry

- **Nucleus.** Several skills carry `alwaysApply: true` and load into every session regardless of task context. Example: `go-engineer` firing when the current session is about editing agent definitions in `dot_claude/` — dead weight consuming attention budget.
- **Anchor.** `skills/*/SKILL.md` frontmatter — a subset of skills declare `alwaysApply: true` without gating on task type. The `editing-claude-config` skill exists specifically *because* the always-on set is not curated for config-editing sessions.
- **Witnesses.** Anthropic Skills progressive-disclosure guidance ([research 26]) — three levels, only level-1 (frontmatter) is meant to be always-on. Context rot at ~3000 tokens ([research 56]) applies to always-on load specifically.
- **Contrasts.** Related to PC7 (both concern rule-count) but distinct: PC7 is about total inventory across the config; PC8 is about the always-on subset specifically. PC7 could be resolved by trimming per-artefact rules; PC8 by moving artefacts off the always-on shelf.
- **Directional hints.** Audit the `alwaysApply: true` set — for each skill, verify *"does this fire correctly for at least 80% of sessions?"*. If no — convert to trigger-based via description-tuning.

---

## Open questions on the card set

- **PC5 merge.** Verbosity (original requirement #1) and answer placement (#5) were merged here because both concern output shape. Is the merge acceptable, or should they split back into PC5a (brevity) and PC5b (layout)?
- ~~**Missing cards.**~~ **Resolved 2026-07-21.** Three additional cues surfaced by `research_pattern_language.md` were carded: PC6 (cross-link discoverability), PC7 (instruction budget), PC8 (always-on load).
- **PC3 evidence gap.** The delegation-failure pattern lacks a mined-log witness. Should we re-run `evidence_log_mining.md` with a new filter, or is the user's testimony sufficient?

## Next step (route selection, not this file)

Once the card set is agreed, move from cue packs (this file) to route candidates (FPF `B.4.1` — `RoutedCueSet`). That is where `synthesis_and_proposal.md` gets revised into a route-selected plan, incorporating the pattern-language reformatting research currently in flight (`research_pattern_language.md`, pending).
