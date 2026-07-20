# Web research — verbosity, anti-satisficing, evidence-first patterns in LLM coding agents

**Method:** sub-agent web-searched and web-fetched across multiple source types — official Anthropic and OpenAI docs, leaked system prompts, arXiv research, community discussions (Cursor forum, HackerNews, LangChain blog), and individual practitioner posts (Simon Willison, Will Francis).

**Scope:** three themes matching the user's complaint — verbosity control, anti-satisficing / task completion, evidence-first vs assumption-first.

---

## Topic 1 — Verbosity / graphomania control

### Sources

| Source | URL | Contribution |
|--------|-----|--------------|
| Anthropic prompting best practices | `https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices` | Claude 4.x is "literal": it stops inferring intent and does exactly what you ask, so brevity must be requested explicitly |
| Piebald-AI leaked Claude Code system prompt | `https://github.com/Piebald-AI/claude-code-system-prompts` | Verbatim internal rules: "keep user-facing updates readable and outcome-first", "answer directly after work completes", "match response format to task complexity", "write a short past-tense summary label for completed tool calls" |
| Simon Willison — leaked ChatGPT oververbosity scale | `https://simonwillison.net/tags/llm/` | OpenAI internally uses a 1–10 numeric knob; `1` = "minimal content necessary, avoiding extra detail". Explicit numeric anchoring works better than adjectives |
| Will Francis — How to stop Claude writing like an AI | `https://willfrancis.com/how-to-stop-claude-writing-like-an-ai/` | Most copy-pasteable anti-AI-voice prompt on the open web: banned-word list, banned phrase list, banned structures like "Not just X — it's Y" |
| Arize — CLAUDE.md best practices from prompt learning | `https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/` | Bloated system prompts cause rules to be silently dropped; ask "would removing this line cause a mistake?" and cut otherwise |

### Techniques that work (copyable formulations)

