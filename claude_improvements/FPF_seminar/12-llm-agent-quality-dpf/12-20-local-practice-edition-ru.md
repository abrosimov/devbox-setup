---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, local-practice-edition, e4-pfr, e53]
seminar-iteration: 3
created: 2026-06-28
status: local-practice-edition
method: FPF E.4.PFR (relation/edition records) · E.5.3 (unidirectional dependency) · G.11 (currentness) · consumes 03-current-config-map (realisation ground truth)
framework: LAQF — LLM-Agent Quality Principle Framework (Layer-2 Local Practice edition)
language-twin: "[[12-20-local-practice-edition]]"
---

# LAQF — Layer-2 Local Practice edition (реализация `dot_claude/` данного пользователя)

Это **Layer-2 Local Practice edition** LAQF: конкретная реализация тридцати паттернов Layer-1 Domain ([[12-10-patterns-A]] … [[12-15-patterns-F]]) в **развёрнутой конфигурации `dot_claude/` данного пользователя** — её хуках, скиллах, агентах, командах, настройках и `USER_AUTHORITY_PROTOCOL.md`, разворачиваемом как `~/.claude/CLAUDE.md`. Там где Domain edition утверждает *что* должно выполняться как свойство качества, данная edition фиксирует *как* (и *выполнено ли* это в действительности), опираясь на снимок истины [[../../03-current-config-map]].

Согласно `E.5.3` (`FPF-Spec.md:64835`) зависимость **строго однонаправленная и ациклическая**: Local Practice edition зависит от Domain edition (LAQF), которая зависит от FPF Core — но никогда не наоборот. Изменение Domain pattern не переписывает молчаливо данную конфигурацию; оно порождает *refresh line* (`G.11` T4, [[12-00-spine]] §6). Равным образом данная реализация — полная или неполная — **ничего не записывает обратно в Domain edition или FPF Core** (`E.5.3` CC-UD.1/2, `FPF-Spec.md:64890`). Следовательно, edition вправе **отставать** от Domain edition, и §2 честно фиксирует это отставание: из тридцати паттернов конфигурация полностью реализует единицы, частично реализует большинство, а девять остаются открытыми пробелами — и именно этот набор пробелов *является* бэклогом улучшений (§5).

Это **edition / relation** артефакт, а не каталог паттернов: новых паттернов `E.8` он не создаёт и источники не перефразирует — он соединяет существующие Local-активы с существующими Domain-паттернами по id (`E.4.PFR`, `FPF-Spec.md:64478`).

## §0 Декларация edition (E.4.PFR)

| Слот | Декларация |
|---|---|
| **Edition** | `LAQF-Local v0.1` — Layer-2 Local Practice edition. |
| **Ограниченный контекст** | Рабочее пространство `AION_AUTOPOIESEON` → развёрнутый `~/.claude/` данного пользователя (источник: `roles/devbox/files/dot_claude/`). |
| **Реализуемый предмет** | Тридцать паттернов Layer-1 LAQF, инстанциированных как конкретные хуки / скиллы / агенты / команды / настройки / разделы протокола. |
| **Зависит от** | `LAQF v0.1` (Domain edition); транзитивно FPF Core (`FPF-Spec.md`). Однонаправленно, ациклически (`E.5.3`). |
| **Статус edition** | `build-with-gaps` — 2 реализованы (✅), 19 частичных (◐), 9 пробелов (⬜); см. §2. |
| **Источник истины** | [[../../03-current-config-map]] (инвентаризация, анализ пробелов, конфликты активов, размер стека инструкций). |
| **Граница неприменения** | Не является переформулировкой Domain-паттернов, патчем FPF Core или артефактом исполнения/сборки — это карта чтения от Local-активов к Domain-идентификаторам. |

---

## §1 Запись зависимости edition (E.4.PFR + E.5.3)

Авторитетный `FrameworkEditionDependencyRecord` на стороне Local, расширяющий представительную запись, зафиксированную в [[12-00-spine]] §4.2.

