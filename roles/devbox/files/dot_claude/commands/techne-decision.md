---
description: Scaffold a new atomic decision file with the next D-NNN ID and add it to DECISIONS.md MoC
argument-hint: "<slug-or-title>"
---

The project records decisions as atomic files at `decisions/YYYY/MM/D-NNN-<slug>.md` and indexes them in `decisions/DECISIONS.md`.

## Steps

### 1. Get slug or title

From `$ARGUMENTS`. If empty, ask the user (single short question):
> Слаг (kebab-case) или короткий заголовок будущего decision'а?

If the user provides a Russian title — преобразуй в латинский kebab-case slug (translit + lowercase + dashes). Подтверди slug у пользователя.

### 2. Find next D-NNN

Сканируй `decisions/**/D-*.md`. Найди наибольший N, инкрементируй на 1. Форматируй с leading zeros до ширины 3: `D-001`, `D-012`, `D-123`.

If `decisions/` directory does not exist or contains no D-NNN files — start from `D-001`.

### 3. Create decision file

Path: `decisions/<current-YYYY>/<current-MM>/D-NNN-<slug>.md`. Create intermediate directories if needed.

Frontmatter template:

```yaml
---
note-id: <YYYYMMDDHHMMSS>
created: <YYYY-MM-DD today>
type: meta
subtype: decision
gov_self_evolvement: true
language: ru
aliases:
  - "D-NNN"
status: accepted
conversation: "[[<current-session-topic-slug>]]"
supersedes: []
superseded_by: []
---
# D-NNN: <title>

## Решение
<one paragraph — заполняется итеративно с пользователем>

## Контекст
<заполняется итеративно>

## Последствия
<заполняется итеративно>

## Источники
- 
```

### 4. Update `decisions/DECISIONS.md`

Прочитай MoC. Добавь новую строку в хронологическую секцию `## <current-YYYY>` → `### <current-MM>` (создай если нет):

```markdown
- [[D-NNN-<slug>]] (<YYYY-MM-DD>) — <короткое summary, можно временное "TBD">
```

Если есть секция `## По темам` — спроси пользователя одной фразой:
> Под какую тему этот decision? <список существующих тем + "новая">

Добавь wikilink под соответствующей темой.

Если темы не уверены / нет секции — пропусти и просто оставь в хронологии.

### 5. Заполнить содержимое

Show the user the file path. Then iterate:

> Что в **Решении**? (one paragraph)

> **Контекст** — почему это решение было нужно?

> **Последствия** — что это включает/блокирует/требует?

> **Источники** — ссылки на conversation, related decisions, внешние материалы?

Apply each piece of input to the file as you receive it. Keep formatting clean.

Update summary in `DECISIONS.md` once title/решение готов.

### 6. Sync conversation log if present

If the current session has a conversation log file (e.g. one referenced by `STATE.md`'s latest snapshot or by a recent `/techne-log` invocation), update its frontmatter `decisions:` list with `[[D-NNN-<slug>]]`.

### 7. Report briefly

Кратко: создан D-NNN, путь, заполненные секции, что осталось. Без preamble.

### 8. Do NOT

- Не делать `git add`, `git commit`, `git push` без явной команды.
- Не запускать валидаторы.
- Не писать в memory.
- Не подтягивать context соседних проектов.
- Не предлагать D-(N+1), D-(N+2) "впрок" — один decision за раз.
