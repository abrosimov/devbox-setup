---
tags: [claude-improvements, phase2, fpf-diagnostic, audit, ru]
phase: 2
created: 2026-06-28
status: diagnostic
method: FPF (First Principles Framework) — A.7, A.6.B, A.3.1, A.15, A.19, C.16
lang: ru
canonical: "[[FPF_seminar/11-fpf-diagnostic]]"
---

# FPF-диагностика — структурный аудит каталога

FPF применён как спецификация-линза к собственным утверждениям каталога, перекрёстным ссылкам и предложенным фиксам. Не пересказ FPF — только те паттерны, которые вскрывают структурные проблемы в материале.

## D1 — Решение противоречит диагнозу (A.7 Strict Distinction)

Каталог диагностирует переполнение attention budget как компаундирующую корневую причину:

- [[rc-11-claude-md-attention-budget]]: модель удерживает ~150 инструкций; системный промпт съедает ~50.
- [[rc-13-claude-md-bloat]]: эффективный стек CLAUDE.md 509 строк — в 2.5–5× выше рекомендаций Anthropic.
- [[10-root-causes-overview#Cross-cutting design observations]] наблюдение #2: «Bloat compounds all other root causes. Trim CLAUDE.md before piling on new rules.»

Затем по 30 RC-файлам предписывается:

- ~25 новых скиллов ([[00-MoC#Fix surface frequency (across all 30 RCs)]])
- ~15 новых output-styles (тот же источник)
- ~10 новых хуков (тот же источник)
- ~10 новых команд (тот же источник)

**Нарушение FPF (A.7):** EntityOfConcern проблемы (ёмкость внимания модели — конечный измеримый бюджет) и EntityOfConcern решения (объём конфигурационных правил, потребляющих этот бюджет) находятся в одном CharacteristicSpace, но движутся в противоположных направлениях. Каталог замечает ограничение, но строит план так, будто оно не действует.

Ни один RC-файл не содержит **баланса по токенам**: сколько токенов каждый предлагаемый фикс добавляет vs сколько освобождает. Ограничение зафиксировано текстом, но не операционализировано как критерий отбора.

## D2 — Layer A RC — это Laws, а не устранимые причины (A.6.B Quadrant L vs A.15 Work)

[[10-root-causes-overview#Layer A — Model-internal (training / architecture)]] содержит 8 RC, классифицированных как «root causes» с «fix proposals»:

- [[rc-01-rlhf-pushback-loop]] — RLHF overcorrection анти-сикофантности
- [[rc-02-helpfulness-as-artefact]] — градиент полезности → «выдай готовый артефакт»
- [[rc-03-verbosity-task-complexity]] — 4.8 калибрует длину по воспринимаемой сложности
- [[rc-04-tokenizer-densification]] — токенизатор 4.7+ на 12–35% плотнее
- [[rc-05-tool-calling-preference-drop]] — 4.8 предпочитает рассуждение вызовам инструментов
- [[rc-06-no-working-memory]] — нет механизма рабочей памяти
- [[rc-07-asymmetric-ask-vs-guess]] — вопрос ощущается как стагнация
- [[rc-08-sycophantic-gap-filling]] — краткий фидбек → расширение скоупа

В терминах FPF (A.6.B Boundary Norm Square) это **Laws** (Quadrant L) — свойства обучения и архитектуры модели, которые пользователь изменить не может. Это граничные условия, внутри которых проектируем, а не причины, которые устраняем.

Слово «fix» в секции «Fix proposals» каждого RC-файла создаёт ложное ожидание: после выполнения фикса причина исчезнет. Ни один Layer A фикс не устраняет свою причину — все митигируют следствия. Сам каталог говорит это в [[10-root-causes-overview#Layer A — Model-internal (training / architecture)]]: «We can mitigate via prompting, hooks, and topology — we cannot directly change them.» Но шаблон файла ([[_writer-instructions#Per-RC file template]]) применяет одинаковый фрейминг «Fix proposals» ко всем слоям, стирая различие.

**FPF-корректный фрейминг:**

| Слой | FPF-вид | Отношение к Work |
|---|---|---|
| A (model-internal) | Laws / Constraints (A.6.B-L) | Проектируем внутри; митигируем эффекты |
| B (harness) | Environment boundary | Адаптируемся; предлагаем upstream-изменения |
| C (config) | Design space | Прямая трансформация через Work |
| D (workflow) | Design space | Прямая трансформация через Work |
| E (verification) | Design space | Прямая трансформация через Work |
| F (process) | Design space | Прямая трансформация через Work |

## D3 — Нет измерительного базиса (C.16)

Acceptance signals в RC-файлах содержат количественные утверждения без измеренного текущего состояния:

- [[rc-02-helpfulness-as-artefact#Acceptance signal]]: «Average output token count on feedback turns drops by ≥40% vs current baseline» — ни один файл не содержит текущее значение baseline.
- [[rc-15-engineering-attitude-skill-missing#Acceptance signal]]: «In 10 sessions involving stack-change questions, ≥7 propose shadow-mode or CBC pattern without the user prompting» — текущая частота не записана.
- [[rc-24-done-without-verification]] (ссылка в [[10-root-causes-overview]]): аудит утверждений «tests pass» — текущий false-positive rate не измерен.

По C.16 (Measurement & Metrics Characterisation) acceptance signal без measurement template с фактическими pre-intervention значениями нетестируем. Это аспирации, отформатированные как evidence.

## D4 — MethodDescription и WorkPlan не разделены (A.3.1, A.15.2)

Каталог структурирован как «pick an RC → implement fixes» — это MethodDescription (как-делать). WorkPlan (когда, в каком порядке, с какими зависимостями) отсутствует.

Между фиксами есть жёсткие зависимости, но они не смоделированы как DAG:

| Предусловие | Блокируемые фиксы | Почему |
|---|---|---|
| [[rc-13-claude-md-bloat]] trim | Любой новый `alwaysApply: true` скилл | Добавление к 509-строчному стеку усиливает диагностированную причину |
| [[rc-11-claude-md-attention-budget]] бюджетный учёт | Решение о количестве новых always-on ассетов | Без бюджетного числа отбор не ограничен |
| [[rc-14-inter-asset-conflicts]] разрешение конфликтов | Любое новое правило, способное конфликтовать | Новые правила поверх существующих конфликтов компаундируют |

[[00-MoC#How to use this catalogue across sessions]] предлагает: «Pick the RC with the highest impact-for-your-pain combination» — это отбор без учёта порядка зависимостей. Приглашает начать с самого болезненного симптома (напр. RC-15 engineering-attitude), а не с предусловия (RC-13 trim), что увеличит bloat, пытаясь уменьшить его эффекты.

## D5 — Fix proposals смешивают surfaces без учёта взаимодействия

Пример из [[rc-15-engineering-attitude-skill-missing#Fix proposals]]:

- F1: новый скилл `engineering-attitude` (`alwaysApply: true`) — добавляет always-on attention cost
- F2: расширение reviewer-агентов — добавляет пункты в review checklist
- F3: ссылки в frontmatter SE-агентов — добавляет per-agent нагрузку
- F4: новый output-style `engineer-posture` — добавляет opt-in output overhead
- F5: расширение хука `proposal_discipline.py` — добавляет UserPromptSubmit injection

Пять фиксов предложены независимо. Модели взаимодействия нет: что произойдёт, когда F1 + F2 + F3 + F5 сработают одновременно на одном ходу? Суммарная attention cost не оценена. По A.15.5 (Work-Entry Readiness) предусловие «помещается ли это в attention budget?» не проверено до того, как какой-либо фикс помечен готовым к реализации.

## D6 — Где банальный ИИ-ответ бесполезен

Типичный ИИ-ответ на этот каталог: «Отличный анализ. Давайте начнём с RC-15 (engineering-attitude) и RC-02 (delta-discipline) — они покрывают самые болезненные симптомы.»

Это бесполезно, потому что:

1. Добавление `engineering-attitude` (`alwaysApply: true`) к 509-строчному стеку усиливает [[rc-13-claude-md-bloat]], который каталог определяет как компаундирующий все остальные причины.
2. Начало с add-фиксов вместо trim-фиксов противоречит cross-cutting observation #2 самого каталога ([[10-root-causes-overview#Cross-cutting design observations]]).
3. Без baseline-измерения (D3 выше) ни один фикс нельзя верифицировать — усилие порождает нефальсифицируемые утверждения.

## Предложенный следующий рабочий ход

**Построить attention-budget ledger** — CharacteristicSpace (A.19) с C.16 measurement baseline.

Конкретные шаги:

1. **Измерить текущий always-on token load.** Подсчитать токены в: `USER_AUTHORITY_PROTOCOL.md` + все `alwaysApply: true` SKILL.md файлы + `additionalContext`-инъекции хуков + overhead системного промпта. Это одно число: текущее потребление бюджета.
2. **Установить целевой бюджет.** Опираясь на [[02-external-research#R6.1]] (IFScale: 68% accuracy при 500 инструкциях) и [[rc-11-claude-md-attention-budget]] (~150 эффективных инструкций), определить целевой потолок — напр. 200 эффективных строк после trim.
3. **Разметить каждый предложенный фикс двумя числами:** токены добавлены, токены освобождены. Фиксы только-добавление (новый скилл, новая hook-инъекция) получают положительную стоимость. Фиксы-обрезки (RC-13 сокращение CLAUDE.md, RC-14 удаление конфликтов) получают отрицательную стоимость.
4. **Это превращает 150+ fix proposals в constrained selection** (A.19.SelectorMechanism): максимизировать покрытие симптомов в пределах attention budget.

Результат: [[rc-13-claude-md-bloat]] переходит из «одного из 30 RC» в **предусловие с конкретной числовой целью**. Все add-фиксы получают числовой критерий входа: помещаются в оставшийся бюджет или нет.

## Состояние и точка продолжения

Эта сессия остановилась на **диагностике** (итерация 1). Следующая сессия начинается с:

1. Прочитать этот файл и [[FPF_seminar/11-fpf-diagnostic]] (EN-каноник).
2. Выполнить «следующий рабочий ход» выше — построить attention-budget ledger.
3. По результатам ledger — сформировать WorkPlan (DAG зависимостей между фиксами) как итерацию 2.

## See also

- [[00-MoC]]
- [[10-root-causes-overview]]
- [[rc-11-claude-md-attention-budget]]
- [[rc-13-claude-md-bloat]]
- [[rc-14-inter-asset-conflicts]]
- [[rc-15-engineering-attitude-skill-missing]]
- [[rc-02-helpfulness-as-artefact]]
- [[01-symptoms-inventory]]
- [[02-external-research]]
- [[FPF_seminar/11-fpf-diagnostic]] — EN canonical version
