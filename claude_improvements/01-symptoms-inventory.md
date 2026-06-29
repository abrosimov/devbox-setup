---
tags: [claude-improvements, phase1, symptoms, evidence]
phase: 1
created: 2026-06-27
status: ground-truth
source-feedback: "kabrosimov_notes/Notes inbox/Claude code behaviour.md"
---

# Symptoms inventory — atomic complaints from user feedback

Distilled from feedback note, related vault notes, and `future_projects/` artefacts. Each symptom is atomic; compound complaints were split. Verbatim quotes preserved in source language. Citations downstream cite by `S-NNN`.

## S-001 — Performance degrades past 55% context fill

- **Verbatim:** "Заметил что Клод код опус 4.7 начинает дико тупить когда заполненность контекста подход к 55%, поэтому в районе 60-65% надо переформулировать задачу с нуля давай инфу о том что сделано и делать новую сессию вероятно."
- **Source:** `Notes inbox/Claude code behaviour.md:10-11`
- **Gloss:** Opus 4.7 noticeably degrades around 55% context-window fill on a 1M-token window; user is forced to restart sessions around 60-65%.
- **Category:** context-mgmt
- **Severity:** high

## S-002 — Allow/deny command list is messed up

- **Verbatim:** "Еще интересная тема, составить список разрешенных и запрещенных команд как на рабочем компе так и на личном. Выглядит так, что у меня с настройками какая-то пизда, о чем Клод сообщил."
- **Source:** `Notes inbox/Claude code behaviour.md:13-14`
- **Gloss:** Current allow/deny list on both machines is broken; Claude itself flagged it.
- **Category:** permission-ux
- **Severity:** medium

## S-003 — Cites code/notes without context

- **Verbatim:** "Следующая вещь - он очень часто ссылается на код/часть заметок и пр, при этом не давая никакого контекта, что это и о чем. Надо его научить быть системнее в этом плане, т.к. у меня контекст не резиновый."
- **Source:** `Notes inbox/Claude code behaviour.md:16`
- **Gloss:** References code or notes by name without explaining what they are or why they matter; forces user to spend their own context to look up.
- **Category:** citation-discipline
- **Severity:** high

## S-004 — Returns results in non-deterministic / wrong order

- **Verbatim:** "Еще момент, отдает результаты в другом порядке, есть примеры проектов oicm-8015."
- **Source:** `Notes inbox/Claude code behaviour.md:18`
- **Gloss:** Output ordering does not match input/expected order; concrete examples exist in project oicm-8015.
- **Category:** ordering
- **Severity:** medium

## S-005 — Opus 4.8 is verbose ("графоман")

- **Verbatim:** "Последний Opus 4.8 - графоман, надо понять, как бы ему это урезать."
- **Source:** `Notes inbox/Claude code behaviour.md:20`
- **Gloss:** Opus 4.8 produces excessive prose. User wants it trimmed.
- **Category:** brevity
- **Severity:** high

## S-006 — Repeats itself and the user instead of supplying useful context

- **Verbatim:** "При этом ладно бы выдавал контекст к терминам/ссылкам на код. Но нет! Он себя и меня переповторяет постоянно. Жесть короче."
- **Source:** `Notes inbox/Claude code behaviour.md:20`
- **Gloss:** Verbosity is wasted on restating itself and the user instead of supplying genuine context.
- **Category:** repetition
- **Severity:** high

## S-007 — Asks questions too early instead of accumulating them

- **Verbatim:** "Нужно научить его копить вопросы до последнего, и задавать их только тогда, когда я говорю «что осталось перед имплементацией» или говорю «погнали». Вот в этот момент вопросы и должны появляться."
- **Source:** `Notes inbox/Claude code behaviour.md:22`
- **Gloss:** Should batch and defer questions until the user signals readiness ("what's left before implementation?", "let's go"). Currently asks too early and too incrementally.
- **Category:** inquiry-discipline
- **Severity:** high

## S-008 — Questions lack file/line/snippet context

