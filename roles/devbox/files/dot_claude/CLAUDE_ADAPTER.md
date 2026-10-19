---

# Claude Code adapter

Engine-specific policy and mechanics for Claude Code. The shared core above states what to do and
why; this part says how in Claude Code.

## Approval policy

Two classes of action need an explicit go from the user. Everything else proceeds under the core's
§1 once the parse is settled: reads, searches, edits inside the named scope, and the project's own
checks need no approval round, however many files they touch. The classes apply by the nature of
the action, not the wording; confidence is not an override.

| Class | Examples | Action |
|---|---|---|
| Externally visible or shared state | commit, push, PR, deploy, migration, sending messages, writing data outside the current Git tree and outside the directories the user added to the session | Always confirm |
| Irreversible or destructive | `rm -rf` outside `$TMPDIR`; `git reset --hard`, `git clean -fd`, `git checkout .`, `git restore .`, `git branch -D`; force-push; `DROP`, `TRUNCATE`, `DELETE` without `WHERE`; skipping a pre-commit hook (`--no-verify`) or signing; writing a file you have not read | Always confirm; the shell cases are also denied by `bin/bash_decision_gate.py` |

**What counts as a go** for these two classes: "yes", "go ahead", "proceed", "do it", "approved",
"implement it", a direct pick of an option, or `/techne-implement`. For reversible local work, "ok",
"okay", "давай" and the like in reply to your stated plan are agreement. "Interesting", "let me
think", a follow-up question, or silence are not.

## The question tool (`AskUserQuestion`)

Use it only for a question that passed the core's §1 stop list, never as a reflex to a problem
description or to a subagent's open questions. It allows up to 4 questions with 2–4 options and a
12-character header, so put the context and rendered previews in the message text and use the tool
only to collect the pick. Put your recommended option first, marked "(Recommended)"; every option
must read on its own (see `writing-for-the-reader`). One call per topic carries every live question.

## Background agents

Subagents run in the background by default, and each one's completion arrives as a separate
notification in a later turn. Apply the core's "one answer, after all of them" rule to those
notifications: while agents from the same batch are still running, reply with the single status line
and nothing else. Launch independent agents in one message so they run concurrently.

## Code changes go through agents

For any modification to `.go`, `.py`, `.ts`, `.tsx` files in a code project, use `/techne-implement`
to spawn the matching software-engineer agent rather than editing directly — the agents carry the
language standards, production necessities, and the project's patterns. The user commits manually;
agents do not commit.

Direct edits are fine for: files under `roles/devbox/files/dot_claude/`, `dot_ai/`, `dot_codex/`,
`dot_agy/` and the deployed `~/.claude/` (see the `editing-claude-config` skill); routine formatting,
narration-comment removal, and dead-code removal in files the task already changes; and any single turn in which the user says
`just edit`, `direct`, `skip agent`, or the Russian equivalents («прямо», «напрямую», «без агента»).

When delegating, respect the agent's own protocol. Give it the outcome, scope, and constraints, not a
command transcript: do not paste shell commands or environment workarounds (`PYTHONPATH=…`,
`UV_CACHE_DIR=…`), and do not ask it to "quickly check that X works" — that belongs in a test. If an
agent returns an error, either escalate the exact error to the user or re-invoke a fresh agent with a
reframed task. Diagnostic hints are fine; command dictation is not.

## Claude Code mechanics

- **Skill pointers:** immutability → `project-preferences`; comments → `code-comments`; agent
  routing → `workflow`; semantic navigation → `lsp-tools`; structural search → `ast-grep`.
- **Model selection:** Opus for engineers, reviewers, and planners (`/techne-implement sonnet` when
  cost matters), Sonnet for test writers and utility agents, Haiku for search.
- **Worktrees:** never call `EnterWorktree`; run `proj wt add <branch>` (layout
  `$AION_AUTOPOIESEON/<project>/<branch>/`). See the `workflow` skill.
- **No redundant `cd`.** Use the tool's path flag (`git -C`, `make -C`) or an absolute path; the
  `redundant-cd` rule in `bin/bash_decision_gate.py` denies a `cd` to the current directory.
- **Bash tool call shape:** no multi-line `if`/`for`/`while` blocks or heredocs in one call — split
  the calls or write a temporary script. The harness otherwise persists fragment rules such as
  `Bash(fi)`.
- **Searches with shell metacharacters** (`|`, `&&`, `;`, `$(…)`) go through the `Grep`/`Glob` tools,
  because the Bash permission matcher splits on them.
- **Cyrillic guard:** `bin/post_edit_cyrillic_guard.py` warns when Cyrillic reaches a written file
  outside `testdata/`, `fixtures/`, `memory/`; correct it on the next edit.
- **End-of-turn guard:** a Stop hook blocks a reply whose "What I need from you" section is not the
  last section or that hands the user a multi-line shell block instead of a script; fix the reply
  and finish again. The section itself is optional and belongs only to a turn blocked on the user.

## Reminder

Deliver exactly what was asked, at the scope intended. Decide what is yours to decide and say so in
a line; ask only what passes the core's stop list, once, with a recommendation. A decision the user
has made stays made.
