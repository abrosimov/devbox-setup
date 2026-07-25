---
note-id: 20260723134959
created: 2026-07-23
type: meta
subtype: state-snapshot
gov_self_evolvement: true
language: ru
event: "W2 frontmatter apply landed (67 files patched); generic git commit/push hook denial added; CMD_REF false-positive on hidden dirs closed."
previous_snapshot: ""
---

## Что зафиксировано этим снапшотом

- **W2 Phase 1c + 2b apply завершён.** `scripts/apply_w2_frontmatter.py` записал `problem:` + `related:` в 39 SKILL.md и 28 agents/*.md (67 файлов, 0 skipped, 0 errors). Идемпотентно.
- **YAML tweaks перед apply:** `skills/python-engineer.related` += `lint-discipline`; `agents/refactor_cleaner.related` += `software_engineer_frontend` (закрыты 2 defensible asymmetries).
- **Hook denial на `git commit` и `git push` в любом контексте.** Две новые Phase-1 rules в `bin/bash_decision_gate.py` (`rule_git_commit`, `rule_git_push`), поставлены в конец `PHASE1_RULES` — специфичные рулы (`amend`, `no-verify`, `commit-on-main`, `force-push`, `push-to-protected`, `push-mirror-all`, `push-delete-branch`) стреляют первыми со своими сообщениями, catch-all ловит остаток.
- **CMD_REF false positive на `.hypothesis/` закрыт.** `bin/validate_config.py::_iter_managed_files` теперь пропускает пути с `.`-префиксным компонентом. Не связано с W2-apply — pre-existing локальный шум от `hypothesis`-кеша.
- **Тесты:** +5 новых (4 hook + 1 validator), 14 инвертировано в `test_pre_bash_safety_gate.py`. Итого 1122 passed.
- **`make validate-claude` → 0 errors, 0 warnings.** `make rules-budget → always-on flat = 73` (target hit, план 119 → ~73).

## Текущий фокус

**W2 apply landed; W2 commit pending; W3 не начата.** Working tree: 73 файла modified (68 W2 + 5 fix). Логический сплит на 2 коммита предложен. Коммитит пользователь (хук теперь блокирует Claude'а на `git commit`/`git push`).

## Top-3 по важности

1. **Коммит W2 apply + fix.** Ветка `master`, 73 файла modified. Без этого следующая сессия начнёт с dirty working tree.
2. **`rules_budget_post_w2.md`** — deliverable плана. Записать `always-on flat = 73` как post-W2 baseline для будущего сравнения.
3. **State log в `future_projects/claude_tuning/README.md`** — дописать запись 2026-07-23 (W2 apply + hook deny + validator fix), пометить W2 как done.

## Execution order

1. Пользователь коммитит W2 (руками).
2. Создать `rules_budget_post_w2.md` (короткий файл с числами + verdict).
3. Обновить `README.md` §State log под 2026-07-23; пометить W2 как done в статус-строке.
4. Открыть W3 route(s): выбрать порядок RC1-RC6 + `project-preferences` split (Q-RI2-2, отложенный на W3).

## Открытые вопросы

- **Q-W3-1** — какой из RC1-RC6 идёт первым в W3? (Не пробовали ранжировать за пределами `routed_cue_set.md`.)
- **Q-W3-2** — `project-preferences` split: три файла (English / libraries / tooling) или два (identity / choices)? Влияет на `related:` edges, которые уже проставлены.
- **Q-hook-1** — оставить hook как unconditional deny, или дать env-var (например `CC_ALLOW_COMMIT=1`) для однократного bypass, когда пользователь явно хочет? Пока что — жёсткий deny, откладываем на первое реальное неудобство.
- **Проектный `mlops-be/CLAUDE.md`** — редактировать «Git workflow» + «Creating merge requests» в отдельной PR. Не блокирует W3.

## Что не забыть

- Хук теперь **блокирует Claude'у `git commit` и `git push` в любом контексте**. Если следующая сессия попросит меня коммитить — ответ будет «руками, через шелл». By design.
- В `PHASE1_RULES` порядок load-bearing — catch-all держим последним, иначе теряются специфичные сообщения (`Cannot commit on main. Create a feature branch first.`).
- `_iter_managed_files` filter применяется только к `path.relative_to(sub).parts` — если когда-нибудь добавим `.`-префиксный подкаталог в `_CMD_SCAN_DIRS`, фильтр его пропустит. Проверять на добавлении новых scan-dirs.
- Скилл `techne-fewer-permission-prompts` шейрит имя с `/techne-*` command-namespace — collision через hypothesis constants-cache засветила это. Второй такой скилл (если будет) снова уронит валидатор на литералах внутри. Архитектурный смелл, оставили осознанно.

## Линки

- Conversation-log: `[[../../conversations/2026/07/w2-apply-plus-git-hook-deny]]`
- План: `[[../../route_W2_structural]]`, `[[../../README]]`
- Инфраструктура: `roles/devbox/files/dot_claude/bin/bash_decision_gate.py`, `roles/devbox/files/dot_claude/bin/validate_config.py`, `scripts/apply_w2_frontmatter.py`