```text
FrameworkEditionDependencyRecord@Context:                # Local → Domain (+ Core)
  frameworkEditionRef:          LAQF-Local v0.1 (Layer-2 Local Practice edition)
  dependsOnEditionRefs:         LAQF v0.1 (Domain edition); transitively FPF Core (FPF-Spec.md)
  dependencyReason:             the dot_claude realisation instantiates Domain patterns as
                                concrete hooks (hooks.json), skills, agents, commands,
                                settings.json, and the USER_AUTHORITY_PROTOCOL.md shipped as
                                ~/.claude/CLAUDE.md
  compatibilityBoundary:        the Local edition MAY lag the Domain edition; a Domain pattern
                                change does NOT silently rewrite this config — it raises a
                                refresh line (§5 / G.11 T4). Current lag = 19 partial + 9 gap
                                of 30 (§2). The lag is admissible precisely because the
                                dependency is one-directional.
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §5 (G.11 T4 — dot_claude config drift); also Domain pattern
                                change ([[12-00-spine]] §6 T1–T3)
  e53ConformanceNote:           Local → Domain → Core; acyclic; no back-edge. This realisation
                                writes nothing into the Domain edition or FPF Core
                                (CC-UD.1/2, FPF-Spec.md:64890). Gaps are a lag, not a
                                back-pressure on the Domain patterns.
```

---

## §2 Карта реализации — 30 Domain-паттернов → активы `dot_claude/`

Легенда статусов: **✅** реализовано (детерминированно / полностью закодировано) · **◐** частично (advisory или неполно) · **⬜** пробел (реализация отсутствует, либо свойство задано Domain и ещё не построено). «Family» — методическое семейство `MF-` ([[12-01-source-pack]] §6), реализуемое Local-активом (или которое было бы реализовано, если бы актив был построен). Факты реализации и ссылки на пробелы взяты из [[../../03-current-config-map]] (ссылки на разделы — в правом столбце).

### §2.A Слой A — Законы (меры снижения рисков)

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **A1** | Substance-Gated Pushback | UAP `§Helpfulness`, `§Voice`; `proposal_discipline.py` (подсказка). Скилл инженерной позиции (максима Фишера) **отсутствует** ([[../../03-current-config-map]] §3.5). | MF-2 | ◐ |
| **A2** | Delta Over Whole-Artefact | UAP `§Voice` режим iteration/delta; `proposal_discipline.py` подталкивает к delta-over-rewrite (§3.2). | MF-2/MF-6 | ◐ |
| **A3** | Answer-Budget Before Prose | UAP `§Voice` плотность фактов по умолчанию. Нет PostStop-шлюза по числу строк (пробел §3.2). | MF-2 | ◐ |
| **A4** | Effective-Fill Accounting | `settings.json:12` `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`; `pre_compact_mask.py`; скилл `iterative-retrieval`. Нет предупреждения при заполнении ≥50% (пробел §4.3.1). | MF-3 | ◐ |
| **A5** | Read Before Assert | Скиллы `lsp-navigation` / `lsp-tools`; `pre_write_existing_guard.py` (только Write, §3.8). | MF-2 | ◐ |
| **A6** | User-Anchored Facts Over Self-Draft | Правило цитирования UAP; `code-writing-protocols`. Нет скаффолда `[USER]`/`[DRAFT]` (пробел §3.6). | MF-4 | ◐ |
| **A7** | Reconnaissance Before Action | UAP `§Inquiry` лестница рекогносцировки + блок Disclosure; `proposal_discipline.py` (UserPromptSubmit + Stop). | MF-2 | ◐ |
| **A8** | Literal Scope On Terse Feedback | UAP `§Proposal ≠ Approval`; скилл `self-contained-options`. | MF-2 | ◐ |

### §2.B Слой B — Граница harness

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **B1** | Rotate Before The Cliff | `settings.json:12` autocompact 80%; `session_save.py`; `pre_compact_mask.py`. 80% превышает практический порог 50–60% (пробел §4.3.1). | MF-3 | ◐ |
| **B2** | Authoritative Handoff Re-Entry | `session_save.py` (PreCompact + SessionEnd) + progress spine (`bin/progress`) — долговременная экстернализация состояния. | MF-4 | ✅ |
| **B3** | Attention-Budget Ledger | Нет механизма отслеживания нагрузки стека инструкций; стек 509 строк измерен, но не управляется (§6, пробел §4.3). | MF-4 | ⬜ |
| **B4** | Self-Imposed Output Budget | UAP `§Voice` режимы краткости. Нет PostStop-шлюза по объёму вывода (пробел §3.2). | MF-6 | ◐ |

