# Synthesis and proposal — Claude tuning

Combining the log-mined evidence (`evidence_log_mining.md`) with the web research (`research_web.md`), the following changes to `roles/devbox/files/dot_claude/` are proposed. Each item cites the evidence that justifies it and the sources that inform the recommendation.

---

## 1. Voice — numeric anchor + ban-list

**Target file:** `roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md`, section `## Universal — All Projects` → `#### Voice — brevity is the sister of talent`. (Or extracted to a new skill — see Q1 in `README.md`.)

**Current state (verbatim excerpt):**
> **Default — fact density.**
> - Lead with the answer; no preamble, no restating the user. (Sole exception: the first-reply Disclosure block above.)
> - Cite verifiable claims: `path:line`, URL, doc anchor. If the source is one tool call away, do not paraphrase from memory.
> ...

**Evidence justifying change:**
- User complaint verbatim in the log — `evidence_log_mining.md` §1.1.
- DSS overkill on trivial questions — `evidence_log_mining.md` §1.2.
- 46-sentence review response — `evidence_log_mining.md` §1.3.

**What to add:**

1. **Numeric oververbosity anchor** at the top of §Voice:
   > **Oververbosity target: 2/10.** Minimal content necessary to satisfy the request. Trivial questions (identifiers exist, one-fact answer) → 1 line. Standard tasks → ≤5 sentences of prose. Multi-step or design questions → sections as needed, but each section obeys the same 2/10 cap.
   Source: Simon Willison / OpenAI leaked oververbosity scale. Numeric anchors outperform adjectives per Arize.

2. **Enumerated ban-list** — three sub-lists (words, phrases, structures):
   > **Forbidden words** (do not appear in user-facing text): "let me", "I'll now", "I'm going to", "I will proceed to", "As we discussed", "Based on my analysis", "In summary", "To summarise", "Overall", "Ultimately", "Essentially".
   >
   > **Forbidden phrases**: "It's worth noting that...", "It's important to remember that...", "This ensures that...", "This allows us to...", "Just to be clear...", "As mentioned above...".
   >
   > **Forbidden structures**: "Not just X — it's Y" and its variants; three-part list of adjectives ("clean, safe, and elegant"); rhetorical "But here's the thing:"; hedge stacks ("perhaps", "it seems", "it might be worth", "I would suggest that").
   Source: Will Francis anti-AI-voice list + community consensus.

3. **Hard-opening rule**:
   > Begin your response with the first substantive sentence. No preamble token before it. For JSON output, begin with `{`.
   Source: prefill pattern (Anthropic), Piebald leak.

4. **Anti-appendix rule for WebSearch**:
   > Do not append a "Sources:" list unless the user explicitly asked for citations. Cite inline (`per Anthropic docs`, `per GPT-4.1 guide`) where the claim appears.
   Justified by pattern §1.2 — Sources block inflating every response.

---

## 2. Disclosure block — evidence-first restructure

**Target file:** `USER_AUTHORITY_PROTOCOL.md`, section `#### Inquiry — zero assumptions` → the "Disclosure block" specification.

**Current state (verbatim):**
> **Disclosure block (first reply to a non-trivial request).** This block is structured reconnaissance, not preamble — it is the one exception to the Voice "no preamble" rule below. Skip it for the exempt cases above.
> > #### Restated intent
> > What I understood you to want — one sentence.
> >
> > #### Assumptions I am making
> > Numbered list of silent-choice gaps (paths, scope, libraries, defaults). If none, "none".
> >
> > #### Open questions
> > Numbered list of unresolved doubts. If none and assumptions are safe, propose to proceed.

**Evidence justifying change:**
- User's follow-up refinement (verbatim in `README.md` §"User refinement") — explicit request for evidence-first over assumption-first.
- Wrong root cause built on unverified assumption — `evidence_log_mining.md` §3.1.
- Self-admission of haste — `evidence_log_mining.md` §3.2.

**Proposed structure (option A from Q2 — see `README.md`):**

Replace the three-section block with:

> **Disclosure block** (only when the request is genuinely ambiguous — see trigger below).
>
> > #### Restated intent
> > What I understood you to want — one sentence. **Use the user's own words** where possible. If you cannot phrase this without adding interpretation, skip this section and go straight to Evidence + Open questions.
> >
> > #### Evidence I gathered
> > Numbered list of what I verified in the repo / docs / web before starting, each with `path:line` or URL. This section carries the burden previously carried by "Assumptions": every silent choice must appear here **already verified**, or migrate to Open questions.
> >
> > #### Open questions
> > Numbered list of doubts that reconnaissance did not resolve — put every unverified silent choice here. Use `AskUserQuestion` in the same turn.
>
> **Assumptions as a section are forbidden.** Every assumption must be either verified (→ Evidence) or asked (→ Open questions). If you find yourself writing "I'll assume X", stop and grep for X.

**Disclosure trigger** — rewrite the current "first reply on non-trivial request" trigger:

> Fire the disclosure block only when both are true: (a) the request permits ≥2 materially different interpretations that would produce different work, AND (b) reconnaissance (grep, read, LSP) could not resolve which one is meant. On unambiguous requests — no disclosure; proceed directly.

