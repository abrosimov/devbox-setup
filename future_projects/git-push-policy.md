# Политика `git push` для агента Claude Code

**Статус:** реализовано (defence-in-depth)
**Дата:** 2026-06-10
**Область:** глобальный `~/.claude/settings.json` + хук `~/.claude/bin/pre_bash_safety_gate.py`
**Применимо к:** GitHub и GitLab (gitlab.com)

---

## 1. Зачем

До изменений `Bash(git push *)` был полностью в `deny`. Это означало, что любой push требовал ручного одобрения, даже в feature-ветку. Это создавало лишний фрикшен в нормальных workflow: «agent → коммит → push → создать PR/MR» — на каждом push agent останавливался и просил подтверждение.

**Цель** — разрешить агенту делать обычные `git push` для feature-веток, сохранив жёсткую защиту от:
- push в `main`/`master`,
- force-push в любой форме (`--force`, `-f`, `--force-with-lease`, refspec с `+`),
- массовых операций (`--mirror`, `--all`, `--tags`),
- удаления веток через push (`--delete`, refspec `:branch`).

## 2. Архитектура: три эшелона обороны

### Эшелон 1: `settings.json` — string-pattern allow/deny

Первичная защита через glob-паттерны Claude Code. Deny **всегда** выигрывает у allow.

**Allow** (разрешены без prompt):
```
Bash(git push)               # bare push to upstream
Bash(git push origin *)      # push to origin (любая ветка кроме deny ниже)
Bash(git push -u origin *)   # push + set upstream
```

**Deny** (опасные паттерны):
```
Bash(git push --force *)
Bash(git push --force-with-lease *)
Bash(git push -f *)
Bash(git push --mirror *)
Bash(git push --all *)
Bash(git push --delete *)
Bash(git push --tags *)
Bash(git push * main)
Bash(git push * master)
Bash(git push * +*)            # refspec с +<branch> = force semantics
Bash(git push *:main)          # local:main
Bash(git push *:master)
Bash(git push * HEAD:main)     # HEAD:main
Bash(git push * HEAD:master)
Bash(git push * :*)            # space-colon = branch delete
```

**Ограничения этого эшелона:** glob-matching не понимает семантику. Возможные обходы:
- `git push origin refs/heads/local:refs/heads/master/sub` — не main/master напрямую, не ловится.
- Запушить в `develop`/`release/*` ничего не мешает (если они не в deny).
- `--tags` запрещён глобально, но `git push origin tag-name` без `--tags` пройдёт.

### Эшелон 2: хук `pre_bash_safety_gate.py` — семантический разбор

Запускается как `PreToolUse` хук перед каждым Bash-вызовом. Парсит `argv` через `shlex`, понимает структуру `git push`. Уже умеет:
- блокировать `--force` и `-f` (`rule_force_push`),
- блокировать коммит и merge на main/master (через `git branch --show-current`).

**Расширения, которые нужны** (отдельная задача через SE-агент):
1. **`rule_push_to_protected`** — резолвить refspec (`branch`, `local:remote`, `HEAD:remote`, `refs/heads/remote`, `+branch`), блокировать если remote-side = `main`/`master`.
2. **`rule_push_mirror_all`** — блокировать `--mirror`, `--all`.
3. **`rule_push_delete`** — блокировать `--delete` и refspec вида `:branch` (удаление ветки на remote).
4. **`rule_force_push`** — расширить: если refspec начинается с `+`, это семантически force-push.
5. **Опционально** — список защищённых веток конфигурируемый (env-var `CC_PROTECTED_BRANCHES=main,master,develop,release/*`).

### Эшелон 3: server-side branch protection — авторитетный backstop

Самая надёжная защита — на стороне сервера. Работает независимо от Claude.

**GitHub** (для каждого репо):
- Settings → Branches → Add branch protection rule
- Pattern: `main`, `master`
- Require pull request reviews before merging
- Restrict force pushes
- Restrict deletions

**GitLab** (для каждого проекта):
- Settings → Repository → Protected branches
- Branch: `main`, `master`
- Allowed to push and merge: `No one` (только через MR)
- Allowed to force push: off

**CLI-варианты:**
```bash
# GitHub
gh api -X PUT repos/<owner>/<repo>/branches/main/protection -f ...

# GitLab
glab api -X POST projects/<id>/protected_branches \
  -F name=main -F push_access_level=0 -F allow_force_push=false
```

## 3. Остаточные риски

