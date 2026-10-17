# План: агенты, которые доводят работу до PR

Статус: план, без правок в проекте. Ветка `claude/agents-delegation-models-1i1s22`. Все пути относительно `roles/devbox/files/`, если не сказано иное. Проверки `file:line` сделаны по текущему дереву; расхождения с черновиком отмечены словом **Исправлено**.

## Цель

Перестроить систему агентов так, чтобы контракт работы (цель, критерии готовности, полномочия) заменял вопросы по ходу дела: разработчик, тест-писатель и ревьюер работают парами и параллельно, спорные решения записываются с вариантами в `.ai_artifacts/` внутри репозитория, коммит/push/PR и слежение за CI пред-разрешены, слияние в основную ветку происходит автоматически при зелёном CI, а Jira-ключ распространяется автоматически и никогда не спрашивается.

## Не-цели

Не меняем диалоговые агенты `tdd_guide` и `focus_coach`; не трогаем `fpf-thinking`, hooks-архитектуру за пределами двух хуков и `bash_decision_gate.py`; не переносим `docs/implementation_plans/` задним числом; не разрешаем force-push, `--no-verify` и деструктивные git-операции; не придумываем примеры порога — они придут из сырых логов (§ «Пороговые примеры»).

## Целевой конвейер

```
contract.md (цель, критерии, полномочия, KEY)
   ├── domain_modeller ──► entities.md ──┐
   ├── api_designer ─────► api_spec ─────┤
   │                                     ▼
   │        ┌── software_engineer_* (реализация, без тестов)
   │        │                 ∥ параллельно, от контракта
   │        └── unit/integration test writer (не видит реализацию)
   │                          ▼
   │              code_reviewer: находка ⇒ refute_*_test (default)
   │                           или задание unit-test-writer'у
   │                          │  фикс-цикл до "no open findings"
   │                          ▼
   │      commit → push → PR → CI до зелёного → gate 4.3 → merge в master
   │                          ▼
   └────────────────► report.md + ответ пользователю
```

Отличия от нынешнего `/techne-implement` (`techne-implement.md:116-197`): тесты пишутся параллельно, а не после («Next: Run `/techne-test`»); ревьюер назначается автоматически, а не по `/techne-review`; commit/push/PR делает агент; merge — автоматический по условиям 4.3.

## Предусловия и проверки до начала