### §2.C Слой C — Конфигурация

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **C1** | Instruction-Stack Within Budget | Эффективный стек = **509 строк** (UAP 216 + проект 196 + рабочее пространство 97), в 2,5–5× сверх лимита; **ещё не сокращён** (§6). | MF-6 | ⬜ |
| **C2** | Single-Owner Rule Resolution | Четыре неразрешённых конфликта между активами (один вопрос vs. пакетные; подагент vs. основной approval; disclosure-block-is-preamble) (§5). | MF-4 | ⬜ |
| **C3** | Encoded Engineering Posture | Нет скилла, кодирующего максиму Фишера / anti-false-dichotomy / shadow-CBC / kill-two-birds; `fpf-thinking` — только opt-in (§3.5). | MF-2 | ⬜ |
| **C4** | Tagged Facts Scaffold | Нет шаблона `[USER]`/`[DRAFT]`/`[FILE path:line]`; модель самостоятельно переформулирует (§3.6). | MF-4 | ⬜ |
| **C5** | Deterministic Over Advisory | `hooks.json` (слой PreToolUse/PostToolUse/Stop) + скилл `hooks-architecture` реализуют мета-паттерн частично; многие правила по-прежнему advisory (§3.15, §7). | MF-1 | ◐ |
| **C6** | Whole-Path Permission Coverage | `permission_auto_approve.py` (PermissionRequest) + скилл `techne-fewer-permission-prompts`; запросы разрешений на рутинных путях сохраняются (§4.3.13). | MF-1 | ◐ |
| **C7** | Enforced Skill Invocation | `validate_skill_evals.py` (частичное покрытие); нет PreToolUse-хука сопоставления триггеров, блокирующего обход (пробел §3.14). | MF-1 | ⬜ |

### §2.D Слой D — Рабочий процесс / топология конвейера

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **D1** | Re-Entry Across Phase Boundary | `pre_plan_code_guard.py`; команды techne workflow; скилл `workflow` — шлюз plan↔code. Повторный вход — ручной (§3.3). | MF-3 | ◐ |
| **D2** | Atomic Single-Form Emission | Скилл `structured-output`. Конвейер по-прежнему выдаёт один большой MD + JSON-тень на каждый этап (§3, проблема rc-21). | MF-6 | ◐ |
| **D3** | Roadmap-Anchored Dispatch | Spine `bin/progress` + команды techne; диспетчеризация по-прежнему ручная, дорожной карты параллелизма нет (§3). | MF-5/MF-4 | ◐ |
| **D4** | Enforced Role Lanes | Frontmatter `tools:` на уровне агента ограничивает инструментальный коридор при диспетчеризации (28 агентов). Нет runtime-хука области редактирования на агента (§3.7). | MF-5 | ✅ |

### §2.E Слой E — Целостность вывода / верификация

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **E1** | Claim Requires Observed Event | `stop_lint_gate.py`, `stop_format.py`, `post_edit_lint.py`. Нет хука, верифицирующего заявленный прогон тестов/сборки против фактически выполненного (пробел §3.15). | MF-1 | ◐ |
| **E2** | Enforced Citation Anchors | Правило цитирования UAP — только advisory; нет Stop-хука, помечающего голые ссылки типа «see d32» (пробел §3.12). | MF-1 | ⬜ |
| **E3** | Counter-Evidence Audit | `code-reviewer` + `go-review-checklist`; `fpf-thinking` opt-in. Общего аудита контрсвидетельств нет (§3.9). | MF-2 | ◐ |
| **E4** | Input-Order Fidelity | Нулевое покрытие — нет механизма сохранения/верификации порядка вывода (пробел §3.11). | MF-6 | ⬜ |
| **E5** | Quiet Toolchain Output | `pre_bash_toolchain_guard`. Нет режима `--quiet` по умолчанию + JSON-при-ошибке по всему тулчейну (пробел §3.1 / rc-28). | MF-6 | ◐ |

