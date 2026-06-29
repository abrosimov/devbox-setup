---
tags: [claude-improvements, fpf-seminar, laqf, dpf-build, measurement-frame, a19-charspace, c16-mmchr]
seminar-iteration: 3
created: 2026-06-28
status: measurement-frame
method: FPF A.19 (CharacteristicSpace) · C.16 (MM-CHR / U.DHCMethod) · A.17 (Characteristic) · A.18 (CSLC) · consumes G.2 pack LAQF.sota.iter3.palette
framework: LAQF — LLM-Agent Quality Principle Framework
language-twin: "[[12-02-measurement-frame]]"
---

# LAQF — измерительная рамка (A.19 CharacteristicSpace + C.16 операционный оверлей)

Это объявленный `CharacteristicSpace`, против которого измеряет LAQF (`A.19`, `FPF-Spec.md:24417`). Он чеканит восемь измерительных характеристик, на которые спина ссылается вперёд ([[12-00-spine]] §5, отношение R2), потребляя §3 `OperatorAndObjectInventory` и §4.2 записи `Γ_epist` пакета G.2 **по id** — никогда не перепересказывая доказательства (`G.2:4.2` контракт передачи, `FPF-Spec.md:87904`). Каждая характеристика получает одну карточку `U.DHCMethod` (одна Characteristic, одна Scale, заявленная полярность, заготовка доказательства — `C.16`, `FPF-Spec.md:42826`); зелёная/жёлтая/красная **полосы — это отдельно поименованный CAL-оверлей**, а не запечённый в голые методы, поскольку пороги и полосы приёмки вне объёма шаблона `U.DHCMethod` (`C.16:5.3.1` R-MT-3 оставляет на шаблоне лишь полярность + цель, `FPF-Spec.md:42945`; `A19-CS-5` запрещает скрытые нормализации внутри пространства, `FPF-Spec.md:24544`). Рамка передаёт каждую характеристику в слот обнаружения её паттерна в S3–S6 (§5).

## §0 Объём / entityOfConcern (A.19:0, `FPF-Spec.md:24428`)

| Slot | Декларация |
|---|---|
| **entityOfConcern** | `⟨GroundingHolon = an LLM coding agent in a session, ReferencePlane = world⟩` — поведение агента под конечным бюджетом внимания/контекста, а не веса модели (унаследовано из [[12-01-source-pack]] §0). |
| **Bounded context** | `AION_AUTOPOIESEON` / `claude_improvements` / FPF-семинар:iter3 ([[12-00-spine]] §1). |
| **Consumed palette** | `SoTAPaletteDescription` **`LAQF.sota.iter3.palette`** ([[12-01-source-pack]] §8): §3 `OperatorAndObjectInventory` (8 кандидатов-характеристик + 6 заготовок семейств операторов), §4.2 `Γ_epist` **G.2-F1** (обрыв контекста) + **G.2-F2** (потолок instruction-adherence), `ClaimSheets` T1–T5, `MicroExamples` ME-1…ME-4, `MethodFamilyCards` MF-1…MF-6. |
| **Space object** | EoC по A.19 здесь — это **сам CharacteristicSpace** (`LAQF.charspace.iter3`, §1), а не таблица оценок, дашборд или результат оценки над ним (`A.19:1` урегулирование E.24.UK, `FPF-Spec.md:24455`). |
| **Plane discipline** | Все восемь характеристик одно-сущностны (`U.EntityCharacteristic`, `A.17:4` R8, `FPF-Spec.md:24181`) для холона агент-в-сессии; реляционных слотов нет. |

---

## §1 Объявление CharacteristicSpace — A.19 (`FPF-Spec.md:24512`)

`U.CharacteristicSpace` **`LAQF.charspace.iter3`** = декартово произведение восьми наборов значений слотов (`A.19:5.1.1`, `FPF-Spec.md:24526`). Каждый слот связывает **ровно одну** Characteristic с **ровно одной** Scale (`A19-CS-1`, `FPF-Spec.md:24536`), с заявленной полярностью по `A.17:4` R6 (`FPF-Spec.md:24177`). Базис — упорядоченный список слотов ниже (`A19-CS-2` поименованный базис, `FPF-Spec.md:24538`).

