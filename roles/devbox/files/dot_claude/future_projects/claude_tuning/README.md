# Claude Tuning — verbosity, completion, evidence-first

**Status:** W1 complete (RI1 → RI2). W2 opened (`route_W2_structural.md`) with resolved scope from Q-RI2-1..3; awaits Q-W2-1..3 decisions before frontmatter batch begins.
**Date opened:** 2026-07-20. **Last update:** 2026-07-21.
**Trigger:** user complaint about verbose responses, 60%-completion pattern, misrepresented restated intents.

## Session handoff — how to resume

1. Read this `README.md` (index).
2. Read `problem_cards.md` (8 problem cards as FPF cue packs — PC1-PC8).
3. Read `routed_cue_set.md` (13 candidate routes across 4 families, coverage matrix, wave rollout — reflects W1 completion).
4. Read `route_RI1_rules_budget.md` + `rules_budget_baseline.md` (W1 output — RI1 script + baseline).
5. Read `route_RI2_always_on_audit.md` (W1 output — RI2 audit with demotion recommendations).
6. Open `route_W2_structural.md` (already scoped: RS1 + RS2 + RS5 + RI2 demotions + trigger-consistency validator). Decide Q-W2-1..3, then execute the sequencing inside the file.

## User complaint (original, verbatim)

> В последнее время я замечаю что ты (как модель) пишешь очень длинные тексты, с кучей воды и страстью к графомании. Давай проанализируем содержимое dot_claude, сделаем исследование в интернете и подумаем как сделать тебя менее говорливым (в тч повторы моих же сообщений и пр).
>
> Второй момент, который меня стал смущать, ты частенько делаешь задачу на 60%, останавливаешься, рапортуешь что все готово, но есть ещё пара мест где можно улучшить. И спрашиваешь стоит ли их улучшать? Когда в оригинальной просьбе они были.

## User refinement (follow-up, verbatim)

> Ещё одно дополнение, я в последнее время часто наблюдаю именно вот такой паттерн:
> ```
> Restated intent
> .....
> Assumptions I am making
> .....
> ```
> Сегодня я вижу что restate сделан лучше чем обычно, но говоря исследование в интернете я имел ввиду именно интернет, и официальная документация от Anthropic — это только один из источников, а их нужно больше. Что в dot_claude нужно лезть — это очевидно. Но частенько бывает так, что в restate ты прям перевираешь мои слова.
>
> А вот Assumptions — лучше сразу уточнить у пользователя или пройтись по репозиторию. Seek for evidence before assume. А то получается мне в самом начале диалога уже приходится править допущения.
> На любой assumption — ищем evidence. Нашли — отлично, не нашли — добавляем в список вопросов к пользователю в конце ответа.
>
> Это кстати важно, бывает так, что я пишу что-то вроде "а что там за штука в таком файле? и да, согласен с твоими правками, делай". И ответ ты мне выдаешь не в самом конце, а в самом начале, а дальше бесконечный лог из tool-calls, etc. Не очень удобно скроллить каждый раз.

## Distilled requirements

1. **Reduce verbosity.** No graphomania, no restatement of user's own words, no filler.
2. **Complete the task as asked.** Do not deliver 60% and ask about the remaining 40% when that 40% was in the original request. Do not split compound asks.
3. **Do not misrepresent the user in restated intents.** If restating, be precise; when in doubt, ask.
4. **Assumptions must be evidence-backed.** Every silent choice — either verified in the repo (grep, read, LSP), or promoted to an explicit open question at the end of the reply. No unverified assumptions.
5. **Answer placement for compound asks.** When the user combines a question with a work request, the answer must appear at the end (after work is reported), not before the tool-call log.

Refined and expanded into 8 problem cards — see `problem_cards.md`.

## File layout

| File | Contents |
|------|----------|
| `README.md` | This file — index, user complaint, distilled requirements, state log, session handoff |
| `evidence_log_mining.md` | Sub-agent report: failure patterns mined from `~/.claude/projects/` session logs |
| `research_web.md` | Sub-agent report: initial web research on verbosity control, anti-satisficing, evidence-first patterns |
| `synthesis_and_proposal.md` | Initial 5-edit proposal with 3 open questions — **partially superseded** by the RoutedCueSet |
| `problem_cards.md` | 8 problem cards (PC1-PC8) as FPF `U.PreArticulationCuePack` — the cues from which routes are derived |
| `research_pattern_language.md` | Sub-agent report: 82-source web research on the Pattern-Language reformatting hypothesis — **verdict: no wholesale rewrite; lightweight hybrid** |
| `routed_cue_set.md` | FPF `RoutedCueSet` (B.4.1) — 13 candidate routes across 4 families, coverage matrix, wave rollout plan |
| `route_RI1_rules_budget.md` | Deep-dive on route RI1 — completed; contains baseline results and per-artefact notes |
| `rules_budget_baseline.md` | Machine-generated baseline from `make rules-budget --baseline` (2026-07-21) |
| `route_RI2_always_on_audit.md` | Deep-dive on route RI2 — always-on skill audit with per-skill keep/demote/split verdicts (Q-RI2-1..3 resolved) |
| `route_W2_structural.md` | Deep-dive on W2 — RS1 + RS2 + RS5 + folded-in RI2 demotions + trigger-consistency validator (Q-W2-1..3 pending) |