- **Verbatim:** "При этом всегда с достаточным контекстом (ссылки на файлы, код, параграфы). Те не «прими решение по d32, вот такие опции», а «в d32 у нас написано «…», смотреть оригинал в таком-то файле, вот опции»"
- **Source:** `Notes inbox/Claude code behaviour.md:22`
- **Gloss:** Each question must carry full context: quoted text, file path, paragraph reference. Not "decide on d32, here are options".
- **Category:** inquiry-discipline
- **Severity:** high

## S-009 — Burns tokens re-confirming/paraphrasing user statements

- **Verbatim:** "Последний опус (4.7 или 4.8) жрет токены с тем, чтобы переподтвердить/пересказать своими словами твои суждения."
- **Source:** `Notes inbox/Claude code behaviour.md:24`
- **Gloss:** Spends tokens re-confirming or paraphrasing the user's own statements back at them.
- **Category:** repetition
- **Severity:** high

## S-010 — Doesn't push back by default; only paraphrases

- **Verbatim:** "Иногда он с ними спорит, если там видна дыра. Но он не спорит по умолчанию, а вот переформулировать - зло."
- **Source:** `Notes inbox/Claude code behaviour.md:24`
- **Gloss:** Argues only when a hole is obvious; default mode is paraphrase. Disagreement-on-substance is rare; restating is constant.
- **Category:** engineering-attitude
- **Severity:** medium

## S-011 — Output reads like pub-talk, not dry facts

- **Verbatim:** "Он должен давать сухой текст-фактуру. Не формат «попиздели с тохой и омаром в пабе», где мыслью можно по древу растечься"
- **Source:** `Notes inbox/Claude code behaviour.md:24`
- **Gloss:** Should produce dry factual text; current style meanders like a pub conversation.
- **Category:** brevity
- **Severity:** high

## S-012 — Runs ahead and pushes unsolicited initiatives

- **Verbatim:** "Далее, постоянно забегает вперед, проталкивает инициативы о которых не просили."
- **Source:** `Notes inbox/Claude code behaviour.md:26`
- **Gloss:** Constantly jumps ahead and pushes initiatives the user did not ask for.
- **Category:** initiative-creep
- **Severity:** high

## S-013 — Reframes instead of treating new info as clarification

- **Verbatim:** "Постоянно делает reframing, вместо того чтобы воспринимать доп информацию как уточнение."
- **Source:** `Notes inbox/Claude code behaviour.md:27`
- **Gloss:** Treats additional info as a chance to reframe the problem instead of folding it in as a clarification.
- **Category:** reframing
- **Severity:** high

## S-014 — Paraphrases user and draws odd conclusions

- **Verbatim:** "Пересказывает твои слова своими словами всегда и делает из них порой странные выводы."
- **Source:** `Notes inbox/Claude code behaviour.md:28`
- **Gloss:** Always paraphrases the user; sometimes draws strange conclusions from the paraphrase.
- **Category:** repetition
- **Severity:** high

## S-015 — Generates random unsupported assumptions up front

- **Verbatim:** "Сходу диалога делает набор assumptions, которые всегда рандомны и ничем не подкреплены. Нужно наоборот, сначала explore убедиться что все понятно, потом ждать сигнала к действию."
- **Source:** `Notes inbox/Claude code behaviour.md:28`
- **Gloss:** Opens dialogue with random, unsupported assumptions. Should instead explore first, confirm understanding, then wait for go-signal.
- **Category:** reconnaissance
- **Severity:** high

## S-016 — Rushes to solve before gathering enough data (4.7 regression)

- **Verbatim:** "Последнее вообще в Opus 4.7 стало проблемой - сразу бросается решать задачу, не собрав достаточно данных"
- **Source:** `Notes inbox/Claude code behaviour.md:29`
- **Gloss:** Opus 4.7 regression: jumps to solving without collecting sufficient input.
- **Category:** premature-action
- **Severity:** high

## S-017 — Over-uses push-back / "hypothesis disproven" pattern

- **Verbatim:** "Очень любит push back, гипотеза опровергается и вот это все. Нужно ему заложить Максиму фишера (найти бы пост) - ты инженер, у тебя есть задача и все доступное вокруг. Нерешаемых задач нет. Чего-то не хватает - создай."
- **Source:** `Notes inbox/Claude code behaviour.md:32`
- **Gloss:** Loves to push back and declare "hypothesis disproven"; user wants Fisher's-maxim engineering posture — no unsolvable tasks, build what's missing.
- **Category:** engineering-attitude
- **Severity:** high