### §2.F Слой F — Гигиена процесса / git

| LAQF | Domain-паттерн | Локальная реализация (актив) | Family | Статус |
|---|---|---|---|---|
| **F1** | Bounded Branch Freshness | fish-функция `wt sync` примиряет worktree с его sync-source (вручную); **нет шлюза актуальности**, верифицирующего отставание ветки при интеграции (S-025 нулевое покрытие, §3.10). | MF-1 | ⬜ |
| **F2** | Deterministic Commit Hygiene | UAP `§Git Commits` запрет трейлеров (advisory) + `settings.json` `permissions.deny` блокирует деструктивный git + `git_safe_commit.py`. **Нет** хука `PreToolUse(git commit)` для удаления трейлеров (S-026 опирается на соблюдение, §3.10). | MF-1 | ◐ |

**Итог:** ✅ 2 (B2, D4) · ◐ 19 · ⬜ 9 (B3, C1, C2, C3, C4, C7, E2, E4, F1). Девять пробелов составляют бэклог реализации (§5); частичные реализации — поверхность обновления по принципу deterministic-over-advisory (C5).

---

## §3 Записи отношений паттерн–фреймворк (E.4.PFR)

Представительные `PatternFrameworkRelationRecord`ы, связывающие Local-реализации с управляющими Domain-паттернами — по одной записи на класс реализации (✅ реализовано, ◐ частично, ⬜ пробел под руководством Domain), по образцу метода представительных записей spine ([[12-00-spine]] §4.3). Полная строка реализации каждого паттерна — в §2; поле `blockedStrongerReading` в каждой записи обеспечивает направление `E.5.3`.

```text
LR1  PatternFrameworkRelationRecord@Context:                       # realised
  relationId: LAQF-Local.R.b2-handoff
  sourceRef: session_save.py (PreCompact+SessionEnd) + bin/progress spine
  targetRef: LAQF.B2 (Authoritative Handoff Re-Entry)
  relationFunction: realisation (Local instantiation of a Domain pattern)
  governedUse: the Local hooks instantiate B2's MF-4 state-externalisation; durable
               handoff survives compaction/session-end
  directGoverningPatternRef: LAQF.B2   dependencyOrEditionEffect: Local → Domain, upward
  blockedStrongerReading: the hook realising B2 MUST NOT read as redefining B2; Domain
               states what, the hook is one realisation of how
  refreshOrSupersessionCondition: session_save.py / progress schema change → refresh §2.B

LR2  relationId: LAQF-Local.R.d4-lanes                              # realised (scoped)
  sourceRef: per-agent `tools:` frontmatter across 28 agents
  targetRef: LAQF.D4 (Enforced Role Lanes)
  relationFunction: realisation (partial scope — tool lane only)
  governedUse: agent frontmatter restricts the MF-5 tool lane at dispatch
  directGoverningPatternRef: LAQF.D4   dependencyOrEditionEffect: Local → Domain, upward
  blockedStrongerReading: a tool-lane restriction is NOT a per-agent edit-scope runtime
               hook; the lane is tool-level, not scope-level (the §3.7 residual)
  refreshOrSupersessionCondition: agent roster / tools change → refresh §2.D

LR3  relationId: LAQF-Local.R.c5-hooks                              # partial (the meta-surface)
  sourceRef: hooks.json (PreToolUse/PostToolUse/Stop) + hooks-architecture skill
  targetRef: LAQF.C5 (Deterministic Over Advisory)
  relationFunction: realisation (partial — the MF-1 surface exists, coverage incomplete)
  governedUse: the hook layer is the Local realisation surface for every other MF-1 gate
               (C6, C7, E1, E2, F1, F2); C5 classifies which advisory rules earn a hook
  directGoverningPatternRef: LAQF.C5   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: an existing hook layer does NOT mean every must-hold rule is
               hooked; the lag is the un-hooked advisory rules (§2 ◐/⬜ rows)
  refreshOrSupersessionCondition: each closed gap adds an MF-1 hook → refresh §2

LR4  relationId: LAQF-Local.R.f2-trailer-gap                        # Domain-led gap (canonical lag)
  sourceRef: UAP §Git Commits (advisory ban) + settings.json permissions.deny (destructive git)
  targetRef: LAQF.F2 (Deterministic Commit Hygiene)
  relationFunction: realisation (incomplete — the MF-1 trailer-strip is unbuilt)
  governedUse: the Domain F2 specifies a PreToolUse(git commit) strip; the Local edition
               realises only the advisory ban + destructive-git deny, not the strip
  directGoverningPatternRef: LAQF.F2   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the missing hook does NOT weaken the Domain F2 pattern; the gap
               is a Local lag, not a back-pressure on Domain (E.5.3 CC-UD.1/2)
  refreshOrSupersessionCondition: author the PreToolUse(git commit) trailer-strip → close
               the gap (§5 / G.11 T4)

LR5  relationId: LAQF-Local.R.f1-freshness-gap                      # Domain-led gap
  sourceRef: wt sync fish function (manual reconcile; no freshness gate)
  targetRef: LAQF.F1 (Bounded Branch Freshness)
  relationFunction: realisation (incomplete — corrective tool exists, gate unbuilt)
  governedUse: wt sync is the reconcile action; F1's integration-point freshness check is
               not realised (S-025 zero coverage)
  directGoverningPatternRef: LAQF.F1   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the presence of wt sync does NOT satisfy F1; the gate (verify
               branch-behind at integration) is the missing part
  refreshOrSupersessionCondition: author a freshness gate over wt sync → close the gap (§5)

LR6  relationId: LAQF-Local.R.e4-order-gap                          # Domain-led gap (zero coverage)
  sourceRef: (none — §3.11 zero coverage)
  targetRef: LAQF.E4 (Input-Order Fidelity)
  relationFunction: realisation (absent — Domain property with no Local asset)
  governedUse: Domain E4 specifies an output-order check; the Local edition has none
  directGoverningPatternRef: LAQF.E4   dependencyOrEditionEffect: Local lags Domain (admissible)
  blockedStrongerReading: the absence of a realisation does NOT remove the Domain E4
               pattern; it records a lag to be closed
  refreshOrSupersessionCondition: author an output-order check → close the gap (§5)
```

