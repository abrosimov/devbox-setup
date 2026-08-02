---
description: Close out the session — append/create conversation log entry, optionally create new state snapshot, update MoCs
argument-hint: "[topic-slug]"
---

The project follows the meta-layer convention with atomic notes:
- `conversations/YYYY/MM/<topic-slug>.md` — atomic conversation logs.
- `state/YYYY/MM/<date>-<event-slug>.md` — atomic state snapshots.
- `state/STATE.md` — MoC pointing to latest snapshot + chronological list.

## Steps

### 1. Determine topic slug

From `$ARGUMENTS`. If empty, ask the user (single short question):
> Что было главной темой этой сессии? Короткий slug (kebab-case), например `kadmus-reframing` или `frontmatter-as-wal-stage1`.

Use the current year and month for path (`conversations/<YYYY>/<MM>/<topic-slug>.md`).

### 2. Conversation log

Path: `conversations/<current-YYYY>/<current-MM>/<topic-slug>.md`.

If the file does not exist — create with this frontmatter shape:

```yaml
---
note-id: <YYYYMMDDHHMMSS>
created: <YYYY-MM-DD of session start>
modified: <YYYY-MM-DD today>
type: meta
subtype: conversation
gov_self_evolvement: true
language: ru
participants:
  - kirill
  - claude-opus-4-7
topic: "<human-readable topic>"
decisions: []
related: []
---
```

Body sections (only when relevant):
- **Контекст начала** — с чего стартовала сессия.
- **Ключевые повороты** — 5–10 пунктов с короткими цитатами или тезисами; повороты в обсуждении.
- **Принятые decisions** — wikilinks на файлы `D-NNN-...`.
- **Открытые на конец сессии** — список.
- **Что не забыть** — короткий список предупреждений на будущее.
- **Следующая сессия** — стартовая точка.

If the file already exists — прочитай его, добавь новую секцию `## <YYYY-MM-DD> — продолжение` с содержимым ИЛИ переструктурируй существующие секции, если пользователь предпочитает (спроси одной короткой строкой).

### 3. State snapshot — спроси пользователя

Ask the user (single short question):
> Создать новый state snapshot? **Да** — если зафиксированы значимые decisions, открытые вопросы изменились, или сменился текущий фокус. **Нет** — если сессия мелкая (декомпозиция, чистка, мелкая правка).

If yes:
- Path: `state/<current-YYYY>/<current-MM>/<YYYY-MM-DD>-<event-slug>.md`. Event slug = краткое описание того, что произошло, kebab-case.
- Frontmatter:
  ```yaml
  ---
  note-id: <YYYYMMDDHHMMSS>
  created: <YYYY-MM-DD today>
  type: meta
  subtype: state-snapshot
  gov_self_evolvement: true
  language: ru
  event: "<one-sentence description>"
  previous_snapshot: "[[<basename of previous Latest snapshot>]]"
  ---
  ```
- Sections: **Что зафиксировано этим снапшотом**, **Текущий фокус**, **Top-3 по важности**, **Execution order**, **Открытые вопросы**, **Что не забыть**, **Линки**.

Then update `state/STATE.md`:
- Replace the "Latest" pointer with `[[<new-snapshot-basename>]]`.
- Prepend a new entry into the chronological list with date and event slug.

### 4. Sync references

If a new snapshot was created — обнови `related:` во frontmatter conversation log'а: добавь wikilink на новый снапшот.

Если в сессии принимались decisions — убедись, что `decisions:` во frontmatter conversation log'а ссылается на них.

### 5. Report briefly

Кратко скажи пользователю что создано/обновлено. Без preamble, без narration.

### 6. Do NOT

- Не делать `git add`, `git commit`, `git push` без явной команды.
- Не запускать валидаторы, тесты, drift detection.
- Не писать в memory.
- Не подтягивать context соседних проектов.