| # | Факт | Как проверить | Результат сейчас |
|---|---|---|---|
| P1 | Claude Code принимает `model: fable` во фронтматтере субагента | `code.claude.com/docs/en/sub-agents`, таблица фронтматтера | **Подтверждено**: `sonnet`, `opus`, `haiku`, `fable`, полный ID, `inherit`. Fable 5.1 требует Claude Code ≥ 2.1.257 (`docs/en/model-config`) — проверить `claude --version` на машине |
| P2 | Репозиторные валидаторы принимают `fable` | `dot_claude/bin/validate_config.py:242-244` (список `sonnet/opus/haiku`), `dot_agy/bin/translate_agents.py:8` (`MODEL_MAP` только opus/sonnet), `dot_ai/skills/agent-builder/SKILL.md:63`, `dot_ai/agents/agent_builder.md:294` | **Не принимают** — правится в шаге 6.1 |
| P3 | `pre_edit_repo_boundary.py` считает worktree частью проекта | `dot_claude/bin/pre_edit_repo_boundary.py:33-37`: граница = git-root от `CLAUDE_PROJECT_DIR`; `_claude_lib/paths.py:51` ищет `.git` через `exists()`, то есть файл `.git` worktree тоже найдётся | **Частично**: если сессия *стартовала внутри* worktree — ок; если стартовала в основном checkout, а worktree лежит рядом (`$AION_AUTOPOIESEON/<project>/<branch>/`, `CLAUDE_ADAPTER.md:64-65`) — хук вернёт `ask`. В `test_pre_edit_repo_boundary.py` теста на worktree нет. Правится в шаге 7.2 |
| P4 | Временная директория исключена из границы | `pre_edit_repo_boundary.py:40-45` → `paths.temp_roots()` (`TMPDIR`, `tempfile.gettempdir()`) | **Исправлено** относительно черновика: исключение есть, живёт в `_claude_lib/paths.py:15-17` |
| P5 | `bash_decision_gate.py` не блокирует commit/push | `dot_claude/bin/bash_decision_gate.py:436-455`: `rule_git_commit` и `rule_git_push` **запрещают безусловно**, с комментарием «stands even when a project-level CLAUDE.md tells the agent to commit» | **Блокирует**. Черновик это пропустил. Без шага 4.1 ни одна политика в Markdown не заработает |
| P6 | Основная ветка и защита ветки | `.github/workflows/ci.yml:14-20` — основная ветка **`master`** (не `main`), CI на push в `master` и `claude/**` и на PR в `master`; джобы `lint`, `validate`, `test`, `hook-projects` | Branch protection / rulesets **не проверены**: `gh auth status` → токен невалиден, в GitHub MCP нет инструмента для protection. Проверить через `gh api repos/abrosimov/devbox-setup/branches/master/protection` и `.../rulesets` с рабочим токеном |
| P7 | GitHub-интеграция доступна агенту | `mcp__github__get_me` → `abrosimov` | **Доступна** (MCP). `gh` есть (`/usr/local/bin/gh`), но токен в этой сессии невалиден — на рабочей машине перепроверить `gh auth status` |
| P8 | Бюджет Codex | `cat USER_AUTHORITY_PROTOCOL.md dot_codex/AGENTS.md \| wc -c` = 21 882 из 32 768 (`tests/deploy/test_codex_assets.py:124-126`) | Запас ~10,9 KB; новые правила кладём в skills, не в ядро |
| P9 | Jira-хук git | `.config/git/hooks/prepare-commit-msg:17,56,67`: ключ берётся из имени ветки по `[A-Z]{2,}-[0-9]+`, позиция из `jira.keyPosition` | Футер/префикс коммита уже автоматический, если ключ в имени ветки. Остаётся только не спрашивать |

## Шаги

### Фаза 0 — артефакты и порог (фундамент)

**0.1 Раскладка `.ai_artifacts/` и правило «не `$TMPDIR`».**
Файлы: `dot_ai/skills/agent-base-protocol/SKILL.md` (новая секция «Artefacts»), `dot_ai/USER_AUTHORITY_PROTOCOL.md:143` (**Исправлено**: ссылка на `$TMPDIR/ledger-<topic>.md` стоит в §5, а не §4), `dot_ai/skills/workflow/SKILL.md:134` (`$TMPDIR/<job>-decision-log.md`), `dot_ai/skills/config/SKILL.md` (`PLANS_DIR`).
Изменение: раскладка из §«Решения и отчёт» ниже становится единственным местом для планов, решений, ledger и отчётов; упоминания `$TMPDIR` заменяются на `.ai_artifacts/<task>/…`. `ai_written_scripts/` (ядро §4:127) остаётся как есть — это код, а не артефакт.
Проверка: `make validate-claude`, `make rules-budget`, `pytest tests/deploy/test_codex_assets.py`. Откат: один коммит. Зависимости: нет.

**0.2 Порог обсуждения вариантов — расширить `diverge-synthesize-select`, не создавать `option-deliberation`.**
**Исправлено**: skill с процедурой 3–7 кандидатов, шагом «Combine» (синергия) и персистентным `dss_output.json` уже существует (`dot_ai/skills/diverge-synthesize-select/SKILL.md:16-40,86-92,135-141`) и подключён у architect, api_designer, designer, domain_modeller, implementation_planner, TPM и всех трёх SE. Новый skill дублировал бы его.
Файлы: `diverge-synthesize-select/SKILL.md` — секция «When to use it» (строки 16-40) дополняется порогом владельца: *проектные решения* (структура кода, алгоритм, форма API, структура данных, границы модулей) → 5–7 кандидатов + синергия + запись в `decisions.md`; имена переменных, порядок аргументов, выбор между эквивалентными хелперами → ниже порога, одна строка в `decisions.md`. Нижняя граница «3» в тексте остаётся для диалоговых карточек пользователю, «5–7» становится нормой для записи в артефакт. Добавить подсекцию-плейсхолдер «Threshold examples (pending raw logs)» с ссылкой на §«Пороговые примеры» этого плана.
`dot_ai/agents/architect.md:49-50` («usually meet the threshold») — заменить на ссылку на порог без «usually».
Проверка: `make validate-claude`, `make validate-skills`. Откат: коммит. Зависимости: 0.1.