---

## §4 Манифест пакета фреймворка (Local edition)

```text
FrameworkPackageManifest@Context:
  frameworkEditionRef:           LAQF-Local v0.1 (Layer-2 Local Practice edition)
  selectedPatternSetPublicationRef: §2 realisation map (30 Domain patterns → dot_claude assets)
  relationRecordRefs:            §3 LR1–LR6 (realised / partial / gap classes); full per-pattern
                                 realisation rows in §2.A–§2.F
  dependencyAndEditionRecordRefs: §1 (Local → Domain + Core); [[12-00-spine]] §4.2 (representative)
  editionStatus:                 build-with-gaps (✅ 2 · ◐ 19 · ⬜ 9 of 30)
  deprecationOrSupersessionRefs: —
  sourcePackRefs:                [[../../03-current-config-map]] (realisation ground truth);
                                 [[12-01-source-pack]] §6 (MF-family vocabulary)
  qualityEvidenceRefs:           → E.21/E.22 quality cycle, S7 ([[README]] + QA)
  refreshPlanOrCurrentnessRefs:  §5 (G.11 T4 — config drift); [[12-00-spine]] §6 (whole-framework)
  firstEntryCarrierRefs:         [[README]] (S7) + this edition file
  blockedRuntimeOrBuildReading:  LAQF-Local is a reading/authoring edition mapping deployed
                                 assets to Domain ids — it creates no imports, APIs, runtime
                                 deps, or build semantics; the assets it names have runtime
                                 effect, the manifest does not (FPF-Spec.md:64478)
```

---

## §5 Актуальность и обновление — G.11 T4 (дрейф конфигурации)

Данная edition является объектом триггера обновления **T4** в общефреймворковом `RefreshPlan` ([[12-00-spine]] §6): *дрейф конфигурации Layer-2 → обновить карту Local Practice edition, **а не** Domain-паттерны.*

