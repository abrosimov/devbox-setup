---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, keystone, e4-dpf]
seminar-iteration: 3
created: 2026-06-28
status: keystone
method: FPF E.4.DPF (спина авторинга) · E.4.PFAD (архитектурное решение) · E.4.PFR (дисциплина relation/edition) · F.18 (нейминг) · E.5.3 (однонаправленная зависимость) · G.11 (актуальность)
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-00-spine]]"
---

# LAQF — keystone-спина (E.4.DPF)

Это keystone (краеугольный камень) **LLM-Agent Quality Principle Framework (LAQF)**, созданный по спине Domain-Principle-Framework FPF (`E.4.DPF`, `FPF-Spec.md:64163`). Он фиксирует те части спины, от которых зависит остальной фреймворк — контекст, архитектурное решение, ратифицированное имя, дисциплину edition и relation, отобранный набор из 30 паттернов и маршрут обновления — чтобы тела паттернов (S3–S6) и измерительную рамку (S2) можно было авторить на стабильном фундаменте.

Тела паттернов здесь **не** живут. Этот файл — архитектура, а не каталог. Это артефакт *чтения и авторинга*: он не создаёт импортов, API, рантайм-зависимостей или build-семантики (`E.4.PFR`, `FPF-Spec.md:64478`).

## §0 Покрытие спины DPF (E.4.DPF:4, `FPF-Spec.md:64247`)

Спина из одиннадцати шагов и то, где каждый шаг закреплён. Этот файл (S1) фиксирует keystone-шаги; остальные перенаправлены вперёд к более поздним сессиям согласно [[PROGRESS]] §7.

| Шаг | Элемент спины E.4.DPF | Владелец | Состояние |
|---|---|---|---|
| 1 | Декларация контекста | этот файл §1 | ✅ S1 |
| 2 | Source pack (`G.2`) | [[12-01-source-pack]] | S2 |
| 3 | Архитектурное решение (`E.4.PFAD`) | этот файл §2 | ✅ S1 |
| 4 | Подготовка имени (`E.10` / `F.18`) | этот файл §3 | ✅ S1 |
| 5 | Допуск носителя / carrier admission (`C.33`–`C.35`) | этот файл §4.4 (заметка); полностью на S7 | ◐ S1 заметка |
| 6 | Черновики паттернов (`E.8`) | [[12-10-patterns-A]] … [[12-15-patterns-F]] | S3–S6 |
| 7 | Дисциплина relation & edition (`E.4.PFR`) | этот файл §4 (per-pattern relations идут с паттернами) | ✅ S1 |
| 8 | Цикл качества (`E.22`/`E.21`/`E.23`) | [[README]] + QA | S7 |
| 9 | Admission review (`E.19`) | [[README]] + QA (только если заявлен допуск) | S7 |
| 10 | Приземление в локальный монолит | эта папка; [[README]] first-entry carrier | S7 |
| 11 | Маршрут актуальности (`G.11`) | этот файл §6 | ✅ S1 |

---

## §1 Декларация контекста (E.4.DPF:1, `FPF-Spec.md:64247`)

| Слот | Декларация |
|---|---|
| **Bounded context** | Воркспейс `AION_AUTOPOIESEON` → проект `claude_improvements` → FPF-семинар, **итерация 3**. Построен на каталоге Κάτοπτρον ([[../../00-MoC]]) и его семинарских аудитах ([[../11-fpf-diagnostic]], [[../choosing_name_with_fpf_48]]). |
| **Предметная область** | Траблшутинг и улучшение качества **LLM-кодинг-агентов** — Claude Code как опорный экземпляр, но паттерны Уровня 1 контекстно-независимы. |
| **Целевой читатель** | FPF-грамотный практик, улучшающий поведение LLM-кодинг-агента; во вторую очередь — сопровождающий реализацию `dot_claude/` этого пользователя (Уровень 2). Для первого использования знаний FPF-разработчика не предполагается (дидактическая характеристика `E.4.DPF`, `FPF-Spec.md:64271`). |
| **Первое использование** | Отбирать и применять паттерны качества для диагностики, смягчения и верификации сбоев агента **в пределах конечного бюджета внимания/контекста** — связывающее ограничение, вскрытое [[../11-fpf-diagnostic]] D1. |
| **Граница неприменения** | Не бенчмарк-сьют, не патч весов Claude, не общий гайд по prompt-инжинирингу. Паттерны Уровня A **смягчают Законы, но никогда их не устраняют** ([[../11-fpf-diagnostic]] D2). Фреймворк **никогда не приземляется в `FPF-Spec.md` / FPF Core** (`E.5.3`, `FPF-Spec.md:64474`). |