### Фаза 1 — контракт результата

**1.1 Секция «Work contract» в `agent-base-protocol/SKILL.md`** (его подключают все 28 агентов, 4,5 KB — есть место).
Содержимое: цель; критерии готовности с доказательством (команда, файл, вывод) — формулировка «user approved» запрещена; три уровня полномочий (решаю и записываю / решаю и поднимаю в отчёт / BLOCKED); пред-разрешённые действия (commit в рабочей ветке, push ветки, создание PR, слежение за CI, merge при зелёном CI — §Фаза 4); формат возврата `Status | Result | Decisions | Blockers | Evidence | Paths`.
Проверка: `make validate-claude`; `make rules-budget` (не вырасти больше, чем на удалённые ниже гейты). Откат: коммит. Зависимости: 0.1, 0.2.

**1.2 Заменить фразовую проверку одобрения на проверку контракта.**
Файлы: `dot_ai/skills/code-writing-protocols/SKILL.md:17-44` («Approval Validation», шаблон «⚠️ Approval Required»), `dot_ai/skills/agent-communication/SKILL.md:148-166` (та же проверка) и `:200` («Implementing without approval → stop»).
Изменение: субагент проверяет наличие контракта от оркестратора (цель + критерии), а не фразу пользователя; одобрение пользователя остаётся делом оркестратора (ядро §0-§1, `CLAUDE_ADAPTER.md:20-23`).
Проверка: `make validate-claude`. Откат: коммит. Зависимости: 1.1.

### Фаза 2 — тела агентов

**2.1 Разработчики** (`software_engineer_go/python/frontend.md`, зеркала `dot_codex/agents/software-engineer-*.toml`): не пишут тесты; вход — контракт + сущности (`domain_modeller`) + API (`api_designer`) + файл потока из плана; порог 0.2; упоминание автоматического ревью. Проверка: `make validate-claude`, `pytest tests/deploy/test_codex_assets.py`. Зависимости: 1.1.

**2.2 Тест-писатели** (`unit_tests_writer.md`, `integration_tests_writer_go/python.md`, `dot_codex/agents/unit-test-writer.toml`, `integration-tests-writer-*.toml`): вход — контракт и публичный интерфейс (сигнатуры, OpenAPI/proto, сущности), **не diff** (`unit_tests_writer.md:3,18`: «Detects the language(s) in the diff»); запрет читать файлы реализации вне публичных заголовков (`contract-boundary`); тесты, падающие до реализации, — ожидаемы, статус в отчёте `RED-by-design`. Самоостановку «re-run with Opus» (`:52-60`) убрать — модель назначает диспетчер (шаг 6.2). Проверка: `make validate-claude`. Зависимости: 1.1.

**2.2a Рукопожатие разработчик ∥ тест-писатель** (новая подсекция в `dot_ai/skills/contract-boundary/SKILL.md`): оба стартуют от одного `contract.md` + `entities.md` + `api_spec`; тест-писатель импортирует только публичные имена из контракта; если реализация отклонилась от контракта, разработчик обязан обновить контракт первым и записать `D<n>` — тест-писатель тесты под реализацию не подгоняет. Оркестратор запускает их одним сообщением (`CLAUDE_ADAPTER.md:38`, «Launch independent agents in one message») и ждёт обоих перед ревью. Проверка: `make validate-claude`. Зависимости: 2.1, 2.2.