```text
RefreshScope (G.11 T4, this edition):
  EntityOfConcernRef: LAQF-Local v0.1 (the §2 realisation map + §3 records)
  TargetScope:        the realisation map only — Domain patterns are out of scope here
  Triggers:
    T4a asset change   → a hook/skill/agent/command/settings edit in dot_claude/:
                         re-walk §2, update the affected row's asset + status
    T4b gap closed     → one of the 9 ⬜ rows gains a realisation (e.g. the F2 trailer-strip
                         hook, the E2 citation hook): flip ⬜→◐/✅, update §3 LR record
    T4c Domain change  → a Domain pattern changes (spine §6 T1–T3): raise a refresh line on
                         the affected §2 row; the Domain change does NOT auto-rewrite config
    T4d conflict fixed → a §2.C C2 inter-asset conflict is resolved: update §2.C + ground truth
  Action:             re-derive the map from a fresh [[../../03-current-config-map]] snapshot;
                      record the refresh in [[PROGRESS]] §9
  RequiredPins:       dot_claude commit hash; config-map snapshot date; Domain edition version
```

**Бэклог пробелов (повестка реализации).** Девять строк ⬜ — упорядоченная поверхность улучшений, большинство из которых отделено от ◐/✅ одним `MF-1`-хуком или одним скиллом/шаблоном: хук удаления трейлеров F2, шлюз актуальности F1, шлюз цитирования E2, проверка test-pass-vs-run E1 (обновление ◐→✅), проверка порядка E4, хук вызова скиллов C7, скаффолд фактов C4, скилл инженерной позиции C3, сокращение стека C1, разрешение конфликтов C2, реестр бюджета внимания B3. Каждое закрытие — это T4b refresh, а не редактирование Domain.

---

## §6 Проверка соответствия E.5.3

Edition соответствует требованиям тогда и только тогда, когда читатель может ответить на все четыре вопроса (`E.5.3` CC-UD, `FPF-Spec.md:64890`):

1. **Направлена ли зависимость только вверх?** Да — `LAQF-Local → LAQF (Domain) → FPF Core`; реализация заимствует *идентификаторы и семантику* паттернов, но не наоборот (§1, §0).
2. **Является ли она ациклической — нет обратных рёбер?** Да — ни один Local-актив не является зависимостью Domain edition или Core; направление §4.1 spine соблюдается (§1 `e53ConformanceNote`).
3. **Записывает ли реализация что-либо в Domain edition или Core?** Нет — она отображает активы на Domain-идентификаторы; активы имеют эффект выполнения, edition — нет (§4 `blockedRuntimeOrBuildReading`).
4. **Являются ли пробелы отставанием, а не противоречием?** Да — 9 строк ⬜ + 19 строк ◐ представляют допустимое отставание в рамках `compatibilityBoundary` (§1); изменение Domain-паттерна порождает refresh line (§5 T4c), но не делает Local edition несоответствующей.

> Layer-2 зафиксирован. Карта реализации (§2) одновременно является бэклогом пробелов (§5); закрытие строки ⬜ — это T4b config-drift refresh, никогда не редактирование Domain. Далее (S7): включить данную edition + монолит паттернов в [[README]], [[seminar_timeline]], [[../../00-MoC]]; выполнить цикл качества E.21/E.19 + примечания admission.

## См. также

- [[12-20-local-practice-edition]] — английский оригинал
- [[12-00-spine]] — keystone: §4.1 направление edition, §4.2 записи зависимостей, §4.3 R1–R5, §6 план обновления G.11
- [[12-10-patterns-A]] · [[12-11-patterns-B]] · [[12-12-patterns-C]] · [[12-13-patterns-D]] · [[12-14-patterns-E]] · [[12-15-patterns-F]] — 30 Domain-паттернов, реализуемых данной edition
- [[../../03-current-config-map]] — источник истины реализации (инвентаризация, пробелы §4, конфликты §5, размер стека §6)
- [[12-01-source-pack]] — §6 словарь семейств MF-, используемый в карте реализации
- [[_inputs/rc-digest]] — рабочий дайджест 30-RC
- [[../11-fpf-diagnostic]] — решение D2 Laws-vs-Work (Layer A смягчает / C–F преобразуют)
- `FPF-Spec.md:64387` E.4.PFR · `:64835` E.5.3 · `:64890` CC-UD.1/2 · `:91923` G.11 · `:64478` reading-framework (no runtime/build reading)
