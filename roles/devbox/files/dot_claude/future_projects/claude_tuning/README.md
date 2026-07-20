# Claude Tuning — verbosity, completion, evidence-first

**Status:** research complete, awaiting user decision on three open questions before edits.
**Date opened:** 2026-07-20
**Trigger:** user complaint about verbose responses, 60%-completion pattern, misrepresented restated intents.

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
2. **Complete the task as asked.** Do not deliver 60%, ask about the remaining 40% as follow-up when the remaining 40% was in the original request. Do not split compound asks.
3. **Do not misrepresent the user in restated intents.** If restating, be precise; when in doubt, ask.
4. **Assumptions must be evidence-backed.** Every silent choice — either verified in the repo (grep, read, LSP), or promoted to an explicit open question at the end of the reply. No unverified assumptions.
5. **Answer placement for compound asks.** When the user combines a question with a work request, the answer to the question must appear at the end (after work is reported), not before the tool-call log that buries it.

## File layout

| File | Contents |
|------|----------|
| `README.md` | This file — index, user complaint, distilled requirements, open questions |
| `evidence_log_mining.md` | Sub-agent report: verbatim evidence of failure patterns mined from `~/.claude/projects/` session logs |
| `research_web.md` | Sub-agent report: web research on verbosity control, anti-satisficing, evidence-first patterns across Anthropic, OpenAI, Cursor, Cline, Aider, community sources |
| `synthesis_and_proposal.md` | My synthesis of both reports, proposed structural changes to `dot_claude/`, open questions for the user |

## Open questions (blocking implementation)

Presented via `AskUserQuestion` in-conversation; user requested clarification before answering. Reproduced here for persistence.

### Q1 — Where to place anti-verbosity rules

A) New always-on skill `voice-discipline` — ban-list, numeric anchor, hard opening in a dedicated `skills/voice-discipline/SKILL.md`. UAP §Voice shrinks to a 3–5-line pointer. Pro: does not bloat UAP (Arize warning on bloat causing rule loss). Con: another always-on skill in every session's context (~800 tokens).

B) Edit `USER_AUTHORITY_PROTOCOL.md` §Voice directly — numeric anchor + ban-list inline. Pro: single location, simple navigation. Con: UAP grows (already large), risk of bloat-induced rule loss per Arize.

C) Hybrid — critical bans in UAP, details in triggered skill. UAP §Voice gets a 5-line numeric anchor + top-5 forbidden phrases. New triggered skill `voice-discipline` (not always-on) with the full ban-list, examples, justified exceptions. Pro: minimum always-on footprint, details available on trigger. Con: details may not load when needed.

### Q2 — How to reshape the disclosure block

A) Remove the Assumptions section entirely — keep only (1) Restated intent (optional, only when the request is genuinely ambiguous), (2) Evidence I gathered — with path:line references, (3) Open questions — what evidence-recon could not resolve. Assumptions explicitly forbidden as a category. Pro: forces evidence-first. Con: rigid format, breaks muscle memory.

B) Keep Assumptions with a mandatory Evidence check per item — each line in Assumptions must have inline evidence: `Assumption: X (verified: file.py:42)`, or migrate to Open questions if not verified. Pro: soft evolution of current format. Con: I might continue to skate through with "verified" claims that were not really verified.

C) Trigger-based disclosure — appears only when the request is genuinely ambiguous. Remove the "first-reply on non-trivial request" trigger. Disclosure fires only when ≥2 materially different interpretations exist (the "would I do anything different?" check yields YES for ≥1 assumption). On unambiguous tasks — proceed to work. Pro: eliminates ceremonial disclosure. Con: brings back the risk of silent assumptions.

### Q3 — Handling compound asks (question + work request in one turn)

A) Answer at the end, single final message — structure: brief acknowledgement ("делаю X, отвечу на Y в конце") → tool calls → work report → answer to question. One final message. Pro: no scrolling. Con: if work is long, the question answer waits.

B) Answer up-front, work silently — structure: brief answer → "делаю X" → tool calls → brief "готово". Pro: quick answer up-front. Con: user complained — answer floats up above the tool-call log.

C) Split — answer immediately, then propose the work in a second message and await "go" — answer first, then "приступаю к Y — подтверди" and wait. Pro: clean separation. Con: extra round-trip when work is obvious and already sanctioned ("и да, согласен, делай").

## Next actions

1. User picks one option per open question (Q1, Q2, Q3) — or a variant.
2. Draft edits to specific files under `roles/devbox/files/dot_claude/`.
3. Present the diff for approval before writing.
4. Deploy via `make claude-push`.