**2.3 Ревьюер** (`code_reviewer.md`, `dot_codex/agents/code-reviewer.toml`):
- Тесты-опровержения: **путь по умолчанию** — ревьюер сам пишет падающий тест в отдельный файл `<tests_dir>/refute_<slug>_test.<ext>` (Go: `refute_<slug>_test.go`; Python: `tests/refute_<slug>_test.py`; TS: `__tests__/refute_<slug>.test.ts`). Файлы `refute_*` живут до фикса; после зелёного CI разработчик (или `unit-test-writer`) переносит их содержимое в основной тестовый файл и удаляет `refute_*`; наличие `refute_*` в ветке — блокер merge (шаг 4.3). **Альтернативный путь** — делегировать `unit-test-writer`у с описанием бага; используется, когда баг требует фикстур/инфраструктуры, которых у ревьюера нет (интеграционные, фронтенд с MSW). Выбор пути — одна строка в `decisions.md`.
- Разрешения: во фронтматтере уже есть `Edit` (`code_reviewer.md:4`), добавить `Write`, ограничив в теле путями тестов. В TOML `sandbox_mode = "read-only"` (`code-reviewer.toml:3,26`) → `workspace-write`; формулировку «Stay read-only and never implement fixes» заменить на «never edit non-test files».
- Замечания о стиле не блокируют.
Проверка: `make validate-claude`, `pytest tests/deploy/test_codex_assets.py`. Откат: коммит. Зависимости: 1.1, 2.2.

**2.4 Проектировщики** — убрать гейты и «user approved»:
`domain_modeller.md:113` («Present the glossary to the user for validation»); `api_designer.md:55` («user approved»), `:154` («Present error strategy for approval»), `:160` («Ask user if offset-based needed»); `designer.md:55`, `:120`, `:168`, `:196`; `database_designer.md:56`; `database_designer.md:109` — `gen_random_uuid()` генерирует v4, при PG 18+ писать `uuidv7()`. Критерий готовности → «spec passes linting + consumers (developer, test writer) can build from it». Проверка: `make validate-claude`. Зависимости: 1.1.

**2.5 TPM** (`technical_product_manager.md:173-181,283,413,561`): интервью-цикл превращается в «вопросы, прошедшие стоп-лист ядра §1, одним пакетом в отчёт», `user approval obtained` → проверяемый критерий. Зависимости: 1.1.

**2.6 Планировщик** (`implementation_planner.md:144,186,631,662`): вместо одного `plan.md` — `plan.md` как индекс (цель, критерии, порядок, зависимости) + `streams/WS-<n>-<slug>.md` на поток; разработчик получает путь только своего потока. Хук `pre-plan-code-guard` (`:26`) должен покрывать `streams/*.md` — проверить `pre_plan_code_guard.py` и расширить тест. Проверка: `make validate-claude`, `make test-claude-hooks`. Зависимости: 0.1.

**2.7 Утилитарные**: `refactor_cleaner.md:60` («Ask the user before removing >20 lines» → решение в отчёт); `observability_engineer.md:24-36` (самоостановка → диспетчер), `:216,441-454` vs `:650` (деплой в sandbox — убрать команды деплоя, оставить генерацию: соответствует `:650` «humans deploy»); `build_resolver_go` — `go clean -modcache`, `goimports -w .` только с записью в `decisions.md`. Зависимости: 1.1.

**2.8 `skill-builder.toml:5`** ссылается на `skill-creator`, которого нет в `dot_ai/skills/` (есть `skill-builder`). Заменить ссылку. Проверка: `make validate-claude`.

### Фаза 3 — Jira без вопросов

**3.1 Единое правило разрешения контекста.** Файлы: `techne-test.md:34-36`, `techne-review.md:25-27`, `techne-design.md:17-19`, `techne-api-design.md:17-19`, `techne-domain-analysis.md:17-19`, `techne-schema.md:36-38` (все шесть — `AskUserQuestion` при exit 2). Заменить на блок по образцу `techne-plan.md:17-20` / `techne-implement.md:68-72` (уже «do not ask»): ключ берётся из ветки (`resolve_context.py:16`), иначе из текста задачи, иначе — `_adhoc`. Если ключ дан в задаче, а ветки ещё нет — ветка создаётся как `<KEY>_<slug>`, тогда `prepare-commit-msg` (P9) сам проставит ключ в коммит; PR-заголовок `<type>(<KEY>): …`; папка `.ai_artifacts/<KEY>_<slug>/`. `PROJECT_DIR` в `resolve_context.py:15` переключить на `.ai_artifacts` (новый дефолт `DEFAULT_PLANS_DIR`), обновить `test_resolve_context.py` и `config/SKILL.md`.
Проверка: `make test-claude-hooks` (`test_resolve_context.py`), `make validate-claude`, `make test-git-hooks`. Откат: коммит. Зависимости: 0.1.

