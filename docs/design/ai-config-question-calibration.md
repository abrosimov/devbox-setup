# Question calibration: deciding versus asking

Written 16 October 2026 after a Pinax design session (Claude Code 2.1.291, `claude-opus-5-5`, effort `medium`, session `eb843d38-f1f1-4e2c-93c8-73cda4fc0570`) in which the model repeatedly returned derivable design questions to the owner. The postmortem is the Katoptron case `docs/katoptron/2026/10/derivable-questions-instead-of-decisions.md` in the Pinax repository. This document states what in this repository's agent configuration must change and why. Paths below are relative to `roles/devbox/files/` unless stated.

## The failure in one paragraph

The owner answered a round of design questions tersely ("MVS like in Go", "no override, at most a go.mod-style replace", "yes, always on disk"). Those answers, read together and with the owner's evident values, settled every remaining point. The model asked more questions anyway, relayed a planner agent's ten open questions wholesale, ended turns with a "What I need from you" list of derivable items, and dropped a working process the owner had stated earlier (formalise a milestone before implementing it). Once challenged, it derived every remaining decision in one turn, which shows that the questions were never necessary.

## Why the configuration produces it

Anthropic's prompting guidance pairs the trigger for checking in ("check in only when different readings would lead to materially different work") with a counterweight ("make routine judgement calls yourself", "do everything that doesn't depend on the answer, then state the assumption"). The shared protocol kept the trigger and dropped the counterweight, and current models follow instructions literally. Measured work on clarification policies points the same way: needless questions lower satisfaction and task quality, while genuinely missing information still justifies asking. Any fix therefore has to be evaluated in both directions. Sources are listed at the end.

## Improvements, each with its reason

1. **Decision rights.** The user owns goals, scope, values, irreversible or externally visible effects, and facts only they have. The agent owns design and implementation choices within a direction the user has set. *Why:* no rule drew this line, so every design sub-question looked like the user's to decide. Where: `dot_ai/USER_AUTHORITY_PROTOCOL.md` §1–§2.

2. **Derive before asking, using the conversation as evidence.** Before any question, check the repository and also the user's earlier answers, the analogies they invoked and the principles they stated; when these settle the matter, state the inference in one line and proceed. *Why:* the protocol's "look it up yourself" step counted only files and documentation as evidence, not the conversation, so answers the user had already given were not used. Where: `dot_ai/USER_AUTHORITY_PROTOCOL.md` §1 step 2.

3. **Replace the "X instead of Y" test with a narrow stop list.** Ask only when the answer cannot be derived, only the user can supply it, and a wrong guess would be costly to undo or would make the work useless. *Why:* the test "if the user meant X instead of Y, would I do anything differently?" answers yes for nearly every design sub-question, and `dot_ai/skills/code-writing-protocols/SKILL.md` hardens it into "if yes, this is an open question". Where: `dot_ai/USER_AUTHORITY_PROTOCOL.md` §1 step 4; `code-writing-protocols`; the closing reminder in all three adapters (`dot_claude/CLAUDE_ADAPTER.md`, `dot_codex/AGENTS.md`, `dot_agy/GEMINI_ADAPTER.md`).

4. **Question budget.** At most one batched question round per topic. After the user answers, derive follow-ups instead of asking again, and give every question a recommended answer that becomes the default. *Why:* batching was only per turn, so each answer could start a new round.

5. **Resolve subagent questions before relaying them.** The orchestrator answers a subagent's open questions itself under these rules and relays only what passes the stop list, each item with a recommendation. The planner's "Open Questions" section becomes "Decisions made", with reasons, plus "Blockers for the user". *Why:* `dot_ai/agents/implementation_planner.md` requires an Open Questions section and says "Questions over assumptions", and the relay rules in `agent-base-protocol`, `agent-communication` and `code-writing-protocols` send those questions straight to the user. The Codex twin `dot_codex/agents/implementation-planner.toml` needs the same change.

6. **Drop topic-based triggers for option menus.** `agent-communication` and `code-writing-protocols` list topics (API design, interface definition, error handling, new structs) as automatic reasons to present options to the user. *Why:* this contradicts the core's narrower rule, which is to show options only when the result differs for the user and nothing they said settles the choice. When options are shown, lead with the decision taken and let the user override it cheaply.

7. **Make "What I need from you" conditional.** The section appears only when work is genuinely blocked on the user. Otherwise the turn ends with a short "Decisions I made" list the user can veto. *Why:* the end-of-turn template made a request section the default closing move, which invites manufactured asks. Where: the core's §4, `response-templates`, `diverge-synthesize-select`, the adapters, and the Stop-hook guard if its logic depends on the wording.

8. **Stated principles and processes persist.** A principle ("software should reduce the user's cognitive load") or a process ("formaliser, executor and reviewer are separate agents") applies to every later decision in the session without the user repeating it. *Why:* the model dropped the owner's formalise-before-implement process within the same session.

9. **Separate design boundaries from gaps in analyses.** "Outside the model by design" and "a real gap" are reported as different categories. *Why:* conflating them delayed the real finding by a turn and produced follow-up questions.

10. **Autonomous run mode.** When the user hands over a multi-step job, each step runs through separate formaliser, executor and reviewer agents, with a fix-and-re-review loop. Open questions are decided inside the run with a documented procedure and a decision log, and the user gets one report at the end. *Why:* `dot_ai/skills/workflow/SKILL.md` offers only "approve after each agent" or manual work.

11. **Tone down absolute wording and prune the always-on files.** Keep MUST and NEVER for true invariants, give each rule its reason, and move procedures into skills. *Why:* Anthropic notes that aggressive emphasis makes current models over-trigger and that explained rules generalise better. The deployed global file is 237 lines against a recommended 200.

12. **Evaluate in both directions.** `dot_ai/skills/code-writing-protocols/evals/evals.json` currently expects "asks for clarification if the request seems too broad", which rewards the failure; it must change. Content evals must cover both "should not ask when the answer is derivable" and "should ask when a costly, non-derivable fact is missing". A replay regression case cut from this session belongs in the `llm-tools-configuration` eval stack, the regression harness these rules are measured against. *Why:* a one-sided fix swings the model into silent guessing.

## Status

Items 1–10 and 12 are being applied to the sources in this repository by an executor agent. That agent edits the files above, keeps the shared rule text identical across engines, and runs the repository's validators and budgets. The replay eval case is being added in `llm-tools-configuration`. Nothing is deployed until the owner runs the playbook.

## Sources

- Anthropic, Prompting Claude Opus 5, task scope: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#task-scope-and-over-verification
- Anthropic, Prompting Claude Opus 5.5, unattended agentic runs (definition of a turn ending that lists non-blocking decisions): https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5#unattended-agentic-runs
- Anthropic, Claude Code memory and CLAUDE.md guidance (size, emphasis, conflicting instructions): https://docs.claude.com/en/docs/claude-code/memory
- Research notes prepared for this change, with per-claim URLs: the Anthropic documentation review, and the practitioner and academic review, including the over-asking measurements in arXiv 2605.07937 and arXiv 2604.14624 and the two-sided Ask-F1 scoring in HiL-Bench.