```text
U.CharacteristicSpace  LAQF.charspace.iter3
  basis (ordered slots, A19-CS-2):
    s1 instruction-adherence   Scale: rate 0–1 (violations/session, read as 1−rate)  polarity: ↑-better
    s2 reconnaissance-depth    Scale: ratio ≥0 (reads-per-edit)                       polarity: ↑-better (diminishing)
    s3 context-integrity       Scale: % effective-fill 0–100                          polarity: target-is-best (low band)
    s4 sycophancy-rate         Scale: rate (modified-version events / 50 turns)       polarity: ↓-better
    s5 output-economy          Scale: count (tokens|lines / turn|stage)               polarity: ↓-better (floored)
    s6 verification-fidelity   Scale: rate 0–1 (claims-with-observed-event / claims)  polarity: ↑-better
    s7 attention-budget-load   Scale: count (instruction-stack lines; conflict pairs) polarity: ↓-better (ceiling)
    s8 scope-fidelity          Scale: ratio 0–1 (edit-target ∩ named-scope / edits)   polarity: ↑-better
  arity:            all slots U.EntityCharacteristic (bearer = agent-in-session), A.17:4 R8
  comparability:    same-template only (C.16 R-CMP-1, FPF-Spec.md:43007); cross-slot comparison undefined
  normalisation:    NONE inside the space (A19-CS-5, FPF-Spec.md:24544) — the eight are
                    NOT summed, averaged, or folded into a single LAQF score
  declared overlay: LAQF.cal.iter3 (§3) — a CAL band overlay; the ONLY declared overlay,
                    attached explicitly, not implicit (A.19:5.1.3, FPF-Spec.md:24552)
  missingness:      a slot with no observable event in a session reads not-applicable,
                    not zero (A19-CS-6 slot-meta completeness, FPF-Spec.md:24548)
```

**Единой оценки нет.** В этой рамке нет `ScoringMethod 𝒢` над восемью координатами. Любая будущая композита должна быть явным внешним `𝒢` на векторе координат, раскрытым с ограниченным кодоменом и полярность-совместимой монотонностью (`A.17:4.1` I7, `FPF-Spec.md:24193`; `C.16` R-G𝒢-1, `FPF-Spec.md:43012`) — она намеренно здесь не чеканится.

---

## §2 Карточки DHCMethod по характеристике — C.16 (`FPF-Spec.md:42937`)

Один `U.DHCMethod` на слот: одна Characteristic, одна Scale, заявленная полярность (R-MT-1/-3, `FPF-Spec.md:42941`), измерительный оператор и `U.EvidenceStub` (R-EV-1 тип-основания + идентификатор, `FPF-Spec.md:42991`). **Пороги отсутствуют по замыслу** — они живут в §3.

```text
U.DHCMethod  laqf.mm.s1.instruction-adherence
  characteristic: instruction-adherence       scale: rate 0–1        polarity: ↑-better
  operator:       1 − (stated-rule-violated events ÷ stated-rule-applicable events) per session
  evidenceStub:   hook logs (PreToolUse exit-2 fires), tool-call history, commit-trailer scans [L22 OTel]
  backing:        G.2-F2 (instruction-adherence ceiling); L15 (CLAUDE.md ≈70% advisory); L12 (IFScale 68%@500)

U.DHCMethod  laqf.mm.s2.reconnaissance-depth
  characteristic: reconnaissance-depth         scale: ratio ≥0       polarity: ↑-better (diminishing)
  operator:       count(Read|Grep|Glob calls) ÷ count(Edit|Write calls) per task
  evidenceStub:   tool-call history (read-class vs edit-class events) [L22]; Disclosure-block presence
  backing:        ME-1 [L05] (reads-per-edit 6.6→2.0); L02 (literal, reasoning-over-tool-calls)

U.DHCMethod  laqf.mm.s3.context-integrity
  characteristic: context-integrity            scale: % fill 0–100   polarity: target-is-best
  operator:       effective-fill % = tokens-in-window ÷ window-budget, tokenizer-adjusted (+~30% per L03)
  evidenceStub:   session token meter; post-compaction task-identity check (constraints retained?) [L22]
  backing:        G.2-F1 (operational cliff); ME-3 [L10] (MRCR 93→76%); L07, L08, L11 (50/60/75 cluster)
  target:         stay below the operational fill band (R-MT-3 names the target; band itself → §3)

U.DHCMethod  laqf.mm.s4.sycophancy-rate
  characteristic: sycophancy-rate              scale: rate           polarity: ↓-better
  operator:       count("modified version of what was asked" events) per 50 turns
  evidenceStub:   turn transcript; multi-file edits triggered by single-item feedback [L22]
  backing:        ME-2 [L06] (arguing loop, modified-version); L19 (RLHF sycophancy, over-correction)

U.DHCMethod  laqf.mm.s5.output-economy
  characteristic: output-economy               scale: count          polarity: ↓-better (floored)
  operator:       tokens/turn; lines/stage; tokens/Bash on passing runs
  evidenceStub:   emission length per turn; toolchain stdout volume on green runs [L22]
  backing:        L04 (≤25/≤100 brevity cap reverted after 3% eval drop — the FLOOR); L03 (tokenizer)

U.DHCMethod  laqf.mm.s6.verification-fidelity
  characteristic: verification-fidelity        scale: rate 0–1       polarity: ↑-better
  operator:       count(terminal claims backed by an observed tool event) ÷ count(terminal claims)
  evidenceStub:   claim ↔ tool-call-history join; citation anchors resolved to path/quote [L22]
  backing:        ME-4 [L20] (disobeyed direct commands → claim≠event); L16 (Plan-Mode gate)

U.DHCMethod  laqf.mm.s7.attention-budget-load
  characteristic: attention-budget-load        scale: count          polarity: ↓-better (ceiling)
  operator:       instruction-stack line count + conflicting-rule-pair count + always-on-skill token ratio
  evidenceStub:   measured stack (UAP+project+workspace CLAUDE.md); conflict register [L23]
  backing:        G.2-F2; L12 (IFScale 68%@500, earlier-instruction bias); L23 (509-line stack)
  target:         below the model's ~150-instruction effective attention (R-MT-3 target; band → §3)

U.DHCMethod  laqf.mm.s8.scope-fidelity
  characteristic: scope-fidelity               scale: ratio 0–1      polarity: ↑-better
  operator:       count(edits whose target ∈ user-named scope) ÷ count(edits); inverse: out-of-lane calls
  evidenceStub:   edit-target paths vs named-scope set; per-agent tool/scope lane logs [L22]
  backing:        L02 (literal, no one-to-another generalisation); L18 (subagent scope lanes)
```

