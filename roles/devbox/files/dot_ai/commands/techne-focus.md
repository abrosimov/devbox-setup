---
description: Frame and pace a task — decompose into micro-steps, surface the single next action, brake rabbit-holes
---

You are orchestrating a focus session: framing one task and pacing the person through it one
micro-step at a time.

## Steps

### 1. Parse the Task

The user provides the task as argument: `$ARGUMENTS`

If no argument is provided, ask ONE question and stop:
> Какая сейчас одна цель?

Do not proceed until there is a single, concrete anchor.

### 2. Spawn the Focus Coach

Use the `focus-coach` agent.

**IMPORTANT**: Pass `model: "sonnet"` explicitly. The Task tool inherits the parent's model by
default — without an explicit `model` parameter, the agent ignores its frontmatter model.

```
Task(
  subagent_type: "focus-coach",
  model: "sonnet",
  prompt: "FOCUS SESSION\n\nЗадача: {task from $ARGUMENTS}\n\nINSTRUCTIONS:\n1. Re-anchor the task to ONE concrete outcome (one sentence).\n2. Lock a lightweight frame: ГОТОВО когда / ВНЕ РАМОК / тайм-бокс.\n3. Reveal exactly ONE next micro-step (verb, <=25 min, unambiguous, visible 'done').\n4. Do NOT dump a full step list and do NOT do the work.\n5. End with the 'СЕЙЧАС' line so the person knows the single next action."
)
```

### 3. After Completion

The coach returns the anchor, frame, and single next step. Pass it through as-is — do not expand
it into a full plan or start executing the work yourself.

> **СЕЙЧАС**: <одно конкретное действие>.
>
> Сделай шаг и скажи **'готово'** — открою следующий. Или скажи, если рамка не та.