## S-018 — Reinvents wheels instead of reaching for prior art

- **Verbatim:** "С другой стороны - изобретать велосипеды (привет из 2023, когда ты, Кирилл, хотел делать DAG руками, а МаксМ оказался более ленив и принес temporal)."
- **Source:** `Notes inbox/Claude code behaviour.md:33`
- **Gloss:** Symmetric failure — reinvents wheels rather than reaching for existing solutions (temporal-vs-hand-rolled-DAG anecdote).
- **Category:** engineering-attitude
- **Severity:** medium

## S-019 — Acts like a developer, not an engineer

- **Verbatim:** "Разработчики идут по пути наименьшего сопротивления, а инженеры решают поставленную проблему не обходя ее . Без костылей когда есть такая возможность"
- **Source:** `Notes inbox/Claude code behaviour.md:35`
- **Gloss:** Behaves like a developer (path of least resistance) instead of an engineer (solve the stated problem without workarounds when avoidable).
- **Category:** engineering-attitude
- **Severity:** high

## S-020 — Afraid to rewrite/swap stack, citing test-parity

- **Verbatim:** "Боится переписывать/менять стэк, мотивируя тем, что не понятно как тестировать разницу. Не умеет по умолчанию в shadow mode и continuous backward compatibility"
- **Source:** `Notes inbox/Claude code behaviour.md:37`
- **Gloss:** Refuses to propose rewrites/stack changes on "can't test the delta" excuse; lacks default fluency in shadow-mode and continuous backward compatibility.
- **Category:** engineering-attitude
- **Severity:** medium

## S-021 — Falls for false dichotomies without prompting

- **Verbatim:** "Учить еще надо, сам только после наводок соображает, про ложную дихотомию."
- **Source:** `Notes inbox/Claude code behaviour.md:39`
- **Gloss:** Only recognises false dichotomies after being explicitly nudged.
- **Category:** engineering-attitude
- **Severity:** medium

## S-022 — Doesn't look for "kill several birds" overlap

- **Verbatim:** "Еще момент - нужно уметь обходить задачи, находить общее/пересечение и думать «можем ли одним выстрелов двух (а лучше 5) зайцев убить»"
- **Source:** `Notes inbox/Claude code behaviour.md:41`
- **Gloss:** Fails to scan a backlog for shared structure / task overlap that could be solved with one move.
- **Category:** engineering-attitude
- **Severity:** medium

## S-023 — No bullshit detector

- **Verbatim:** "А еще, а еще. Нужно бы его научить (как?!?!?) bullshit detector."
- **Source:** `Notes inbox/Claude code behaviour.md:43`
- **Gloss:** Lacks a bullshit detector; open question how to instil one.
- **Category:** bullshit-detection
- **Severity:** medium

## S-024 — External locus of control / immature engineering posture

- **Verbatim:** "Ну и внутренний локус контроля (возвращаемся к engineering approach/culture). В целом от взрослый (mature) подход, который и в w&w поехать должен."
- **Source:** `Notes inbox/Claude code behaviour.md:45`
- **Gloss:** Needs an internal locus of control / mature engineering posture — own the outcome, do not blame the environment.
- **Category:** engineering-attitude
- **Severity:** medium

## S-025 — Does not pull fresh master into the working branch

- **Verbatim:** "Не тянет свежий мастер в ветку. Нужен протокол, подтягивать его после коммита и пр."
- **Source:** `Notes inbox/Claude code behaviour.md:47`
- **Gloss:** Never rebases/merges fresh master into the working branch; user wants a protocol that pulls master after each commit.
- **Category:** git-hygiene
- **Severity:** medium

## S-026 — Co-Authored-By trailer keeps reappearing

- **Verbatim:** "Claude mustn't include \"Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>\" comment"
- **Source:** `Notes inbox/Claude agents improvements.md:34`
- **Gloss:** Despite explicit ban in global protocol, Claude still adds Co-Authored-By trailers to commit messages.
- **Category:** instruction-adherence
- **Severity:** medium