Каждая карточка заявляет свою рамку применимости (холон агент-в-сессии, R-MT-4, `FPF-Spec.md:42947`) и временную стойку *как-наблюдено-за-сессию* или *как-агрегировано-по-окну* (R-ME-4, `FPF-Spec.md:42967`). Ни одна карточка не несёт границы зелёная/жёлтая/красная — это работа CAL-оверлея (§3).

---

## §3 CAL-оверлей калибровки — полосы (`LAQF.cal.iter3`)

**Отдельно поименованный, явно объявленный** оверлей над `LAQF.charspace.iter3`. Он прикрепляет зелёную/жёлтую/красную полосу + опережающий индикатор к каждому слоту. Объявлен здесь, не в пространстве §1 и не в методах §2, по `A19-CS-5` (`FPF-Spec.md:24544`) и `C.16` R-CMP-2 (преобразованная/пороговая сравнимость **цитируется, а не определяется** на методе, `FPF-Spec.md:43010`). Каждая полоса цитирует id своего подкрепляющего пакета. Полосы, заякоренные на единственном интерполированном числе, помечены **[interp]** — это калибровочные выборы, а не цитируемые SLA, в согласии с честной трактовкой обрыва в исходном пакете (G.2-F1 `residualLoss`).

```text
CALOverlay  LAQF.cal.iter3   attachesTo: LAQF.charspace.iter3 (§1)   status: calibration, not SLA
```

| Slot | Green | Amber | Red | Backing id |
|---|---|---|---|---|
| s1 instruction-adherence | ≥0.90 (≤1 нарушение/10 применимых) | 0.70–0.90 | <0.70 | G.2-F2; L15 (≈70 % advisory-потолок = граница жёлтая/красная); L12 |
| s2 reconnaissance-depth | ≥3.0 чтений на правку | 2.0–3.0 | <2.0 | ME-1 [L05] (2.0 = пол Laurenzo = красная граница; ≥3.0 цель) |
| s3 context-integrity | <50 % эффективного заполнения | 50–75 % | >75 % | G.2-F1; L11 (50 рано / 60 явно / 75–77 autocompact). ~55 % точка ротации = **[interp]**, не жёсткая линия |
| s4 sycophancy-rate | 0 изменённых-версий / 50 ходов | 1–2 / 50 ходов | ≥3 / 50 ходов | ME-2 [L06]; L19. Пороги полос **[interp]** (контролируемого session-rate не существует) |
| s5 output-economy | только задаче-необходимое содержание | лёгкое раздувание | графомания | L04 (**пол**: НЕ зажимать ниже задаче-необходимого — ≤25/≤100 вызвало падение eval 3 %). Жёсткого верхнего числа нет |
| s6 verification-fidelity | ≥0.95 утверждений-с-событием | 0.80–0.95 | <0.80 | ME-4 [L20]; L16. Пороги полос **[interp]** от находки «prompt-уровневое don't не есть запрет» |
| s7 attention-budget-load | ≤~150 строк стека, 0 конфликтующих пар | 150–509 строк | >509 строк | G.2-F2 (~150 внимания); L23 (509-строчный измеренный baseline = красная граница); L12 |
| s8 scope-fidelity | ≥0.95 правок в объёме | 0.80–0.95 | <0.80 | L02; L18. Пороги полос **[interp]** от находки буквального объёма |