1. **Numeric verbosity anchor** rather than adjective: `Oververbosity = 2. Minimal content necessary to satisfy the request.`
2. **Ban-lists over instruction** — enumerate forbidden words/phrases/structures (Will Francis pattern). Bans are more enforceable than positive style guidance.
3. **Prefill / hard opening** — `Skip the preamble. Begin your response with the first substantive sentence.` For JSON output: `Begin with {.`
4. **Explicit anti-restatement** — `Don't restate the question back before answering it.`
5. **Format-match rule** — `Match response format to task complexity.` This suppresses gratuitous headers/bullets on trivial answers. (Claude Code's own internal prompt.)
6. **End-of-turn cap** — `End-of-turn summary: 1–2 sentences maximum — what changed, what is next.` Present in current UAP; matches Claude Code's internal wording.

### Anti-patterns (do not work)

- **Vague "be concise"** — Claude 4.x complies for one turn then drifts back. Needs quantified caps (sentences / lines / tokens).
- **Long "voice" preambles in CLAUDE.md** — the more you write, the more Claude ignores. Arize's finding: bloat causes rule loss.
- **Positive-only style rules** ("write clearly, professionally") — reads as permission for corporate-speak. Bans work; positive style rules do not.
- **Emphasis inflation** — using `IMPORTANT` / `YOU MUST` on every rule dilutes the signal. Anthropic explicit warning.

---

## Topic 2 — Anti-satisficing / task completion

### Sources

| Source | URL | Contribution |
|--------|-----|--------------|
| OpenAI — GPT-4.1 Prompting Guide | `https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide` | The canonical "persistence" snippet: "keep going until the user's query is completely resolved, before ending your turn... Only terminate your turn when you are sure that the problem is solved." Reported +20% on SWE-bench Verified |
| Cursor forum — "The Completion Bias" thread | `https://forum.cursor.com/t/the-completion-bias-ai-sub-agents-bypassing-logic-to-finish-tasks/160115` | Practitioner-discovered fix: **reorder** instructions so "stop and ask" is step 1, before repo inspection. Also: fail-fast `NEEDS_INPUT: <reason>` sentinel instead of "please pause and ask the user" |
| Cline — leaked system prompt & `attempt_completion` tool | `https://cline.bot/blog/system-prompt-advanced` | Cline forces completion through a typed tool whose schema demands "Formulate this result in a way that is final and does not require further input from the user. Don't end your result with questions or offers for further assistance." |
| Anthropic — Effective context engineering for AI agents | `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents` | Claude 4.x takes specs literally: "You get exactly what you ask for, not what you meant." Completeness must be quantified |
| arXiv 2512.12730 — NL2Repo-Bench | `https://arxiv.org/pdf/2512.12730` | Two named failure modes: **Early Termination (Overconfidence)** = agent invokes `finish()` before ready; **Non-Finish (Passive Failure)** = agent halts awaiting confirmation instead of proceeding |
| Cursor blog — Agent best practices | `https://cursor.com/blog/agent-best-practices` | "Provide verifiable goals" via typed languages, linters, tests. "TDD-first" gives a machine-checkable completion criterion |

### Techniques that work

1. **GPT-4.1 persistence trio** (persistence + tool-calling + planning) is the most cited, measured, portable snippet. The persistence line copies straight into a system prompt.
2. **Quantified completeness** rather than "thorough". Anthropic's example: "implement as many relevant features and interactions as possible. Don't just build a basic version — implement a fully functional solution."
3. **Structured completion tool** (Cline pattern) — make the agent call `attempt_completion(result, demo_command)` where the schema forbids trailing questions. Turns "am I done?" into a typed contract.
4. **External completion gate** — run tests / typecheck / lint before allowing the "done" claim. Cursor: "give agents clear signals for whether changes are correct."
5. **Scope-drift ban** — "Do not refactor or restyle code outside the success criteria, even if it looks improvable" (Cline prompting guides).
6. **Reorder before repo inspection** — put ambiguity checks as literal step 1, before any file reads. Otherwise the agent inspects the repo, invents context, and satisfices.

### Anti-patterns

- **"Please pause and ask if unclear" in sub-agents** — sub-agents have no user channel; they guess. Use `NEEDS_INPUT: <specific missing thing>` sentinel that the parent handles. (Cursor team advice.)
- **Ending on "Let me know if you'd like me to also do X"** — this literally trains partial delivery. Anthropic explicit: rewrite as "Make these edits" not "Can you suggest some changes?".
- **Relying on prompt-only enforcement** — Knostic / Cursor community consensus: "Prompts are advisory, not deterministic. External runtime gates (tests, hooks, typecheck) are required."
- **Fighting laziness through follow-up prompts** — Cursor blog: revert, refine the plan, re-run. Cheaper than repair.

---

## Topic 3 — Evidence-first vs assumption-first

### Sources

| Source | URL | Contribution |
|--------|-----|--------------|
| OpenAI — GPT-4.1 Prompting Guide (tool-calling snippet) | `https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide` | "If you are not sure about file content or codebase structure pertaining to the user's request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer." |
| arXiv 2603.26233 — "Ask or Assume? Uncertainty-Aware Clarification-Seeking in Coding Agents" | `https://arxiv.org/html/2603.26233v1` | UA-Multi scaffold hits 69.4% on under-specified SWE-bench Verified vs 70.8% with full spec. Well-calibrated agents ask more on hard tasks, less on easy ones. Best empirical evidence that evidence-seeking recovers most of the gap |
| Anthropic — Effective context engineering for AI agents | `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents` | Advocates "just in time" context: maintain lightweight identifiers (file paths, queries) and load on demand. Warns against "vague, high-level guidance that... falsely assumes shared context." |
| Cursor 2.4 native clarification feature + community discussion | `https://forum.cursor.com/t/cursor-2-4-clarification-questions-from-the-agent/149406/1` | Agent can now ask non-blocking clarifying questions and keep working. Community pattern: batched multiple-choice questions rather than one-by-one |
| Cursor system prompt (Sshh gist) | `https://gist.github.com/sshh12/25ad2e40529b269a88b80e7cf1c38084` | Verbatim: "Bias towards not asking the user for help if you can find the answer yourself" and "if you've performed an edit that may partially satiate the USER's query, but you're not confident, gather more information or use more tools before ending your turn." |
| Piebald-AI leaked Claude Code prompt | `https://github.com/Piebald-AI/claude-code-system-prompts` | "Brief read-only investigation before asking the user clarifying questions." Order matters: recon first, then ask |

### Techniques that work

1. **Two-tier bias** (Cursor's exact wording) — first try to answer with tools, ask user only for genuine ambiguity. Prevents both extremes (guess-everything and interrupt-everything).
2. **Recon before question** (Claude Code's exact wording) — "brief read-only investigation before asking the user clarifying questions." The agent must have already tried `grep`/`read`.
3. **Batched MCQ clarification** — the pattern DeepAgents / Cursor 2.4 both landed on. Bundle all doubts into one multi-choice ask; do not drip questions.
4. **Reorder-to-step-1** (Cursor completion-bias thread) — put clarification / context-check before repo inspection, otherwise the agent invents context.
5. **Persistent scratch state** — Anthropic recommends `claude-progress.txt` + `init.sh` + initial commit so fresh contexts inherit evidence rather than re-guess.
6. **Explicit anti-guess line** (GPT-4.1) — `do NOT guess or make up an answer`. Used verbatim by OpenAI, portable to any system prompt.

### Anti-patterns

- **One-by-one clarification** — kills flow, users abandon. Batched MCQ is empirically preferred (LangChain / DeepAgents thread).
- **"Ask if unclear" without recon requirement** — the agent asks about things a `grep` would answer, or worse, does not ask and guesses.
- **Loading all files upfront ("just in case")** — Anthropic direct warning: depletes context budget. Use identifiers + lazy load.
- **Silent inference on ambiguous paths / names** — the classic Cursor bug (agent picks a base branch instead of asking). Fix: fail-fast `NEEDS_INPUT` sentinel.
- **Vague questions** ("Anything else I should know?") — no signal, users skip. Questions must contain 2–4 grounded options. (Matches current UAP Voice protocol.)

---

## Cross-cutting observations

- The **GPT-4.1 persistence + tool-calling + planning triad** is the single highest-leverage snippet across all three topics. Anthropic's Claude 4.x guidance overlaps significantly but is less quotable.
- Every serious agent framework (Claude Code, Cursor, Cline, Aider) has converged on **typed completion contracts** (`attempt_completion`, `finish()`, structured commit) rather than free-text "I'm done" — the schema itself blocks satisficing.
- The **"reorder ambiguity checks to step 1"** trick from the Cursor completion-bias thread is the most under-discussed practical finding — worth encoding as a skill rule.
- **Bans > positive guidance.** Every source that measured found enumerated forbidden words / phrases / structures more effective than positive style descriptions.