## S-027 — Reports "task done, run build/lint" — and it fails

- **Verbatim:** "Agents report that they did their work and say \"run `go build` / lint / test\", when I'm trying to run - it fails (compilation, tests, linters)."
- **Source:** `Notes inbox/Claude agents improvements.md:41`
- **Gloss:** Sub-agents claim completion and ask the user to run build/lint/test, but those commands fail when the user runs them. Self-verification instruction is ignored.
- **Category:** premature-completion
- **Severity:** high

## S-028 — Skill suppression: Claude fixes code instead of running the skill

- **Verbatim:** "evals для всех скиллов + кейсы, когда claude не запустил скилл, а начал сам исправлять код - это прям наш кейс постоянный"
- **Source:** `Notes inbox/Notes on LLM.md:15`
- **Gloss:** Claude bypasses the configured skill and tries to patch the code directly. Eval coverage is missing.
- **Category:** skill-suppression
- **Severity:** medium

## S-029 — No proactive 5-7 option scenarios when call-to-action is absent

- **Verbatim:** "If there is no call to actions - agents should always propose options/scenarios 5-7. and mustn't perform any action"
- **Source:** `Notes inbox/Claude agents improvements.md:24`
- **Gloss:** When the user hasn't issued a call-to-action, agents should present 5-7 options/scenarios and do nothing. Currently they default to action.
- **Category:** premature-action
- **Severity:** medium

## S-030 — Command/skill namespace shadowing

- **Verbatim:** "Нет префикса у команд - овердап возможен просто потому что возможен."
- **Source:** `Notes inbox/Claude agents improvements.md:23,39`
- **Gloss:** User-defined commands can be shadowed by built-ins because nothing forces a prefix; collision possible by design. The `techne-` prefix discipline is the partial fix.
- **Category:** naming-discipline
- **Severity:** medium

## S-031 — Bare `git push` requires manual approval — friction

- **Verbatim:** "До изменений `Bash(git push *)` был полностью в `deny`. Это означало, что любой push требовал ручного одобрения, даже в feature-ветку."
- **Source:** `future_projects/git-push-policy.md:11-12`
- **Gloss:** Prior settings blanket-denied `git push`, forcing manual approval on every push — workflow friction. Now partially solved via three-echelon design.
- **Category:** permission-ux
- **Severity:** medium

## S-032 — Waterfall spec process

- **Verbatim:** "Скрытый waterfall. Пайплайн режет работу горизонтальными слоями: сначала вся спека → потом весь домен → потом весь план → потом код."
- **Source:** `future_projects/spec-workflow-redesign-proposal.md:15`
- **Gloss:** Pipeline forces horizontal-layer waterfall (full spec → full domain → full plan → code); reality invalidates assumptions before code starts.
- **Category:** workflow-design
- **Severity:** high

## S-033 — Monolithic output: one giant spec/domain file

- **Verbatim:** "Монолит. Спека — один большой файл. Неудобно читать ни человеку, ни LLM. То же с `domain_analysis.md` и `domain_model.md` — длинные простыни."
- **Source:** `future_projects/spec-workflow-redesign-proposal.md:14`
- **Gloss:** Specs and domain docs come out as monolithic walls of text. Unreadable for both humans and downstream LLM agents.
- **Category:** brevity
- **Severity:** high

## S-034 — Existing duplication: `X.md` + `X_output.json`

- **Verbatim:** "Дополнительно — дублирование: каждый агент пишет `X.md` + `X_output.json`, две заметки об одном и том же. Это уже существующая графомания."
- **Source:** `future_projects/spec-workflow-redesign-proposal.md:18`
- **Gloss:** Each pipeline agent writes both a markdown and a JSON file describing the same content — already-existing graphomania.
- **Category:** repetition
- **Severity:** medium

## S-035 — Manual slash-command dispatch, no parallelism

