---
note-id: 20260723134958
created: 2026-07-23
modified: 2026-07-23
type: meta
subtype: conversation
gov_self_evolvement: true
language: ru
participants:
  - kirill
  - claude-opus-4-7
topic: "W2 frontmatter apply + generic git commit/push hook denial + CMD_REF false-positive fix"
decisions: []
related:
  - "[[2026-07-23-w2-apply-plus-git-hook-deny]]"
  - "[[route_W2_structural]]"
  - "[[../../README]]"
---

## Контекст начала

Продолжение работы над `future_projects/claude_tuning/`. На старте состояние по плану W2: инфраструктура готова (apply-скрипт, YAML на 67 записей, расширения `validate_config.py`, preconditions на 15 агентов), но `w2_frontmatter_data.yaml` не был apply'ен — единственный pending-decision. Полный контекст — `README.md` §State log (запись 2026-07-22).

Параллельно — свежий пользовательский фидбек: SE-агент во время `/techne-implement` авто-коммитит и авто-пушит, несмотря на глобальные инструкции «user commits manually». Причина, найденная по grep до старта: перекрывающий проектный `~/Work/mlops-be/CLAUDE.md`.

## Ключевые повороты

1. **Ревью YAML по рубрике** (route_W2_structural.md §Tomorrow's flow). Прошёл все 67 записей (39 skills + 28 agents). Ключи YAML полностью совпадают с диском (0 dangling). Медиана 2-3 ребра `related:` на артефакт, over-linking-а нет. Найдено 2 defensible асимметрии.

2. **Правки в YAML перед apply.**
   - `skills/python-engineer` — добавлен `lint-discipline` в `related:` (симметрия с `go-engineer`, у которого он уже есть).
   - `agents/refactor_cleaner` — добавлен `software_engineer_frontend` в `related:` (его собственный `description:` покрывает TS, но frontend-SE не был среди соседей).

3. **W2 apply**. `.venv/bin/python scripts/apply_w2_frontmatter.py --dry-run` → **would change 67, skipped 0, errors 0**. Apply → **changed 67, 0/0**. Git показал 68 modified (67 patched + YAML).

4. **`make validate-claude` упал на 1 error** — CMD_REF на `agents/.hypothesis/constants/9b764f1b19b9469a`. Диагностика: (a) `bin/validate_config.py::_iter_managed_files` использует `rglob("*")` без фильтра `.`-префиксов и лезет в gitignored кеш `hypothesis`; (b) `hypothesis` (v6.156.7) через constants-cache харвестит литералы из исходников, и в `skills/techne-fewer-permission-prompts/scripts/scan_transcripts.py` есть строка `/techne-fewer-permission-prompts` — regex `_TECHNE_REF_RE` матчит, а `commands/techne-fewer-permission-prompts.md` не существует (артефакт скилл, не команда). **Причина не связана с W2-apply — pre-existing локальный шум.**

5. **`make rules-budget` → always-on flat count = 73** ✅ (план 119 → ~73, попадание в цель).

6. **Мидсессионный фидбек про `/techne-implement`.** Пересказ обсуждения: `commands/techne-implement.md:169` уже говорит «user commits manually. Do NOT auto-commit», глобальные skills тоже. Реальный override — проектный CLAUDE.md + собственный брифинг пользователя. Опция B из чужого обсуждения (громче в `techne-implement.md`) уязвима к тому же перекрытию.

7. **Развилка по techne-implement фиксу — решение hook denial в любом контексте.** Пользователь заменил моё «hook denial в subagent-контексте» на «в любом контексте» — жёстче: Claude вообще не коммитит и не пушит, ни для агента, ни для main.

8. **Развилка по CMD_REF — решение «пропускать `.`-диры в валидаторе».** Durable фикс, тест регрессии.

9. **Реализация CMD_REF-фикса.** В `bin/validate_config.py::_iter_managed_files` добавлен фильтр: `if any(part.startswith(".") for part in path.relative_to(sub).parts): continue`. Тест `test_hidden_dir_not_scanned` в `bin/test_validate_config.py` (агент .hypothesis/constants blob + skill .pytest_cache blob).

10. **Реализация hook denial.** Две новые Phase-1 rules в `bin/bash_decision_gate.py`: `rule_git_commit` и `rule_git_push`. Первая попытка — поставил их в начале списка `PHASE1_RULES`, но это глушит специфичные сообщения (`amend`, `no-verify`, `commit-on-main`, `force-push`, `push-to-protected`, `push-mirror-all`, `push-delete-branch`). Переставил в конец: специфичные рулы стреляют первыми со своими сообщениями, catch-all ловит остаток. +4 новых теста в `test_bash_decision_gate.py`.

11. **Регрессия — 14 упавших тестов** в `test_pre_bash_safety_gate.py`. Все проверяли, что push/commit на не-protected branches **разрешён**. Инвертированы (переименованы `test_allows_* → test_*_denied_via_generic_*`), assert-ят `blocked` + `rule_name == "git-push"`/`"git-commit"`. Тесты, специфично проверяющие механику push-to-protected (env-var extend/override), теперь верифицируют оба исхода: matched pattern → `push-to-protected`, non-matched → `git-push`.

12. **Финальные checks.** `make validate-claude` → 0 errors, 0 warnings. `make test-claude-hooks` → **1122 passed** в ~110 секундах.

## Принятые decisions

- **W2 Phase 1c + 2b — frontmatter apply**. `problem:` + `related:` добавлены во все 39 SKILL.md + 28 agents/*.md. Идемпотентно (второй apply даст no-op).
- **Q-W2-fix-cmd-ref** — валидатор игнорирует любые пути с `.`-префиксом компонента.
- **Q-hook-git-catchall** — Phase-1 rules `git-commit` и `git-push` как catch-all deny, в самом конце `PHASE1_RULES`. Claude больше никогда не коммитит/пушит — ни как основной, ни как sub-agent. Специфичные рулы сохраняют свои сообщения.
- **YAML-правки** — asymmetries в `python-engineer.related` и `refactor_cleaner.related` закрыты перед apply.

Атомарных `D-NNN-*.md` файлов в этой сессии не создано (не было `/techne-decision` вызовов) — decisions зафиксированы прямо здесь и в state-snapshot.

## Открытые на конец сессии

1. **W2-коммит не сделан.** Working tree modified: 73 файла (68 W2 + 5 fix). Логический сплит на 2 коммита предложен, но не выполнен — коммитит пользователь (тем более что новый хук теперь блокирует `git commit` из моего контекста).
2. **`rules_budget_post_w2.md`** — deliverable из плана — не создан. Значение из головы: always-on flat = 73.
3. **State-log в `future_projects/claude_tuning/README.md`** — не обновлён под 2026-07-23.
4. **W3 не начата.** Скоуп из плана: RC1-RC6 content edits + split `project-preferences` (Q-RI2-2).
5. **Проектный `~/Work/mlops-be/CLAUDE.md`** — вариант A из чужого обсуждения (смягчить «Git workflow» / «Creating merge requests») отложен на отдельную PR.

## Что не забыть

- **Hook теперь блокирует Claude'у `git commit` и `git push` в любом контексте**, в т.ч. когда пользователь просит «закоммить это». Ожидание — пользователь коммитит сам через свой шелл. Если станет неудобно — послаблять хук осознанно (не откатывать; сузить условие).
- **Специфичные push/commit rules не dead code** — они дают более резкие сообщения (`Cannot commit on main. Create a feature branch first.`) до того, как срабатывает generic catch-all. Держать порядок в `PHASE1_RULES`: catch-all всегда в конце.
- **Тесты в `test_pre_bash_safety_gate.py` семантически инвертированы** — если в будущем кто-то захочет вернуть «push на feature разрешён», это будет заметно (много `test_*_denied_via_generic` придётся править обратно).
- **`_iter_managed_files` filter не проверяется на `sub` частях** — только на `path.relative_to(sub).parts`. Если `_CMD_SCAN_DIRS` когда-нибудь получит скрытые пути напрямую — фильтр их пропустит. Терпимо для текущего набора (`agents`, `skills`, `commands`, `bin`, `docs`).
- **Скилл `techne-fewer-permission-prompts` шейрит имя с `/techne-*` command-namespace** — collision засветилась через hypothesis-кеш, но это архитектурный смелл. Если родится ещё один скилл с `techne-` префиксом — валидатор снова ловит false positive от литералов внутри. На переименовать не пошли (heavy for W2).

## Следующая сессия

**Первое действие** — коммит W2 (пользователь вручную). Предложенный сплит:
1. `feat(claude-config): apply W2 problem+related frontmatter to 39 skills + 28 agents` — 68 файлов (67 patched + YAML tweak).
2. `fix(claude-config): deny git commit/push at hook level; skip hidden dirs in CMD_REF scan` — 5 файлов инфраструктуры.

Или единым коммитом, если удобнее.

**Второе действие** — на выбор:
- Закрыть W2 полностью: создать `rules_budget_post_w2.md` (запись `always-on flat = 73`), обновить `README.md` §State log под 2026-07-23, mark W2 done.
- Открыть W3: перечитать `routed_cue_set.md`, выбрать RC1-RC6 порядок, открыть новый route-файл.

## Линки

- `[[2026-07-23-w2-apply-plus-git-hook-deny]]` — state snapshot этой сессии.
- `[[route_W2_structural]]` — план W2, теперь Phase 1a/1b/1c + 2a/2b apply'ены.
- `[[../../README]]` — план-индекс claude-tuning.