**Дисциплина пола (s5).** `output-economy` есть `↓-better`, но **с полом**: зелёная полоса — это «задаче-необходимое содержание», а не «минимум токенов». L04 — явный пол: Anthropic откатил лимиты ≤25/≤100 слов после падения eval 3 %. Пере-зажим — это красно-эквивалентный отказ на *другой* стороне; оверлей не задаёт жёсткого нижнего числа (`R-MT-3` отказывается от семантики допуска/спада, `FPF-Spec.md:42945`).

**Честность интерполяции.** Точка ротации ~55 % у s3 и пороги полос s4/s6/s8 — это калибровочные интерполяции над цитируемыми доказательствами, а не контролируемые измерения. Они переполосуются при обновлении (§6). Сам G.2-F1 фиксирует, что ни одно контролируемое исследование не фиксирует единый % для обрыва.

---

## §4 Опережающие vs запаздывающие индикаторы

Для каждого слота: дешёвый **опережающий** сигнал, наблюдаемый в середине сессии (то, что Layer-2 Local Practice-издание подключает к хукам/телеметрии, L22), против **запаздывающего** исхода, который его подтверждает.

| Slot | Опережающий (середина сессии, дёшево) | Запаздывающий (исход) |
|---|---|---|
| s1 instruction-adherence | счёт near-miss хука PreToolUse; попадания trailer-scan | события нарушения заявленного правила, всплывающие в ревью |
| s2 reconnaissance-depth | живой коэффициент чтений на правку; присутствие Disclosure-block | события преждевременного действия / переделки (ME-1 дефолт самого дешёвого действия) |
| s3 context-integrity | % эффективного заполнения (с поправкой на токенайзер) | потеря идентичности задачи после компакции; сброс ограничения (B2) |
| s4 sycophancy-rate | флаг «изменённой версии» по ходу | мультиходовой цикл препирательства (3–5 ходов, ME-2) |
| s5 output-economy | бегущий счётчик токенов/ход, строк/стадию | сообщённая читателем графомания / недопоставка |
| s6 verification-fidelity | флаг утверждения-эмитированного-без-предшествующего-tool-event | ложное «build/test passed», доходящее до пользователя (E1) |
| s7 attention-budget-load | счёт строк стека инструкций; регистр конфликтующих пар | дрейф соблюдения с ростом стека (плато G.2-F2) |
| s8 scope-fidelity | флаг цель-правки ∉ названный-объём; вызов вне-полосы | расползание объёма / нарушение границ роли (D4) |

Опережающий столбец — операционная нагрузка: он вычислим из истории вызовов инструментов, логов хуков и событий OTel ([L22]) **без** ожидания запаздывающего исхода. Это ось обнаружения §5, которую потребляет слот §11 каждого паттерна S3–S6.

---

## §5 Индекс паттерн ↔ характеристика

Каждая характеристика — **первичная ось обнаружения** для паттернов ниже (вытянуто из реестра [[12-00-spine]] §5 и [[_inputs/rc-digest]] §7). Это передача, которую потребляет слот §11/обнаружения каждого паттерна S3–S6 (отношение спины R2, [[12-00-spine]] §4.3).

| Slot | Characteristic | Первичная ось обнаружения для (паттерны LAQF) |
|---|---|---|
| s1 | instruction-adherence | C5, C6, C7, F2 |
| s2 | reconnaissance-depth | A5, A6, A7, C4 |
| s3 | context-integrity | A4, B1, B2 |
| s4 | sycophancy-rate | A1, C3 |
| s5 | output-economy | A2, A3, B4, D2, E5 |
| s6 | verification-fidelity | E1, E2, E3, E4, F1 |
| s7 | attention-budget-load | B3, C1, C2 |
| s8 | scope-fidelity | A8, D1, D3, D4 |