### Фаза 4 — git, PR, CI, merge

**4.1 Хук `bash_decision_gate.py`** (`:436-455`): `rule_git_commit`/`rule_git_push` → разрешать `git commit` и `git push` **без** `--force*`, `--no-verify`, `--amend` и не на `main|master` (правила `rule_commit_on_main:458`, force-push и `--no-verify` остаются deny). Обновить `test_pre_bash_safety_gate.py:52-260` (тесты `*_denied_via_generic` для обычного push/commit инвертируются). Проверка: `make test-claude-hooks`, `make test-agy-hooks` (копия дерева в `dot_agy/bin/` — править отдельно). Откат: коммит. Зависимости: нет, но включать только вместе с 4.2.

**4.2 Политика в адаптерах и skills**: `CLAUDE_ADAPTER.md:17` (commit/push/PR из «Always confirm» → «pre-authorised inside a work contract; merge — only via 4.3 gate»), `:44-45` и `:62-63` (модели — ссылка на фронтматтер); `dot_codex/AGENTS.md:56-57,97`; `dot_agy/GEMINI_ADAPTER.md:11`; `agent-communication/SKILL.md:208` (строка «Push commits, open PRs» из Human-Only → в контракт; `approve/merge` остаётся human-only **кроме** автоматического merge по 4.3); `techne-implement.md:177-197` («The user will commit manually», «Next: Run /techne-test»), `techne-review.md:85-110` (меню `'pr'`). Проверка: `make rules-budget`, `pytest tests/deploy/test_codex_assets.py`, `make test-live` (меняется содержимое, но не генерация settings — достаточно `test-live-guard`). Зависимости: 1.1, 4.1.

**4.3 Авто-merge в `master`** — новая секция в `workflow/SKILL.md` + `techne-implement.md` шаг «Land». Условия, все обязательны:
1. PR не draft; `mergeable_state` = `clean` (`mcp__github__pull_request_read`).
2. Все required checks зелёные (`get_check_run`/`actions_get`); required-набор берётся из защиты ветки (P6), а до её подтверждения — хардкод `lint, validate, test, hook-projects` из `ci.yml`.
3. Нет неразрешённых review-thread'ов (`pull_request_read` → threads; `resolve_review_thread` только для thread'ов, открытых самими агентами и закрытых фиксом с зелёным CI).
4. Ревьюер вернул `no open findings`, в ветке нет файлов `refute_*`.
5. `.ai_artifacts/<task>/report.md` записан и закоммичен.
Механика: `mcp__github__enable_pr_auto_merge` (squash) после п.1-5; если auto-merge на репозитории выключен — `merge_pull_request` вручную после повторной проверки п.2. **CI красный** → разбор логов (`get_job_logs`), фикс, push, повтор; падение вне задачи → BLOCKED в отчёте, merge не делается. **CI недоступен** (нет запусков 10 мин, API 5xx) → PR остаётся открытым, статус `CI unavailable` в отчёте, merge не делается. **Branch protection требует review** от человека → merge невозможен, это записывается, PR остаётся; требование снять/оставить — вопрос владельцу (Q2).
Проверка: сквозной прогон (шаг 8.2). Откат: коммит; аварийно — `disable_pr_auto_merge`. Зависимости: 4.1, 4.2, P6.

**4.4 Слежение за CI**: `subscribe_pr_activity` после создания PR; при недоступности — опрос `actions_list` раз в 2 мин, не более 30 мин. Файл: `workflow/SKILL.md`. Зависимости: 4.3.

### Фаза 5 — команды и конвейер

**5.1 `techne-implement.md`**: шаги 6-8 (`:116-197`) → цепочка «contract → (domain_modeller, api_designer при необходимости) → [developer ∥ test writer] → reviewer → fix loop → push → CI → land → report». `:91` «Unclear → backend» и `:97,122` (неявный запуск `/techne-api-design`) → решение с записью в `decisions.md`. `:99-110` таблица моделей → ссылка на фронтматтер. Проверка: `make validate-claude`. Зависимости: фазы 1-4.