## Open questions (superseded — kept for deliberation history)

The original Q1-Q3 below are **superseded** by the RoutedCueSet framework in `routed_cue_set.md`. Do not re-answer them; use the newer frame.

- **Q1 (superseded) — Where to place anti-verbosity rules.** Now handled by RC4 (retire ban-list; replace with one line) + RS1 (per-artefact `problem:` field for discovery).
- **Q2 (superseded) — How to reshape the disclosure block.** Now handled by RC1 (Understood ask) + RC2 (seek evidence).
- **Q3 (superseded) — Handling compound asks.** Now handled by RC6 (answer at end of reply).

Live open questions now live inside each route deep-dive file — see `route_RI1_rules_budget.md` §Open questions for the current set (Q-RI1-1 to Q-RI1-5).

## State log

- **2026-07-20.** Complaint captured. Log-mining + initial web-research sub-agents dispatched. `synthesis_and_proposal.md` drafted with a 5-edit proposal and 3 open questions (Q1-Q3).
- **2026-07-21.** FPF `PROBLEM-SHAPING` re-frame. The 5 initial cues turned into problem cards (`problem_cards.md`, PC1-PC5). Pattern-Language reformatting hypothesis investigated via 82-source research (`research_pattern_language.md`); verdict: no wholesale rewrite, adopt a lightweight hybrid. 3 additional cues surfaced (PC6-PC8). Route framework built (`routed_cue_set.md`) — 13 candidate routes across 4 families with a wave-based rollout plan. W1 selected (RI1 rules-budget → RI2 always-on audit); RI1 deep-dive opened (`route_RI1_rules_budget.md`) with 5 open questions to resolve before implementation.
- **2026-07-21 (later).** W1 executed end-to-end. Q-RI1-1..5 resolved (D, D, as-listed, A, A). Implemented `bin/rules_budget.py` + `bin/test_rules_budget.py` (37 tests green, <1s runtime, stdlib only). Added `make rules-budget` Makefile target. Captured `rules_budget_baseline.md` — 119 always-on rules, verdict `under` the 150-200 budget. Ran RI2 static audit (`route_RI2_always_on_audit.md`) — recommendation: demote 3 of 5 always-on skills (`code-comments`, `lint-discipline`, `lsp-navigation`) for 46-rule saving; flag `project-preferences` for split in W3. Q-RI2-1..3 resolved (W2 batch, W3 incremental split, add trigger-consistency validator in W2). Opened `route_W2_structural.md`: scope = RS1 + RS2 + RS5 + RI2 demotions + new validator; Q-W2-1..3 pending user decision.
- **2026-07-21 (evening).** W2 Phase 1a (LSP merge) + Phase 1b (demote `code-comments` / `lint-discipline`) committed in `5f4d4b4`. W2 infrastructure completed the same day: Phase 2a preconditions (6 agents), `scripts/apply_w2_frontmatter.py` + tests, `bin/validate_config.py` extended with `related-links` + `trigger-consistency` checks + tests, `bin/build_skills_index.py` + tests + `make skills-index` target, `install_configs.yml` Block 2 wired for `SKILLS-INDEX.md`, initial index generated. Subagent authored `w2_frontmatter_data.yaml` (67 entries, 163 related-edges). Rules-budget checkpoint: **73 always-on** (target hit). See `route_W2_structural.md` §Infrastructure session.
- **2026-07-22.** Phase 2a extension: trigger-consistency warning surfaced `self-contained-options` as unreachable via the agent trigger-path; added to `skills:` of 9 planning/design agents. Q-W2-2 reversed — RS2 dropped: `bin/build_skills_index.py`, `bin/test_build_skills_index.py`, `SKILLS-INDEX.md`, `make skills-index` target, and `install_configs.yml` Block 2 hook removed. Rationale: the rendered index adds no signal Claude uses (`description:` visible via Skill tool; related-graph lives in frontmatter and is validated by `related-links`). Tomorrow's flow: review YAML → apply → validate → commit + `make claude-push`.