Все 30 паттернов (A1–F2) покрыты; каждый подключается к ≥1 характеристике (замороженная конвенция авторинга, [[12-00-spine]] §5). Там, где спина пометила ось «*(nearest)*» (C6 → s1, F1 → s6), эта ближайшая подгонка сохраняется до по-паттернного авторинга.

---

## §6 Соответствие и обновление

**Соответствие A.19 / C.16 / A.17 / A.18.**

1. **Одна характеристика, одна шкала на слот** — `A19-CS-1` (`FPF-Spec.md:24536`), C.16 R-MT-1 (`FPF-Spec.md:42941`): все восемь карточек (§2) связывают ровно одну Characteristic с одной Scale.
2. **Полярность объявлена на шаблоне** — `A.17:4` R6 (`FPF-Spec.md:24177`), C.16 R-MT-3 (`FPF-Spec.md:42945`): каждый слот объявляет ↑/↓/target (§1, §2).
3. **Нет неявной нормализации между восемью** — `A19-CS-5` (`FPF-Spec.md:24544`): единой оценки LAQF нет; кросс-слотовое сравнение не определено (C.16 R-CMP-1, `FPF-Spec.md:43007`).
4. **Полосы как объявленный оверлей, не запечённый** — `LAQF.cal.iter3` (§3) — единственный объявленный оверлей (`A.19:5.1.3`, `FPF-Spec.md:24552`); пороги держатся вне голых методов (C.16 R-MT-3 отказывается от допуска/спада, R-CMP-2 цитирует преобразованную сравнимость, `FPF-Spec.md:43010`).
5. **Заготовка доказательства на метод** — C.16 R-EV-1 (`FPF-Spec.md:42991`): каждая карточка называет тип-основания + идентификатор (логи хуков, история вызовов инструментов, события OTel [L22]).
6. **Потребление по id** — всё подкрепление цитирует компоненты пакета по L-id / ME-id / Γ_epist id, никогда не пересказ (`G.2:4.2`, `FPF-Spec.md:87904`).

**Обязательные пины.** `CharacteristicSpaceId = LAQF.charspace.iter3`; `CALOverlayId = LAQF.cal.iter3`; потребляемый `SoTAPaletteDescriptionId = LAQF.sota.iter3.palette`; `GammaEpistSynthId = {G.2-F1, G.2-F2}`.

**Маршрут обновления (делегирует спине §6 / G.11, `FPF-Spec.md:91923`).** Переполосуй, когда SoTA-якорь вытеснен. Рамка не владеет собственным словарём обновления — она называет объект актуальности и делегирует спине `RefreshPlan@Context` `LAQF.refresh.v0` ([[12-00-spine]] §6), по `G.11:0.3` (DPF-seed-артефакты называют объект актуальности напрямую, `FPF-Spec.md:91952`):

- **спина T1 (поколение модели)** → перетестировать полярности и переизмерить все восемь полос (поколение 5.x может сдвинуть обрыв и потолок внимания).
- **спина T2 (распад SoTA)** → якорь вытеснен (IFScale, MRCR v2, reads-per-edit, токенайзер, brevity-cap, baseline 509 строк) → переуборка через G.2 → [[12-01-source-pack]], затем переполосовать затронутый(е) слот(ы) в §3.
- **спина T3 (апгрейд Core)** → перегрепнуть пины `FPF-Spec.md:<line>` для A.17–A.19 / C.16; перепроверить соответствие `A19-CS-5`.

`G.11` фиксирует объёмное действие переполосовки; он **не** решает, улучшилась ли рамка — это E.21/E.23 на S7 (`FPF-Spec.md:91952`).

---

## См. также

- [[12-02-measurement-frame]] — английский двойник
- [[12-01-source-pack]] — пакет SoTA G.2; потреблены §3 инвентарь + §4.2 Γ_epist (палитра `LAQF.sota.iter3.palette`)
- [[12-00-spine]] — keystone; §5 реестр паттернов, §4.3 отношение R2, §6 маршрут обновления
- [[_inputs/rc-digest]] — §7 восемь характеристик, §8 SoTA-якоря
- [[PROGRESS]] — журнал сборки (§7 сессионный DAG, §8 инвентарь, §9 журнал)
- `FPF-Spec.md:24417` A.19 CharacteristicSpace · `:24129` A.17 Characteristic · `:24265` A.18 CSLC · `:42826` C.16 MM-CHR · `:87746` G.2 · `:91923` G.11