**5.2 `workflow/SKILL.md:96,104,160`**: автономный режим — дефолт, пошаговый — по `--step`. Убрать «Next: Run …» из 5 команд (`grep "Next\*\*: Run"`). `lint-discipline/SKILL.md:28,85-90` — WAIT → пункт в отчёт оркестратору. Зависимости: 5.1.

### Фаза 6 — модели

**6.1 Валидаторы**: `validate_config.py:242-244` — добавить `fable` и `inherit`; `test_validate_config.py` — кейсы; `translate_agents.py:8` — `fable` → **открыто** (у Antigravity тиры `pro`/`flash`; сопоставления для `fable` в его документации не найдено — до проверки оставить явный fallback `pro` с комментарием и тестом в `test_agy_hooks.py`); `agent-builder/SKILL.md:63`, `agent_builder.md:184-189,294`. Проверка: `make validate-claude`, `make test-claude-hooks`, `make test-agy-hooks`. Зависимости: P1.

**6.2 Фронтматтер** `dot_ai/agents/*.md` по таблице ниже. Один источник правды — `model:`; прозу `agent-communication/SKILL.md:122-129`, `techne-implement.md:101`, `CLAUDE_ADAPTER.md:62-63` удалить. Codex TOML поля `model` не содержат — верно, наследуют (`dot_codex/README.md:155`). Проверка: `make validate-claude`. Зависимости: 6.1.

### Фаза 7 — хуки

**7.1 `stop_user_actions_guard.py`** R3 (`:191-196`): тест на русский императив рядом со слэш-командой в `test_stop_user_actions_guard.py`. Проверка: `make test-claude-hooks`.

**7.2 `pre_edit_repo_boundary.py:33-37`**: считать in-project любой путь, чей `git rev-parse --git-common-dir` совпадает с общим `.git` проекта (worktree того же репозитория). Добавить `test_worktree_of_the_session_repository_is_allowed`. Зеркало в `dot_agy/bin/`. Проверка: `make test-claude-hooks`, `make test-agy-hooks`. Зависимости: P3.

**7.3 Изоляция субагентов**: Claude Code поддерживает `isolation: worktree` во фронтматтере (docs/sub-agents), но `CLAUDE_ADAPTER.md:64` запрещает `EnterWorktree` в пользу `proj wt add`. Решить одним правилом (Q3) и записать в `workflow/SKILL.md`.

### Фаза 8 — проверка

**8.1** `make qa`, `make validate-claude`, `make validate-skills`, `make rules-budget`, `make test-live-guard`; деплой `make "$MNEMOSYNE_PERISTASEOS" EXTRA_VARS='--tags ai,claude,codex,agy'`.
**8.2** Сквозной прогон на учебной задаче в отдельном worktree этого репозитория: контракт → developer ∥ test writer → reviewer с `refute_*` → фикс → push → CI → auto-merge в тестовую ветку-«master» (временная ветка `landing-test`, чтобы не трогать настоящий `master`) → отчёт. Критерии: ни одного `AskUserQuestion`, `decisions.md` заполнен, `refute_*` отсутствует после фикса, параллельные worktree не мешают.

### Порядок коммитов и откат

Каждый шаг — один коммит с Jira-ключом задачи в заголовке (ключ появится через `prepare-commit-msg`, если ветка названа `<KEY>_<slug>`). Порядок фаз фиксирован зависимостями: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8; внутри фазы 2 шаги независимы и могут идти параллельно в разных worktree. Два шага нельзя разносить по разным деплоям: 4.1 (хук) и 4.2 (политика) — иначе либо Markdown разрешает то, что хук запрещает, либо наоборот. Откат любого шага — `git revert` его коммита; откат 4.1 возвращает прежний deny, и это единственный шаг, после отката которого остальное дерево остаётся согласованным только при одновременном откате 4.2 и 4.3. Деплой на машину (`make "$MNEMOSYNE_PERISTASEOS" EXTRA_VARS='--tags ai,claude,codex,agy'`) делать после каждой фазы, а не после каждого шага: Block 1 rsync `--delete` перезапишет `~/.claude/` целиком, и промежуточное состояние фазы (например, 4.1 без 4.2) не должно жить на живом движке.