- **Verbatim:** "Тяжесть и ручной труд. Человек руками дёргает `/domain-analysis`, `/plan`, `/api-design`."
- **Source:** `future_projects/spec-workflow-redesign-proposal.md:16`
- **Gloss:** User manually invokes every stage; every stage is mandatory and produces another wall of text. No parallel dispatch.
- **Category:** workflow-design
- **Severity:** medium

## S-036 — No re-entry into spec after POC learning

- **Verbatim:** "Право процесса вернуться в спеку после POC, узнав «работает / не работает», и переписать `to-be` MVP с учётом узнанного. Сейчас этого нет — движение только вперёд по гейтам."
- **Source:** `future_projects/spec-workflow-redesign-proposal.md:51`
- **Gloss:** Pipeline is one-way through gates; no mechanism to re-enter the spec after a POC delivers learning that invalidates earlier assumptions.
- **Category:** workflow-design
- **Severity:** medium

## S-037 — TPM agent reads code directly (out of its lane)

- **Verbatim:** "TPM агент никогда не должен сам читать код. Это должны делать software engineers и перекладывать логику на понятном TPM языке."
- **Source:** `Notes inbox/Claude agents improvements.md:52`
- **Gloss:** TPM agent should never read source code itself. That's SE responsibility; SE translates to TPM-level language.
- **Category:** role-boundary
- **Severity:** medium

## S-038 — Out-of-scope decisions across agents

- **Verbatim:** "TPM and designer discussed one problem and then they agreed that it's only frontend problem. First, it's not their scope of responsibility, second - users can do whatever we can imagine and whatever we can't."
- **Source:** `Notes inbox/Claude agents improvements.md:47`
- **Gloss:** Agents make scope decisions outside their authority (TPM+designer declared an issue "frontend-only"), ignoring that any layer must gracefully degrade.
- **Category:** role-boundary
- **Severity:** medium

## S-039 — No roadmaps / milestones tracked across iterations

- **Verbatim:** "Нету роадмапов и майлстоунов."
- **Source:** `Notes inbox/Claude agents improvements.md:35`
- **Gloss:** The agent system has no notion of roadmaps or milestones; work is per-task with no longer-horizon spine.
- **Category:** workflow-design
- **Severity:** medium

## S-040 — No structured feedback channel outside CLI

- **Verbatim:** "Как получить возможность вне консоли дать фидбек к тому что есть?"
- **Source:** `Notes inbox/Claude agents improvements.md:38`
- **Gloss:** No channel to provide structured feedback on agent behaviour outside an active CLI session.
- **Category:** feedback-loop
- **Severity:** low

## S-041 — Lint/test output verbosity wastes tokens

- **Verbatim:** "Linters and tests output - first run is always silent (with disabled cache maybe(?)), if it fails - agent should run it again with output to json."
- **Source:** `Notes inbox/Claude agents improvements.md:43`
- **Gloss:** Lint/test commands dump full text output into the context every time; should default to silent then re-run with JSON output only on failure.
- **Category:** context-mgmt
- **Severity:** medium

## Related vault notes (cross-refs)

- `Notes inbox/Claude agents improvements.md` — broader agent/skill TODO list including S-026 (Co-Author leak), S-030 (prefix-shadowing), S-027 (false-done), S-037 (TPM-reads-code scope creep).
- `Notes inbox/Notes on LLM.md` — flags S-028 (skill bypass) as recurrent + missing eval coverage.
- `Notes inbox/Improving hooks in claude code.md` — wish-list for hooks (SessionStart resume, SubagentStop quality gate, PostToolUseFailure logging) targeting the same symptoms: lost context after compaction, agents shipping TODOs.
- `Notes inbox/Агенты, harness и context engineering..md` — wider context-engineering proposal: multi-layer harness, AgentStop-time validation, traceability so re-entry can locate where deviation began.
- `Notes inbox/О дальнейшем развитии автоматизации вокруг агентов и пр.md` — reflects premature frame-merging behaviour at meta-project level (wanted to merge w&w and UOV immediately) — symmetric to S-013 (reframing) + S-012 (initiative creep).

## See also

- [[02-external-research]] — Anthropic docs + community evidence
- [[03-current-config-map]] — current config asset map
- [[00-MoC]] — Map of Content hub