**Двухуровневая форма** (замороженное решение #1, [[PROGRESS]] §2):

- **Уровень 1 — издание Domain Principle (LAQF):** 30 переиспользуемых, контекстно-независимых паттернов качества (`E.8`) + измерительная рамка (`A.19` CharacteristicSpace + `C.16` операционные полосы).
- **Уровень 2 — издание Local Practice:** реализация `dot_claude/` этого пользователя (хуки, скиллы, настройки), зависящая от Уровня 1 через `E.5.3`.

---

## §2 Архитектурное решение — E.4.PFAD (`FPF-Spec.md:63995`)

Одна relation `PrincipleFrameworkArchitectureDecision@Context`, заполненная в порядке, предписанном в `FPF-Spec.md:64054`.

```text
PrincipleFrameworkArchitectureDecision@Context:
  frameworkDecisionId:        LAQF.PFAD.iter3-s1
  governedFrameworkRef:       LAQF — LLM-Agent Quality Principle Framework
                              (издание Layer-1 Domain + издание Layer-2 Local Practice)
  boundedContextRef:          AION_AUTOPOIESEON / claude_improvements / FPF-seminar:iter3
  frameworkEditionRef:        LAQF v0.1 (издание Domain Principle, status=build)
  fpfCoreEditionRef:          FPF-Spec.md (edit-tracked копия в репо) — зависит от
                              семейства E.4, E.8, A.17–A.19, C.16, E.5.3, F.18, G.2, G.11
  decisionQuestion:           «Какое издание фреймворка характеризует и улучшает
                              качество LLM-кодинг-агента — как двухуровневый DPF, построенный
                              на E.4.DPF, приземляющийся локальным монолитом, зависящий от FPF
                              Core и ничего не пишущий в Core?»
  sourceBasisRefs:            [[../../01-symptoms-inventory]] (41 симптом);
                              [[../../10-root-causes-overview]] (30 RC);
                              [[../../02-external-research]] (~80 SoTA-источников);
                              [[../../04-reflection-evidence]]; [[../11-fpf-diagnostic]] (D2 Laws-vs-Work);
                              [[_inputs/rc-digest]] (рабочий дайджест)
  sotaSynthesisPackRefs:      → [[12-01-source-pack]] (пакет G.2, S2);
                              текущие якоря в [[_inputs/rc-digest]] §8
                              (IFScale; Laurenzo reads-per-edit; MRCR v2; уплотнение
                              токенайзера; откат brevity-cap у Anthropic; потолок
                              advisory-правил CLAUDE.md; стек инструкций в 509 строк)
  namingDecisionRefs:         этот файл §3 (F.18 Name Card `laqf-f18-iter3`);
                              ратифицирует замороженное решение #2
  selectedPatternSetRefs:     этот файл §5 (реестр из 30 паттернов); публикуется как
                              12-10…12-15 на протяжении S3–S6
  selectedPatternRelationRefs: этот файл §4.3 (репрезентативные записи);
                              per-pattern §12 relations идут с каждым паттерном
  publicationUnitRefs:        локальный монолит = папка `12-llm-agent-quality-dpf/`;
                              first-entry carrier = [[README]] (S7) + эта спина
  dependencyAndEditionRefs:   этот файл §4.1–§4.2 (FrameworkEditionDependencyRecords +
                              FrameworkPackageManifest); направление по E.5.3
  qualityEvaluationRefs:      → каркас E.22 + оценка E.21, S7 (заметка E.4.PFAD:4,
                              `FPF-Spec.md:64066`)
  admissionReviewRefs:        → E.19, S7, только если заявлена готовность к допуску /
                              внешнему ревью (`FPF-Spec.md:64066`)
  rejectedAlternatives:       (a) один уровень (паттерны без издания Local) —
                              теряет реализацию пользователя и историю зависимости E.5.3;
                              (b) приземление в FPF-Spec.md — запрещено E.5.3
                              (Core никогда не зависит от доменного издания);
                              (c) подмножество RC как паттерны — замороженное #1 требует все 30;
                              (d) только одна измерительная шкала — замороженное #1 сохраняет и
                              абстрактное пространство A.19, и операционные полосы
  rationaleRefs:              [[../11-fpf-diagnostic]] (D1 ограничение бюджета, D2 Laws-vs-Work,
                              D3 baseline, D4 WorkPlan DAG); [[PROGRESS]] §2 замороженные решения
  consequences:               30 полных паттернов E.8 — большой объём авторинга; смягчается
                              сессионным DAG S1–S7 + делегированием субагентам в S4–S6;
                              решения Уровня A могут лишь смягчать Законы (должны быть так оформлены);
                              двуязычность EN + -ru удваивает поверхность
  localMonolithLandingRefs:   `12-llm-agent-quality-dpf/` (замороженные #4, #5); не FPF-Spec.md
  sourceReturnConditions:     возврат к G.2 / [[../../02-external-research]] при распаде SoTA-якоря;
                              возврат к E.4.PFAD при изменении объёма или слоистости
  refreshOrSupersessionConditions: новое поколение модели; повышение издания FPF Core;
                              дрейф конфигурации dot_claude Уровня 2; повторяющаяся ошибка
                              читателя — см. §6 (G.11)
```

Проекция решения (носитель в стиле ADR через `C.32.ADR` / `E.17`) здесь **не** публикуется; согласно `FPF-Spec.md:64064` сначала должна существовать relation решения — этот раздел и есть эта relation.

---

## §3 Ратификация имени — прогон F.18 для LAQF (`FPF-Spec.md:85840`)

Замороженное решение #2 предварительно выбрало **LAQF**; `E.4.DPF:4` шаг 4 отправляет долговечные имена в `F.18`. Это **независимый** прогон F.18, который ратифицирует — или переоткрыл бы — имя, отзеркаливая метод [[../choosing_name_with_fpf_48]].

### §3.1 Восстановить управляемую ценность (F.18:4.1, `FPF-Spec.md:85926`)

| Инвариант | Содержание |
|---|---|
| Сначала управляемая ценность | Издание **Domain Principle Framework** Уровня 1 — 30 контекстно-независимых паттернов качества + измерительная рамка для LLM-кодинг-агентов. |
| Управляющий паттерн виден | `E.4.DPF` владеет родом фреймворка; `A.19`/`C.16` владеют измерительной ценностью; сам ярлык выбирается под `F.18`. |
| Bounded context виден | `claude_improvements` / FPF-seminar:iter3. Локален для этого воркспейса — **строка публичного термина `F.17` не задействована** (`FPF-Spec.md:85985`, F.18:4.4). |
| Локальный смысл виден | «Переиспользуемый паттерн-фреймворк для характеризации и повышения поведенческого качества LLM-кодинг-агентов.» |

**Mint/Reuse (F.8 через F.18):** MintNew. Ни один внешний стандарт не фиксирует этот ярлык; предварительный LAQF — внутренний прайор, свободно переминтящийся или подтверждаемый.

### §3.2 Набор кандидатов — 8 кандидатов, 4 семейства главного термина (F.18:4.3, `FPF-Spec.md:85974`)

- **Семейство A — Quality + Principle-Framework (верные роду DPF):** A1 · **LLM-Agent Quality Principle Framework (LAQF)**; A2 · Coding-Agent Quality Principle Framework (CAQF); A3 · Agent Quality Principle Framework (AQPF).
- **Семейство B — одна характеристика:** B1 · LLM-Agent Reliability Framework (LARF); B2 · LLM-Agent Behaviour Framework.
- **Семейство C — практика / форма Work:** C1 · LLM-Agent Quality *Practice* Framework; C2 · Coding-Agent Improvement Framework.
- **Семейство D — экосистема / греческая преемственность:** D1 · Katoptron Quality Framework.

### §3.3 Порядковая оценка (F.18:4.3 — High/Med/Low, никогда не усредняется; AliasRisk: low = хорошо)

| # | Кандидат | SemanticFidelity | CognitiveErgonomics | MorphologicalActionFit | AliasRisk *(low хорошо)* |
|---|---|---|---|---|---|
| A1 | LAQF | **High** — домен + характеристика + род DPF | **High** — чёткий 4-буквенный акроним | **High** — «Principle Framework» = форма DPF | **Low** — «LLM-Agent» обходит FPF `A.13` Agent; «Quality» слегка широк |
| A2 | CAQF | High — «Coding-Agent» наиболее точен по домену | Med — CAQF менее чёткий; «C» неоднозначно (Claude? Coding?) | High | Med — сужает до кодинга; Уровень 1 контекстно-независим |
| A3 | AQPF | Med — теряет квалификатор LLM/coding | Med | High | **High** — голый «Agent» сталкивается с FPF `A.13` + хайп вокруг agentic |
| B1 | LARF | Med — «Reliability» — одна из восьми характеристик | Med | High | Med — импортирует прототип SRE/reliability-engineering |
| B2 | — | Med — «Behaviour» расплывчат | Med | Med | Med |
| C1 | — | Med — называет качество | Med | Med | **High** — «Practice Framework» сталкивается с собственным изданием Layer-2 Local *Practice* этого проекта |
| C2 | — | Med — называет Work, а не артефакт | Med | **Low** — форма Work; мы именуем издание | Med |
| D1 | — | **Low** — «Katoptron» именует родительский каталог/корпус, а не это издание | High | Low — смешивает инструмент с фреймворком | **High** — читатель импортирует идентичность каталога |

**Правило доминирования (F.18:4.3, `FPF-Spec.md:85981`).** *X* доминирует *Y* тогда и только тогда, когда *X* ≥ *Y* по всем четырём измерениям (AliasRisk инвертирован) и строго лучше хотя бы по одному. A3, B1, B2, C1, C2, D1 — каждый доминируется A1. **A2 не доминируется** — он обходит A1 по SemanticFidelity (точность по кодингу), проигрывая по CognitiveErgonomics и AliasRisk.

→ **NQD-фронт = { A1 LAQF, A2 CAQF }.**

### §3.4 Выбор (F.18:4.3, `FPF-Spec.md:85983`)

Выбрано: **A1 — LAQF**, из фронта в два кандидата. *Что даёт:* широту (Уровень 1 — это **контекстно-независимое** качество агента, не только кодинг), самый чёткий акроним и уход от столкновения с FPF `A.13` Agent. *Остаточный риск:* «Quality» — широкий главный термин, а «LLM-Agent» чуть менее точен по домену, чем «Coding-Agent»; акроним опускает родовое слово *Principle*. Они зафиксированы, а не устранены — ровно то допущение F.18, что один кандидат может победить, не будучи идеальным.

### §3.5 Name Card (F.18:4.2, `FPF-Spec.md:85941`)

```text
NameCard:
  NameCardId:        laqf-f18-iter3
  GovernedValueRef:  издание Layer-1 Domain Principle Framework — 30 контекстно-независимых
                     паттернов качества LLM-кодинг-агента + измерительная рамка (A.19 + C.16)
  GoverningPatternRef: E.4.DPF (род фреймворка); A.19/C.16 (измерительная ценность); ярлык под F.18
  BoundedContextRef: AION_AUTOPOIESEON / claude_improvements / FPF-seminar:iter3
  LocalSenseRef:     «переиспользуемый паттерн-фреймворк для повышения поведенческого качества LLM-кодинг-агента»
  TechLabel:         LAQF — LLM-Agent Quality Principle Framework
  PlainLabel:        фреймворк качества агента
  CandidateSet:      A1 LAQF; A2 CAQF; A3 AQPF; B1 LARF; B2 LLM-Agent Behaviour Framework;
                     C1 LLM-Agent Quality Practice Framework; C2 Coding-Agent Improvement
                     Framework; D1 Katoptron Quality Framework
  RejectedCandidates:
    - CAQF (A2): на фронте, но сужение до кодинга повышает AliasRisk против
      контекстно-независимого Уровня 1; менее чёткий акроним. Отклонён выбором, не доминированием.
    - AQPF (A3): голый «Agent» сталкивается с ролью FPF A.13 Agent и хайпом вокруг agentic.
    - LARF (B1): «Reliability» называет одну из восьми характеристик, а не пространство качества.
    - C1: «Practice Framework» сталкивается с собственным изданием Layer-2 Local Practice этого проекта.
    - C2: называет Work (улучшение), а не издание фреймворка (несоответствие морфологии).
    - D1 Katoptron-*: называет родительский каталог/корпус — иную управляемую ценность.
  SelectionRationale:
    Даёт — широту (контекстно-независимое качество агента), чёткий акроним, уход от
    столкновения с A.13 Agent. Остаток — «Quality» широк; «LLM-Agent» чуть менее точен, чем
    «Coding-Agent»; акроним опускает «Principle». Независимо ратифицирует замороженное решение #2.
  BridgeRefs:        нет — совпадения написания с FPF «Agent» / «Quality» НЕ являются
                     заявлениями тождества (инвариант моста F.18:4.1, FPF-Spec.md:85938).
  UnifiedTermRowRef: нет — локально; F.17 не задействован (F.18:4.4).
  LineageEntries:
    - замороженное решение #2 ([[PROGRESS]] §2): предварительный LAQF, «LLM-Agent» чтобы обойти A.13.
    - iter3-S1 (этот файл): независимый прогон F.18; подтверждает LAQF на NQD-фронте из 2 кандидатов.
  RefreshCondition:
    Пересмотреть, когда (a) объём сужается до кодинга (→ переоткрывается CAQF); (b) объём
    расширяется за пределы агентов; (c) FPF переименовывает/расширяет A.13 Agent; или (d)
    повторяющаяся ошибка читателя читает «Quality» как QA/тестирование, а не пространство характеристик.
```

ID паттернов сохраняют ратифицированную основу **`LAQF.<Layer><n>`** (замороженное #3).

---

## §4 Дисциплина edition, relation & dependency — E.4.PFR + E.5.3 (`FPF-Spec.md:64387`, `:64835`)

### §4.1 Направление зависимости изданий (E.5.3, `FPF-Spec.md:64863`)

Только вверх, ациклично — зависимости указывают в сторону большей стабильности; более стабильное издание никогда не зависит обратно (`E.5.3` CC-UD.1/2, `FPF-Spec.md:64890`).

```text
издание Layer-2 Local Practice  ⟶  LAQF (издание Layer-1 Domain)  ⟶  FPF Core (FPF-Spec.md)
     (волатильно: dot_claude)         (полустабильно: 30 паттернов)      (стабильно: не зависит обратно)
```

### §4.2 Записи зависимостей изданий фреймворка (E.4.PFR, `FPF-Spec.md:64435`)

```text
FrameworkEditionDependencyRecord@Context:                # Domain → Core
  frameworkEditionRef:          LAQF v0.1 (издание Domain Principle)
  dependsOnEditionRefs:         FPF Core (FPF-Spec.md) — семейство E.4, E.8, A.17–A.19,
                                C.16, E.5.3, F.18, G.2, G.11
  dependencyReason:             заимствует конвенции авторинга паттернов, словарь характеристик /
                                метрик, нейминг, дисциплину source-pack и обновления
  compatibilityBoundary:        зависит от *семантики* паттернов Core, не от номеров строк;
                                line refs — удобные пины, перегрепнуть при повышении издания Core
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §6 (G.11) — триггер повышения издания Core
  e53ConformanceNote:           ациклично, только вверх; Core не зависит от LAQF (CC-UD.1/2)

FrameworkEditionDependencyRecord@Context:                # Local → Domain (+ Core)
  frameworkEditionRef:          LAQF-Local v0.1 (издание Layer-2 Local Practice)
  dependsOnEditionRefs:         LAQF v0.1 (Domain); транзитивно FPF Core
  dependencyReason:             реализация dot_claude инстанцирует паттерны Domain в
                                конкретные хуки, скиллы, настройки, команды
  compatibilityBoundary:        издание Local может отставать от Domain; изменение паттерна Domain
                                не переписывает молча конфиг Local — оно поднимает строку обновления
  deprecationOrSupersessionRefs: —
  refreshConditionRefs:         §6 (G.11) — триггеры изменения паттерна Domain + дрейфа dot_claude
  e53ConformanceNote:           Local → Domain → Core; обратного ребра нет (CC-UD.1/2)
```

### §4.3 Репрезентативные записи relation паттерн–фреймворк (E.4.PFR, `FPF-Spec.md:64421`)

Relations уровня архитектуры фиксируются сейчас; полные §12 relations каждого паттерна идут с паттерном (S3–S6).

```text
R1  PatternFrameworkRelationRecord@Context:
  relationId: LAQF.R.layerA-as-law
  sourceRef: паттерны LAQF Layer-A (A1–A8)   targetRef: FPF A.6.B Boundary Norm Square (квадрант Law)
  relationFunction: relation управляющего паттерна (оформление Law)
  governedUse: решения Layer-A оформляются как *смягчение Закона*, никогда не устранение
  directGoverningPatternRef: A.6.B + [[../11-fpf-diagnostic]] D2
  blockedStrongerReading: НЕЛЬЗЯ читать как устранение модель-внутренней причины
R2  relationId: LAQF.R.measurement
  sourceRef: 12-02-measurement-frame (8 характеристик)   targetRef: A.19 CharacteristicSpace + C.16
  relationFunction: relation управляющего паттерна
  governedUse: восемь осей — это характеристики A.19; операционные полосы через C.16 DHCMethod
  directGoverningPatternRef: A.19 / C.16   blockedStrongerReading: полосы — не жёсткие SLA
R3  relationId: LAQF.R.sota
  sourceRef: §11 SoTA-Echoing каждого паттерна   targetRef: пакет G.2 над [[../../02-external-research]]
  relationFunction: переиспользование источника/решения (по значению)
  directGoverningPatternRef: G.2   sourceReturnCondition: распад якоря → переуборка (§6)
R4  relationId: LAQF.R.local-edition
  sourceRef: издание Layer-2 Local Practice   targetRef: издание LAQF Domain
  relationFunction: зависимость изданий фреймворка
  directGoverningPatternRef: E.5.3 + G.11   dependencyOrEditionEffect: вверх, ациклично
R5  relationId: LAQF.R.e8-conformance
  sourceRef: все 30 тел паттернов   targetRef: конвенции авторинга E.8
  relationFunction: специализация (каждое тело соответствует 13-секционной форме E.8)
  directGoverningPatternRef: E.8   blockedStrongerReading: не новый мета-формат паттернов
```

### §4.4 Манифест пакета фреймворка (E.4.PFR, `FPF-Spec.md:64444`)

```text
FrameworkPackageManifest@Context:
  frameworkEditionRef:           LAQF v0.1 (издание Domain Principle)
  selectedPatternSetPublicationRef: реестр §5 → 12-10…12-15 (selected-set G.5, S3–S6)
  relationRecordRefs:            §4.3 R1–R5 + per-pattern §12 (S3–S6)
  dependencyAndEditionRecordRefs: §4.2 (Domain→Core, Local→Domain)
  editionStatus:                 build (keystone S1 зафиксирован; тела в ожидании)
  deprecationOrSupersessionRefs: —
  sourcePackRefs:                [[12-01-source-pack]] (S2); [[_inputs/rc-digest]]
  qualityEvidenceRefs:           → E.21/E.22, S7
  refreshPlanOrCurrentnessRefs:  §6 (G.11)
  firstEntryCarrierRefs:         [[README]] (S7) + эта спина
  blockedRuntimeOrBuildReading:  LAQF — фреймворк чтения/авторинга; манифест не создаёт
                                 импортов, API, рантайм-зависимостей или build-семантики
                                 (FPF-Spec.md:64478)
```

**Заметка о допуске носителя (E.4.DPF:4 шаг 5, `FPF-Spec.md:64251`).** Локальный монолит и эта спина используются как first-entry carrier; допуск носителя для захваченной/потерянной/произведённой структуры принадлежит `C.33`/`C.34`/`C.35` и завершается на S7, а не фабрикуется здесь.

---

## §5 Отобранный набор паттернов — индекс из 30 паттернов (вперёд к E.8, S3–S6)

Отобранный набор для манифеста (§4.4). Род FPF по [[../11-fpf-diagnostic]] D2: **Law** (проектировать внутри; смягчать) · **Boundary** (адаптироваться; предлагать апстрим) · **Design** (преобразовывать через Work). Характеристика обнаружения **предварительна** — финализируется относительно [[12-02-measurement-frame]] (S2). Названия предварительны до авторинга каждого паттерна.

Схема ID (замороженное #3): `LAQF.A1..A8`, `B1..B4`, `C1..C7`, `D1..D4`, `E1..E5`, `F1..F2` (30). Каждое тело паттерна несёт футер-сентинел `### LAQF.<id>:End` (H-9, без содержания).

| LAQF | RC | Предв. название | Род | Характеристика обнаружения (предв.) | S |
|---|---|---|---|---|---|
| **A1** | rc-01 | Substance-Gated Pushback | Law | sycophancy-rate | S3 |
| **A2** | rc-02 | Delta Over Whole-Artefact | Law | output-economy | S3 |
| **A3** | rc-03 | Answer-Budget Before Prose | Law | output-economy | S3 |
| **A4** | rc-04 | Effective-Fill Accounting | Law | context-integrity | S3 |
| **A5** | rc-05 | Read Before Assert | Law | reconnaissance-depth | S3 |
| **A6** | rc-06 | User-Anchored Facts Over Self-Draft | Law | reconnaissance-depth | S3 |
| **A7** | rc-07 | Reconnaissance Before Action | Law | reconnaissance-depth | S3 |
| **A8** | rc-08 | Literal Scope On Terse Feedback | Law | scope-fidelity | S3 |
| **B1** | rc-09 | Rotate Before The Cliff | Boundary | context-integrity | S4 |
| **B2** | rc-10 | Authoritative Handoff Re-Entry | Boundary | context-integrity | S4 |
| **B3** | rc-11 | Attention-Budget Ledger | Boundary | attention-budget-load | S4 |
| **B4** | rc-12 | Self-Imposed Output Budget | Boundary | output-economy | S4 |
| **C1** | rc-13 | Instruction-Stack Within Budget | Design | attention-budget-load | S4 |
| **C2** | rc-14 | Single-Owner Rule Resolution | Design | attention-budget-load | S4 |
| **C3** | rc-15 | Encoded Engineering Posture | Design | sycophancy-rate | S4 |
| **C4** | rc-16 | Tagged Facts Scaffold | Design | reconnaissance-depth | S4 |
| **C5** | rc-17 | Deterministic Over Advisory | Design | instruction-adherence | S4 |
| **C6** | rc-18 | Whole-Path Permission Coverage | Design | instruction-adherence *(ближайшая)* | S4 |
| **C7** | rc-19 | Enforced Skill Invocation | Design | instruction-adherence | S4 |
| **D1** | rc-20 | Re-Entry Across Phase Boundary | Design | scope-fidelity | S5 |
| **D2** | rc-21 | Atomic Single-Form Emission | Design | output-economy | S5 |
| **D3** | rc-22 | Roadmap-Anchored Dispatch | Design | scope-fidelity | S5 |
| **D4** | rc-23 | Enforced Role Lanes | Design | scope-fidelity | S5 |
| **E1** | rc-24 | Claim Requires Observed Event | Design | verification-fidelity | S5 |
| **E2** | rc-25 | Enforced Citation Anchors | Design | verification-fidelity | S5 |
| **E3** | rc-26 | Counter-Evidence Audit | Design | verification-fidelity | S5 |
| **E4** | rc-27 | Input-Order Fidelity | Design | verification-fidelity | S5 |
| **E5** | rc-28 | Quiet Toolchain Output | Design | output-economy | S5 |
| **F1** | rc-29 | Bounded Branch Freshness | Design | verification-fidelity *(ближайшая)* | S6 |
| **F2** | rc-30 | Deterministic Commit Hygiene | Design | instruction-adherence | S6 |

Восемь характеристик обнаружения (instruction-adherence, reconnaissance-depth, context-integrity, sycophancy-rate, output-economy, verification-fidelity, attention-budget-load, scope-fidelity) определены как `A.19` CharacteristicSpace в [[PROGRESS]] §5 и операционализированы полосами в [[12-02-measurement-frame]] (S2). Каждый паттерн привязан к ≥1 (замороженная конвенция авторинга, [[PROGRESS]] §3).

---

## §6 Маршрут актуальности и обновления — G.11 (`FPF-Spec.md:91923`)

Один `RefreshPlan@Context` для LAQF: назвать затронутый объект, род объекта актуальности, управляющий паттерн, действие с областью и ref отчёта (`G.11:0.2`, `FPF-Spec.md:91949`). LAQF — артефакт-seed DPF, поэтому строка обновления называет объект актуальности напрямую (`G.11:0.3`, `FPF-Spec.md:91952`).

```text
RefreshPlan@Context:
  RefreshPlanId:    LAQF.refresh.v0
  EntityOfConcernRef: LAQF v0.1 (издание Domain) + издание Layer-2 Local Practice
  TargetScope:      весь фреймворк (набор паттернов, измерительные полосы, source pack, издания)
  PlannedTriggers (причины обновления в стиле RSCR):
    T1 смена поколения модели    → новое поколение Claude (напр. 5.x): перетестировать каждый
                                  Закон (A1–A8); перемерить baseline; восемь полос могут сдвинуться
    T2 распад SoTA-источника     → якорь [[../../02-external-research]] вытеснен
                                  (IFScale, MRCR v2, reads-per-edit, токенайзер, brevity-cap):
                                  переуборка через G.2 → [[12-01-source-pack]]
    T3 повышение издания FPF Core → изменение E.4/E.8/A.19/C.16/F.18/G.11: перегрепнуть пины строк;
                                  перепроверить соответствие E.5.3
    T4 дрейф конфигурации Layer-2 → изменение dot_claude/ (хук/скилл/настройки): обновить
                                  маппинг издания Local Practice, не паттерны Domain
    T5 повторяющаяся ошибка читателя → неверное чтение имени/объёма (напр. «Quality» → QA):
                                  переоткрыть Name Card §3
  PlannedActions:   каждое делегирует своему управляющему паттерну — G.2 (source pack), E.21/E.23
                    (качество/улучшение паттернов), E.4.PFR (записи изданий), F.18 (имя)
  RequiredPins:     издание FPF Core; поколение модели Claude; набор SoTA-якорей; коммит dot_claude
  RefreshReportRef: → фиксируется в [[PROGRESS]] §9 (журнал сессий) при каждом обновлении
```

`G.11` фиксирует актуальность, распад источника, изменение издания и действие с областью; он **не** решает, улучшился ли фреймворк — это `E.21`/`E.23` (`FPF-Spec.md:91952`).

---

## §7 Проверка полноты спины (E.4.DPF:4 закрытие, `FPF-Spec.md:64275`)

Спина полна только когда читатель может ответить на все шесть:

1. **Какое издание фреймворка авторено?** LAQF v0.1, двухуровневый DPF (Domain + Local Practice) — §1, §2, §3.
2. **Какие источники и решения его сформировали?** Каталог Κάτοπτρον (41 симптом → 30 RC → ~80 SoTA-источников) + семинарский диагностик, через запись E.4.PFAD — §2, `sourceBasisRefs`.
3. **Какие паттерны и relations отобраны?** 30 паттернов (A1–F2) + записи relation R1–R5 и манифест — §4, §5.
4. **Где он опубликован?** Локальный монолит `12-llm-agent-quality-dpf/`, first-entry carrier [[README]] + эта спина; никогда не FPF Core — §2, §4.4.
5. **Как улучшается качество?** Каркас E.22 → оценка E.21 → улучшение E.23 на S7; обнаружение через восемь характеристик — §0, §5, §6.
6. **Когда он возвращается для обновления или ремонта?** Пять триггеров G.11 (поколение модели, распад SoTA, повышение Core, дрейф конфигурации, ошибка читателя) — §6.

> Keystone зафиксирован. Далее: **S2** — [[12-01-source-pack]] (SoTA-пакет G.2) + [[12-02-measurement-frame]] (полосы A.19 + C.16). S2 может идти параллельно с **S3** (заморозка стиля + Layer A) после ратификации этой спины ([[PROGRESS]] §7).

## См. также

- [[12-00-spine]] — английский двойник
- [[PROGRESS]] — журнал сборки (замороженные решения §2, конвенции §3, сессионный DAG §7)
- [[_inputs/rc-digest]] — рабочий дайджест 30 RC + 8 характеристик
- [[../11-fpf-diagnostic]] — ruling Laws-vs-Work (D2), ограничение бюджета (D1)
- [[../choosing_name_with_fpf_48]] — образец F.18 (метод Name Card)
- [[../../00-MoC]] · [[../../10-root-causes-overview]] · [[../../02-external-research]]
- `FPF-Spec.md:64163` E.4.DPF · `:63995` E.4.PFAD · `:64387` E.4.PFR · `:64835` E.5.3 · `:85840` F.18 · `:91923` G.11