## Модели по ролям (проверить по докам перед 6.2)

| Роль | Модель | Почему | Статус |
|---|---|---|---|
| architect, technical_product_manager | `fable` | первые решения, на которых держится остальное; docs: «hardest and longest-running tasks» | алиас подтверждён; версия CLI ≥ 2.1.257 — проверить |
| оценщик вариантов для архитектурных решений (advocates в DSS) | `fable` | независимая проверка высоких ставок | то же |
| domain_modeller, api_designer, designer, database_designer, implementation_planner | `opus` | контракты для двух потребителей | без изменений |
| software_engineer_* | `opus` (`sonnet` по явному флагу) | точность реализации, ревьюер ловит остальное | без изменений |
| unit/integration test writers | `sonnet`, `opus` при сложном контракте (решает диспетчер по размеру интерфейса, не агент) | спецификация → тесты | убрать самоостановку |
| code_reviewer | `opus` | ревью корректности + падающие тесты | без изменений |
| build_resolver_go, doc_updater, refactor_cleaner, consistency_checker, freshness_auditor, observability_engineer | `sonnet` | ограниченные задачи | без изменений |
| tdd_guide, focus_coach | `sonnet` | диалог | не трогать |
| `haiku` | не назначать | ни одна роль не механическая | — |
| Antigravity-тир для `fable` | `pro` (fallback) | нет документации на сопоставление | открыто |

## Решения и отчёт: раскладка `.ai_artifacts/`

```
.ai_artifacts/
  <KEY>_<slug>/            # или _adhoc/<sanitised_branch>/
    contract.md            # цель, критерии, полномочия, пред-разрешённое
    plan.md                # индекс плана (implementation_planner)
    streams/WS-<n>-<slug>.md
    entities.md, api_spec.yaml | *.proto   # domain_modeller, api_designer
    decisions.md           # журнал решений (формат ниже)
    dss_output.json        # машинная запись DSS, когда запрошена
    review.md              # находки ревьюера со ссылками на refute_*
    ci.md                  # push → run id → статус → что исправлено
    report.md              # итоговый отчёт пользователю
```

Запись в `decisions.md`: `## D<n> — <вопрос>` → уровень (routine / stated / escalated) → для проектных решений 5–7 вариантов с плюсами/минусами и найденной синергией → выбор и причина → отвергнутые → как отменить → статус (`decided`, `raised`). Ниже порога — одна строка `D<n>: <выбор> — <причина>`.

`report.md` и ответ пользователю: ссылка на PR и статус merge; критерии PASS/FAIL с доказательством; `Decisions I made` (только stated/escalated, с номерами D<n>); блокеры; состояние CI; `What I need from you` — только при BLOCKED (ядро §4:116-120, хук R1-R3). Папка коммитится в ветку вместе с работой; `.gitignore` её не исключает (проверено).

## Риски

| Риск | Смягчение |
|---|---|
| 4.1 открывает commit/push, и агент коммитит мусор | deny на `main|master`, `--amend`, `--force*`, `--no-verify` остаются; обязательный `git_safe_commit.py`; PR всегда создаётся до merge |
| Авто-merge при неполном наборе required checks | до подтверждения P6 — хардкод четырёх джобов + запрет merge, если хотя бы один не отчитался |
| Тесты, написанные параллельно, не компилируются против реализации | test writer работает только от сигнатур контракта; расхождение = contract gap в `decisions.md`, разработчик правит реализацию, не тесты |
| Ревьюер с правом записи начинает чинить код | allowlist путей тестов в теле агента + проверка в 8.2; TOML `workspace-write` только для `refute_*` |
| `refute_*` остаются в ветке | условие 4 в 4.3 блокирует merge |
| Процесс 5–7 вариантов съедает бюджет на мелочах | порог 0.2 + плейсхолдер примеров; ниже порога — одна строка |
| Бюджет Codex 32 KiB | новые правила в skills; `test_codex_assets.py` в CI |
| `dot_agy/bin` разошёлся с `dot_claude/bin` | каждый шаг хуков — обе копии, оба make-таргета |
| `fable` недоступен на машине (версия CLI, гейтвей) | docs: fallback на session model тихий — шаг 8.2 проверяет фактическую модель через hook log (`universal_logger`) |

