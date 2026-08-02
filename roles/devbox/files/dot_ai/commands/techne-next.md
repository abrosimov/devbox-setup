---
description: Pick up project work where we left off — read state snapshot and report current focus + next concrete step
---

The project follows a meta-layer convention: `state/STATE.md` is a MoC pointing to atomic state snapshots in `state/YYYY/MM/`. Each snapshot answers "where we are / current focus / next step / open questions / not to forget".

## Steps

### 1. Read `state/STATE.md`

If it does not exist in the current working directory: tell the user "В этом проекте нет meta-слоя `state/STATE.md`. С чего начнём?" and stop.

### 2. Follow the "Latest" pointer

In `STATE.md`, find the most recent snapshot (typically the first wikilink under a `## Latest` section, or the topmost entry in the chronological list). Read that file.

### 3. Report to the user in Russian

Compact report, no preamble, no narration. Sections:

- **Где мы сейчас** — 1–2 фразы из снапшота (раздел "Где мы сейчас" или эквивалент).
- **Текущий фокус** — что прямо сейчас в работе.
- **Следующий конкретный шаг** — то, что в "Следующих шагах" или Layer-0/top-priority item'е.
- **Открытые вопросы** — короткий список.
- **Что важно не забыть** — короткий список из соответствующего раздела снапшота.

End the report with: `Жду "поехали" или поправок.`

### 4. Do NOT

- Do not act on the next step.
- Do not propose a plan.
- Do not start reading roadmap items, decisions, conversations beyond the snapshot itself unless the user asks.
- Do not write to memory.
