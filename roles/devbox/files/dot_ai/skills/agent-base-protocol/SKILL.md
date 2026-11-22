---
name: agent-base-protocol
description: >
  Shared foundational protocol for all agents. Covers file operations, language standard,
  and clarification rules. Referenced by all agent definitions to avoid duplication.
alwaysApply: false
problem: "Every agent would otherwise re-inline the same file-ops, language, and clarification rules, drifting apart over time."
related: [project-preferences, shared-utils, writing-for-the-reader, response-templates]
---

# Agent Base Protocol

Foundational rules shared by all agents. Agents reference this skill instead of inlining these sections. The User Authority Protocol (the shared core deployed as each engine's global instructions) is the source for questions, decisions, reporting, and language; this skill only adds what agents need on top of it.

## File Operations

Create new files with the **Write** tool and edit existing ones with the **Edit** tool; keep Bash for commands (build tools, test runners, linters, formatters).

These forms are forbidden. The hooks refuse them, so a retry in another spelling costs a turn and changes nothing; use the replacement on the first attempt.

| # | Forbidden | Refused by | Use instead |
|---|---|---|---|
| 1 | A heredoc or here-string: any `<<` in the command text, quoted or not | `bash_decision_gate.py` | Write to create a file, Edit to change one; pass input as a file argument |
| 2 | Inline code to an interpreter: a command whose first word is `python`, `python3`, `node`, `ruby` or `perl` with `-c`, `-e`, `-m`, `--command…` or `--exec…` (bare `python -m pytest` included); a command starting with `eval`, `exec`, `source` or `.`. Also `uv run python -c "import …"` in a Python project. Other `uv run python -c` code is not refused by a hook but is forbidden all the same | `bash_decision_gate.py` (first word only); `pre_bash_toolchain_guard.py` for `uv run python -c` with an import | Write the script to `.claude/claude_written_scripts/<unique-name>.<ext>` (the directory the deny message names) and run it by path with the project prefix (`uv run python <path>`); run modules through the prefix: `uv run python -m <module>` is the allowed form; read JSON with `jq` |
| 3 | `bash -c`, `sh -c`, `zsh -c` or `fish -c` (also through `xargs`) whose body does not parse or contains a form from this table | `bash_decision_gate.py` | Run the commands directly, or as a script file (row 2) |
| 4 | Deleting, moving or overwriting anything under `.claude/claude_written_scripts/` (`rm`, `mv`, `cp`, `tee`, `sed -i`, `find -delete`, `>`, `>>`) | `bash_decision_gate.py` | Leave earlier scripts in place; write a new one under a new name |
| 5 | `rm` with recursive and force flags on a path outside `$TMPDIR`, `/tmp`, the repository's `tmp/` or a cache or build directory (`node_modules`, `.venv`, `dist`, `build`, `__pycache__`, …) | `bash_decision_gate.py` | Keep scratch under `$TMPDIR` and leave it there |
| 6 | A write outside the working directory, the session's allowed directories, `$TMPDIR` and `/tmp`: a redirection, a write command (`rm`, `mv`, `cp`, `tee`, `mkdir`, `touch`, …) or `sed -i` | `bash_decision_gate.py` | Edit for changes to files; scratch under `$TMPDIR` |
| 7 | A lint-suppression token anywhere in a Bash command whose text also contains `sed`, `echo`, `printf`, `cat`, `tee`, `perl`, `python`, `ruby` or `awk`. Both are substring tests: a read-only grep is refused, and `cat` matches inside `location` | `bash_decision_gate.py` | A character class in the pattern: `no[q]a`, `type: *[i]gnore`, `no[l]int`, `eslint-[d]isable` |
| 8 | A Write, or an Edit whose new text adds what its old text lacked, containing a suppression comment in its literal form, marker included (Python noqa, type-ignore and pyrefly-ignore comments, Go nolint, TypeScript ts-ignore, ts-expect-error and eslint disable, Java SuppressWarnings; case-insensitive), in any file type, Markdown handoffs included | `pre_edit_lint_guard.py` | Fix the lint. In prose, name the directive without its comment marker, as this row does |
| 9 | Write onto an existing non-empty file | `pre_write_existing_guard.py` | Edit; for a scratch file you rewrite whole, a new file name |
| 10 | `cd` to the directory the shell is already in | `bash_decision_gate.py` | Drop the `cd`; use absolute paths or `git -C` |

The gate also refuses destructive git and SQL forms; agents do not run those.

Change files with Edit or Write only; `sed`, `awk` and `perl` serve reads (`sed -n '10,20p'`), never in-place edits.

An exit code that goes into a report comes from the command run alone, never after a pipe: run the command by itself and read the exit code the tool reports; in POSIX shells, `cmd; echo "exit=$?"`. Shell-specific pipe-status variables are not portable across the shells the tool may run.

## Language Standard

The core's language invariant applies: match the user's language in conversation, and write every persisted artefact in British English. The `project-preferences` skill holds the word list. If the Cyrillic guard hook warns about a written file, correct it on the next edit.

## Repository Boundary

Read any repository the task needs a fact from. Write only inside the session's repository or a directory the user added to the session. A change you believe belongs in a neighbouring repository goes into your report as a finding — the file and the proposed change — never into that repository: the main session holds the user's authority for it (core §7).

## Claims Come From Reading

What code, a setting or a test does is established by reading its body, its definition or its observed output, never by its name, signature or docstring; a link, note or quotation is established by the passage read inside it (core §8). An unread premise is reported as unverified, with what stopped you reading it — not presented as a decision.

## When to Ask for Clarification

Follow core §1: derive first, through the ladder in its step 2 — the repository and the conversation (the user's earlier answers, analogies they invoked, principles they stated), the other items of the same task, primary documentation and a web search for public facts, then a cheap reversible check — and ask only what passes the core's stop list: the answer cannot be derived, only the user can supply it, and a wrong guess would be costly to undo or would make the work useless. Design and implementation choices inside the user's direction are yours (core §0): decide them and report them. When the user describes a problem rather than requesting a change, the deliverable is an assessment: investigate as far as the evidence allows, with rival explanations, and stop before changing anything — a menu of "how should I fix this?" questions is already a fix step.

### Decide yourself (routine — Tier 1)

These have deterministic answers; apply the rule and proceed:
- Removing a comment that violates the comment policy
- Formatting a file
- Adding error context
- Continuing routine work

### Decide and state it in one line (standard — Tier 2)

Naming when the domain is clear, structure when approaches are close, scope when one reading is clearly more defensible. Pick a defensible default and mention it in one line of the report, so the user can overturn it cheaply.

### Show candidates (decision — Tier 3)

When the core §2 threshold holds — the user asked for options, or the candidates differ in what the user gets and the conversation does not settle the choice — present 3–7 candidates as the decision card (template T2 in the `response-templates` skill), leading with your recommendation. The topic of a choice (API, interface, architecture) and the number of files it touches are not triggers. Below the threshold, consider the candidates in your own reasoning (core §1 step 3), pick, and report the pick with its reason in a line.

### How to ask

Put each question in the message with its context: what you are working on, what the reader will actually see or get under each option, and your recommended answer with its reason, which the user can accept in one word; work that depends on it waits for the answer. The `writing-for-the-reader` skill has the question template. Ask one batched round per topic, so the user answers once; after they answer, derive the follow-ups from their answers instead of asking again.

A question tool (such as `AskUserQuestion`) only collects the pick; it cannot carry the context, so the context stays in the message text.

### Subagents and orchestrators

A subagent cannot reach the user. It decides what is its to decide, records each decision with its reason, and returns as open only the items that pass the stop list, each with a recommended answer. The orchestrator treats those items as input, not as a list to forward: it resolves each from the conversation and evidence it holds, and relays only the residue that still passes the stop list, with its recommendation (core §6). The reason: the orchestrator holds the user's context the subagent lacks, and a forwarded list hands the user work the orchestrator could do.
