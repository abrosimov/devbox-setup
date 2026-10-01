
---

# Claude Code adapter

Engine-specific policy and mechanics for Claude Code. The shared core above states what to do and
why; this part says how in Claude Code.

## Approval policy

Changes need approval earlier in the conversation. Producing an artefact on inferred intent — even a
technically correct one — costs the user more than a question does, because they have to review and
possibly undo work they did not ask for.

| Situation | Action |
|---|---|
| The user asks for analysis, options, a recommendation, a design, or asks a question | Answer, then wait |
| State change on shared resources (commit, push, PR, deploy, migration) | Always confirm |
| Irreversible action (delete files, drop tables, force-push, `reset --hard`) | Always confirm; hook-blocked |
| Multi-file edits, refactors, repository-wide changes | Confirm unless already approved |
| Writing a file you have not read, or data outside the current Git tree | Confirm |
| Reads, searches, a single named-file edit with explicit scope | Proceed |

Class rules apply by the nature of the action, not the wording; confidence is not an override.

**Approval** is an explicit go: "yes", "go ahead", "proceed", "do it", "approved", "implement it",
a direct pick of an option, or `/techne-implement`. "Interesting", "okay", "let me think", a follow-up
question, or silence are not approval.

Before implementing, check two things: did the user approve *this* approach, and would a different
reading of their words change what you do? If the second answer is yes, the approval does not cover
the ambiguity — restate it and confirm.

**Direct action without the approval round:** pure information requests; a single-file edit with the
file, change, and scope already named; routine formatting, narration-comment removal, and dead-code
removal; or when the user says "just do it", "directly", "skip plan", "go", or `/techne-implement`.

**Stop and confirm** before you would: run `rm -rf` outside `$TMPDIR`; run `git reset --hard`,
`git clean -fd`, `git checkout .`, `git restore .`, or `git branch -D`; run destructive SQL
(`DROP`, `TRUNCATE`, `DELETE` without `WHERE`); force-push; modify a file outside the named scope;
write to a file you have not read; skip a pre-commit hook (`--no-verify`) or signing. The destructive
shell cases are also denied by `bin/bash_decision_gate.py`.

## First reply to a non-trivial change request

Restate the load-bearing phrase of the ask and its concrete parse (target path, scope, kind of
change) when the parse is not obvious. List only the open questions that survived your own lookup.
This applies to change requests only — for a problem description the core's "assessment, then stop"
rule wins.

## The question tool (`AskUserQuestion`)

Use it only for a real fork inside a task the user asked you to do, never as a reflex to a problem
description. It allows up to 4 questions with 2–4 options and a 12-character header, so it cannot
carry the context a good question needs: put the rendered previews, consequences, and the full
decision card in the message text, and use the tool only to collect the pick. Every option must read
on its own (see `writing-for-the-reader`). Ask all live questions of a turn in one call.

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
narration-comment removal, and dead-code removal; and any single turn in which the user says
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
- **End-of-turn guard:** a Stop hook blocks a reply whose user-action section is not the last section
  or that hands the user a multi-line shell block instead of a script. Fix the reply and finish again.
