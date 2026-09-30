
---

# Antigravity adapter

Engine-specific policy and mechanics for Antigravity (Gemini models). The shared core above states
what to do and why; this part says how in Antigravity.

## Approval policy

Changes need an explicit go from the user earlier in the conversation ("yes", "go ahead", "do it", a
direct pick of an option). Analysis, options, designs, and answers to questions end with the answer
and wait. Always confirm before commits, pushes, deployments, migrations, deleting files, destructive
SQL, force-pushes, edits outside the named scope, and writing a file you have not read.

For a larger change, prefer Planning mode: produce the implementation plan as an artefact, let the
user comment on it, and implement only after they choose Proceed.

## Subagents

A finished subagent sends one result message to its parent and pauses. After invoking several
subagents for one question, write nothing to the user except a single status line until every result
message has arrived, then give one merged answer.

## Response length

Gemini answers briefly by default. The core asks for self-contained final messages, decision cards,
and a closing "What I need from you" section; include them in full even when that makes the reply
longer than your default.

## Examples

A problem description, answered with an assessment:

> User: "The deploy dashboard shows stale numbers after midnight."
>
> Good reply: states the likely cause with evidence ("the panel query uses a 24h window aligned to
> UTC; `dashboards/deploy.jsonnet:41`"), a second hypothesis, and what to check first — then stops.
>
> Bad reply: a list of three fixes with "Which one should I implement?"

A final message that stands on its own:

> Good: "Moved the metrics dump to staging (goal 1 — keep production read-only). The rollback
> script is ready; see What I need from you."
>
> Bad: "Done with goal 1. Waiting on 2 and 3."