Даже после всех трёх эшелонов остаются риски — большинство не митигируются автоматически.

| # | Риск | Серьёзность | Состояние |
|---|---|---|---|
| 1 | **String-matching bypass**: двойные пробелы, quote-tricks (`"or""igin"`) | Low | Не митигировано на уровне 1. Уровень 2 (shlex) парсит корректно. |
| 2 | **refs/heads/master/sub**: ветка с master в начале пути, не сам master | Low | Уровень 2 нужен (хук разбирает `refs/heads/<name>`). |
| 3 | **Push в `develop` или другие защищённые** | Medium | Нужен конфигурируемый список протекций. Server-side ловит. |
| 4 | **Push в чужой remote** (`upstream` при fork-workflow) | Medium | Allow `git push origin *` блокирует `upstream` → prompt. |
| 5 | **CI cost**: каждый push = pipeline | Medium | Культурное, не техническое. |
| 6 | **Wrong-branch push**: коммит в неправильной ветке → push туда же | Medium-High | Не митигируется. Нужна дисциплина веток + PR/MR review. |
| 7 | **Push секретов (`.env`, токены)** | High | Частично — `Edit(**/*.pem)`, `Edit(**/*.key)` deny на запись. Нужен secret-scanner pre-commit (отдельная задача). |
| 8 | **Force через refspec `+`** | Medium | Уровень 1 ловит `Bash(git push * +*)`. Уровень 2 нужно расширить (`rule_force_push` должен проверять `+` prefix). |
| 9 | **Tag push с force** | Low | `--force` deny ловит. Tag deletion (`git push origin :refs/tags/v1`) — ловит `Bash(git push * :*)`. |
| 10 | **PR/MR merge через CLI** | None | `gh pr merge`, `glab mr merge` уже в deny. |
| 11 | **Hook не запускается** (баг в hooks.json, ошибка в Python) | Critical если случится | Уровень 1 (settings.json) остаётся как safety net. Server-side protection — финальный backstop. |
| 12 | **Agent делает `git push origin HEAD:main`** через какой-то не-стандартный alias | Low | Ловится `Bash(git push * HEAD:main)` + хук. |

## 4. Что НЕ изменилось

Эти deny остались на месте и продолжают работать:
- `git rebase *` — переписывание истории
- `git reset *` (включая `--hard`) — потеря uncommitted
- `git commit --amend *` — переписывание последнего коммита
- `git commit --no-verify *` — обход pre-commit hooks
- `git tag *` — создание/удаление тегов (push тегов отдельно — `--tags` тоже deny)
- `gh pr close/merge/issue close`, `glab mr close/merge/issue close` — merge/close через CLI

## 5. Что сделать руками (action items для пользователя)

1. **Включить branch protection** для `main`/`master` на всех активных репозиториях:
   - GitHub: личные репо + work-форки
   - GitLab: work-проекты на gitlab.com
2. **Опционально**: добавить `develop` и `release/*` в protected, если такие ветки используются.
3. **Опционально**: настроить secret-scanner pre-commit hook (gitleaks/trufflehog) — закрывает риск №7.
4. **Расширение списка protected branches**: задано через `devbox_shell.env` в `roles/devbox/defaults/main/shell.yml` (`CC_PROTECTED_BRANCHES`). Дефолт — `main,master,develop,release/*`. Изменения подхватятся после `make personal`/`make work` (propagation через `_init_env.fish.j2` и `.bashrc.j2`).

## 6. Журнал решений

- **2026-06-10** — выбран hybrid-подход (Option C): narrow deny + explicit allow + хук на семантику. Альтернативы — оставить всё в deny (фрикшен) или убрать вообще (риск) — отвергнуты.
- **2026-06-10** — `--force-with-lease` оставлен в deny `settings.json`, хотя в хуке (`rule_force_push`) он специально разрешён. Это намеренная асимметрия: на уровне glob дешевле блокировать всё семейство `--force*`; на уровне хука можно различить безопасный lease-вариант (если в будущем потребуется).
- **2026-06-10** — branch protection описан как обязательный backstop, но реализация — ручная (нет автоматизации через Ansible).
- **2026-06-10** — `_init_env.fish.j2` обновлён: значения env-переменных теперь обёрнуты в `"..."`. Цель — поддержать `release/*` glob в `CC_PROTECTED_BRANCHES` без преждевременного раскрытия глоба fish'ем. Безопасно для всех существующих значений (`$HOME` раскрывается одинаково внутри double-quoted строк в fish).