## Открытые вопросы владельцу

1. **Merge-стратегия**: squash (рекомендация — один коммит на задачу, Jira-ключ в заголовке) или merge-commit?
2. **Branch protection на `master`**: если требует approving review человека, авто-merge невозможен. Рекомендация: required checks = четыре джоба CI, review не требовать, разрешить auto-merge в настройках репозитория.
3. **Worktree-механика для субагентов**: `isolation: worktree` Claude Code (временный, удаляется без изменений) или нынешний `proj wt add` (`CLAUDE_ADAPTER.md:64`)? Рекомендация: оставить `proj wt add`, так как `pre_edit_repo_boundary` и раскладка `$AION_AUTOPOIESEON` уже на него завязаны; 7.2 делает его безопасным.
4. **Antigravity и `fable`**: fallback `pro` или исключить агентов на `fable` из `agy`-деплоя? Рекомендация: `pro` с комментарием до появления документации.

## Пороговые примеры (будут добавлены из сырых логов)

> Плейсхолдер. Сюда войдут реальные случаи, где пользователь явно требовал обсуждения вариантов (с цитатой запроса, типом решения — структура / алгоритм / форма API / структура данных / границы модулей — и тем, что было выбрано), и контрпримеры ниже порога. Примеры не придумываются; источник — сырые логи сессий. После добавления они переносятся в `diverge-synthesize-select/SKILL.md` (шаг 0.2).

## Что проверено и что нет

Проверено по файлам: все `file:line` в шагах выше открыты и подтверждены, в том числе `unit_tests_writer.md:52-60`, `domain_modeller.md:113`, `api_designer.md:55,154,160`, `designer.md:55,120,168,196`, `database_designer.md:56,109`, `technical_product_manager.md:175-179,283,413,561`, `refactor_cleaner.md:60`, `observability_engineer.md:24-36,216,441-454,650`, `architect.md:49-50`, `agent_builder.md:184-189,294`, шесть команд с `AskUserQuestion`, `techne-implement.md:68-72,91,97,101,122,177-197`, `techne-review.md:25-27,85-110`, `workflow/SKILL.md:96,104,134,160`, `code-writing-protocols:17-44`, `agent-communication:122-129,148-166,200,208`, `lint-discipline:28,85-90`, `agent-builder/SKILL.md:63`, `translate_agents.py:8`, `validate_config.py:242-244`, `code-reviewer.toml:3,26`, `skill-builder.toml:5`, `CLAUDE_ADAPTER.md:17-18,44-45,62-65`, `dot_codex/AGENTS.md:52-57,97`, `GEMINI_ADAPTER.md:11-12`, `ci.yml:14-20`, `prepare-commit-msg:17,56,67`, бюджет Codex 21 882 B. По документации: `model: fable` в субагентах и алиас `fable` в Claude Code (code.claude.com, sub-agents и model-config). GitHub MCP работает (`get_me`).

Исправлено относительно черновика: `$TMPDIR` в ядре — §5:143, не §4; исключение temp-директории в `pre_edit_repo_boundary` существует (`paths.temp_roots`); `bash_decision_gate.py` безусловно запрещает commit/push — критичный пропуск; DSS-skill уже содержит процедуру вариантов — новый `option-deliberation` не нужен; основная ветка — `master`, не `main`; `techne-implement.md:68-72` и `techne-plan.md` Jira уже не спрашивают.

Не проверено: branch protection / rulesets и настройка auto-merge на `abrosimov/devbox-setup` (`gh` токен невалиден, в MCP нет инструмента); версия `claude` на целевой машине (≥ 2.1.257 для Fable 5.1); сопоставление `fable` с тирами Antigravity; поведение `pre_plan_code_guard.py` для `streams/*.md`; поддержка `workspace-write` в текущей версии Codex для TOML-агентов (`dot_codex/README.md:41` отдаёт это клиенту Codex).