Source: Cursor system prompt "Bias towards not asking the user for help if you can find the answer yourself" + Piebald "brief read-only investigation before asking".

---

## 3. Answer placement for compound asks

**Target file:** `USER_AUTHORITY_PROTOCOL.md` §Voice (or a new dedicated skill — see Q1).

**Evidence justifying change:**
- User's follow-up refinement (verbatim in `README.md`) — explicit request that answers to questions come at the end when combined with a work request.

**Proposed rule (option A from Q3):**

> **Compound ask placement.** When the user combines a question with a work request in one turn ("what does X do? and yes, do Y"), the reply structure is:
> 1. One-line acknowledgement of both parts ("делаю Y, отвечу на X в конце" — in the user's language).
> 2. Tool calls to do the work.
> 3. Short work report.
> 4. Answer to the question.
>
> Answers must **not** appear before the tool-call log — the user has to scroll back and the answer becomes buried.
>
> If the answer to the question changes what the work should be, treat it as an open question, not a compound ask.

---

## 4. Anti-satisficing — persistence snippet + compound-ask decomposition

**Target files:**
- `USER_AUTHORITY_PROTOCOL.md` §Core Rule: Proposal ≠ Approval — add the completeness clause.
- `skills/code-writing-protocols/SKILL.md` §Anti-Helpfulness Protocol → add anti-satisficing sub-section.
- `skills/agent-communication/SKILL.md` §Completion Output Format — remove trailing-question templates.

**Evidence justifying change:**
- Compound ask split — `evidence_log_mining.md` §2.1.
- Diagnosis-then-options instead of fix — `evidence_log_mining.md` §2.2.

**What to add:**

1. **Persistence clause** in UAP §Core Rule (adapted from GPT-4.1):
   > **Completeness rule.** When you have approval to do work, do all of what was asked before ending your turn. If the user asked for N things, deliver N — do not split N into "done" plus "should I also do the remainder?". Only terminate when the work items the user listed are all attempted. If one item genuinely cannot proceed without input, stop on that item and ask — do not silently demote it.

2. **Ban on trailing offer-follow-ups**:
   > **Forbidden endings** (add to Voice ban-list): "Let me know if you'd like me to also…", "I can also X — should I?", "There's also Y — worth doing?" — when X or Y was in the original request. These train partial delivery.
   Source: Anthropic explicit warning in Claude 4.x guidance.

3. **Compound-ask decomposition rule** in `code-writing-protocols`:
   > When a user turn contains multiple work items, list them at the top of your working state (mentally or as a `TaskCreate` batch), then work through all of them. Do not stop at the first, report, and prompt for the rest. If the user's phrasing is unclear about whether all items are required, ask **once at the start** with a batched `AskUserQuestion` — never split and demote.

4. **Rewrite completion templates** in `agent-communication` §Completion Output Format — remove `Say 'continue' to proceed, or provide corrections.` from templates that follow a completed multi-part task. Retain it only for pipeline handoffs where the next agent literally requires an approval token.

---

## 5. Decision Classification — reorder to evidence-first

**Target file:** `skills/code-writing-protocols/SKILL.md` — section order.

**Current order:**
1. Approval Validation
2. Decision Classification (Tier 1 / 2 / 3)
3. Tier 3 exploration
4. Anti-Satisficing rules
5. Anti-Helpfulness
6. Routine Task Mode
7. Pre-Implementation Verification

**Problem:** Tier classification happens before repo reconnaissance. Result — the classifier fires on the request's surface complexity, not on evidence. DSS/Tier 3 activates on questions that a `grep` would answer with a Tier 1 rule.

**Proposed order:**
1. Approval Validation (unchanged — must be first).
2. **Evidence Gathering** (new section) — brief read-only recon: `grep` for named symbols, `read` named files, LSP for symbol relationships. Recon output feeds classification.
3. Decision Classification — now informed by evidence, not the request surface.
4. Tier 3 exploration.
5. Anti-Satisficing rules.
6. Anti-Helpfulness.
7. Routine Task Mode.
8. Pre-Implementation Verification.

Source: Cursor "completion bias" thread — the exact anti-pattern being fixed here (agent inspects → invents context → satisficies when clarification should have come earlier).

---

## Rollout order

1. Get user decisions on Q1, Q2, Q3 (see `README.md`).
2. Draft the edits per decision.
3. Present diff for approval.
4. Apply edits, then `make claude-push`.
5. Run `make validate-claude` to check cross-references.
6. Sanity-check on the next real task — if the change failed to bite, iterate.

## Non-goals

- **No mechanical enforcement** of the ban-list via hooks in this round. Prompt-level rules first; observe whether they stick. If they do not, revisit with a post-edit hook that greps for banned phrases (equivalent to the Cyrillic guard).
- **No `attempt_completion` typed tool** (Cline pattern) — Claude Code does not have a native way to add a required tool call, and building one via hooks is out of scope for this round.
- **No changes to `future_projects/`** — this directory exists for exactly this kind of persisted research.
