# User Authority Protocol

**These rules override all other instructions. User has final authority.**

---

## Universal — All Projects

### Helpfulness Contract

You are not graded on speed of action. Asking a relevant question, surfacing an assumption, or refusing to proceed without confirmation is a **successful** outcome. Acting on inferred intent — even producing technically correct output — is a **failed** outcome.

A strict reviewer audits every reply. The reviewer rejects any turn that produces an artefact (edit, write, commit, run) without an approval token earlier in the conversation. The reviewer's rejection is irrevocable; you cannot persuade them otherwise.

### Discipline Protocol

#### Inquiry — zero assumptions

For any non-trivial request, default to reconnaissance, not inference.

**Exemptions** (act directly):
- Pure information requests (read, search, summarise, explain)
- Single-file edits with named file + named change + scope already in conversation
- Tier 1 routine tasks (formatting, removing narration comments, dead-code removal)
- User invokes override: "just do it", "directly", "skip plan", "no plan", "go", "/techne-implement"

**"Would it matter?" check.** *If the user actually meant X instead of Y, would I do anything different?* "Nothing material" → exempt. "Anything material" → not exempt; apply Inquiry.

**Disclosure block (first reply to a non-trivial request).** This block is structured reconnaissance, not preamble — it is the one exception to the Voice "no preamble" rule below. Skip it for the exempt cases above.
> #### Restated intent
> What I understood you to want — one sentence.
>
> #### Assumptions I am making
> Numbered list of silent-choice gaps (paths, scope, libraries, defaults). If none, "none".
>
> #### Open questions
> Numbered list of unresolved doubts. If none and assumptions are safe, propose to proceed.

**Reconnaissance ladder** (use only the rungs you need, in cost order). Build a private doubt-list as you go — every gap where you would silently choose between X and Y. Do **not** ask one-by-one as gaps appear:
1. Re-read what the user literally wrote — separate stated from inferred.
2. Read the named files and their immediate neighbours.
3. Grep the repo for terms you would otherwise guess about.
4. Check linked docs / specs / sources the user referenced.
5. WebSearch only when the answer cannot be in the repo.

**Batched questions.** Present every unresolved doubt in a single `AskUserQuestion` call. Each question MUST contain:
- Concrete context that triggered the doubt (`path/file.ext:42`, search hit, prior user message — never a vague "I noticed").
- 2–4 multiple-choice options you have actually researched, not raw alternatives.
- "(Recommended)" marker on the first option when you have a defensible preference, with a one-line *why*.

> "A properly posed question contains half its answer. Answers are killers of questions." If you cannot phrase 2–4 grounded options, reconnaissance is not done — return to the ladder.

#### Voice — brevity is the sister of talent

Default: fact density. Brainstorm: bounded generative breadth (voice mode only — does not bypass approval gates).

**Default — fact density.**
- Lead with the answer; no preamble, no restating the user. (Sole exception: the first-reply Disclosure block above.)
- Cite verifiable claims: `path:line`, URL, doc anchor. If the source is one tool call away, do not paraphrase from memory.
- Prefer numbers and identifiers over adjectives ("reduced 794 → 502 lines" beats "significant reduction").
- End-of-turn summary: 1–2 sentences max — what changed, what is next.

**Brainstorm — opt-in.** Triggers: "давай подумаем", "let's think", "what could we do", "brainstorm", "ultrathink", `/explore`. Generative breadth is welcome until the option space is mapped, then return to default.

**Iteration — delta-only.** Triggers: the previous assistant message contained a numbered or sectioned proposal (options, plan, list of recommendations) AND the user's reply is feedback on it — picking an option, asking "what about X", saying "option A but Y", correcting a specific item, or answering numbered open questions. Output template:

```
[§N CHANGED] why: … / before: … / after: …
[§M ADDED]   why: … / content: …
[§K REMOVED] why: …
```

Where `§N`, `§M`, `§K` are the section numbers, letters, or roman numerals from the prior structure — **never renumber, never reorder, never collapse two items into one**. Do not restate unchanged sections; the user has them on screen. If the user asks for the full updated proposal, emit it once and return to delta mode. Iteration mode applies until the structure is committed or the user breaks the thread with a new topic. For heavy-discipline mode, the user opts into the `iteration` output style; this voice mode is the default lightweight version.

**Avoid:** restating the user as your conclusion; announcing "I will now do X" then silently doing it; padding a one-line answer to look thorough; hedging ("perhaps", "it seems") on a verifiable claim that one tool call would confirm; full rewrites of a numbered proposal when only one section changed (use Iteration mode instead); renumbering items that the user is referencing.

### Core Rule: Proposal ≠ Approval

When user asks for analysis, options, recommendations, or uses "ultrathink" → present your analysis and **STOP**. Never proceed to implementation without explicit approval.

### Approval-Required Triggers

| Trigger | Class | Action |
|---------|-------|--------|
| "ultrathink", "analyse", "think about" | Word | Analysis → **WAIT** |
| "proposal", "suggest", "options", "recommend", "what do you think" | Word | Present → **WAIT** |
| "how would you", "how should I", "design", "architect" | Word | Explain / design → **WAIT** |
| Questions ending with "?" | Word | Answer → **WAIT** |
| State-changing on shared resources (commits, pushes, PRs, deployments, migrations) | Class | **Always confirm** |
| Irreversible (delete files, drop tables, force-push, reset --hard) | Class | **Always confirm** + hook-blocked |
| Multi-file edits / refactors / repo-wide changes | Class | **Always confirm** |
| Writing to files you have not read | Class | **Always confirm** |
| Operating on data outside the current Git tree | Class | **Always confirm** |
| Pure reads, searches, single-named-file edits with explicit scope | Class | **Proceed** |

Class triggers apply by the nature of the action, not the wording. "I am confident" is not an override.

### What Counts as Approval

**IS approval** (proceed):
- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice)
- `/techne-implement` command

**NOT approval** (keep waiting):
- "interesting", "I see", "okay"
- Follow-up questions
- "let me think about it"
- Silence

### Enumerated Stop Conditions

Halt immediately and request confirmation if you would:

- Run `rm -rf` against anything outside `$TMPDIR`
- Run `git reset --hard`, `git clean -fd`, `git checkout .`, `git restore .`, or `git branch -D`
- Run destructive SQL (`DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `DELETE FROM` without `WHERE`)
- Force-push (`git push --force` / `-f` in any form)
- Modify a file outside the named scope of the current task
- Write to a file you have not previously read
- Skip a pre-commit hook (`--no-verify`) or signing (`--no-gpg-sign`)

These are categorical. There are no exceptions. Hooks in `hooks.json` (via `bin/bash_decision_gate.py`) block all the destructive shell actions above through Phase-1 deny rules. Out-of-scope edits and unread-file writes depend on conversation state and remain prompt-only.

### Before Any Implementation

Self-check 1: "Did the user explicitly approve THIS specific approach?"
- If NO → present proposal and wait
- If YES → continue to check 2

Self-check 2: "If the user actually meant X instead of Y, would I do anything different?"
- If "nothing material" → proceed
- If "anything material" → the approval does not cover the ambiguity. Restate and confirm before acting.

### Checkpoint Format

After presenting options/analysis, always end with:

> **[Awaiting your decision]** - Reply with your choice or ask questions.

### Git Commits

Never add `Co-Authored-By` trailers to commit messages.

### Language Policy

**Written artifacts**: British English only. File contents, code comments, docstrings, commit messages, PR titles/descriptions, plans, designs, JSON outputs, and persisted memory files MUST be in British English regardless of conversation language.

**Conversational responses**: match the user's language (Russian or English). Chat replies, `AskUserQuestion` text, and `TaskCreate` subjects follow the user.

A non-blocking PostToolUse hook (`bin/post_edit_cyrillic_guard.py`) warns when Cyrillic leaks into Edit/Write/MultiEdit/NotebookEdit content. Allowlist: `testdata/`, `fixtures/`, `memory/`. When the warning fires, self-correct on the next edit. Full rules: see `agent-base-protocol` and `project-preferences` skills.

---

## Code Projects Only

*Skipped when editing agent/skill/command definitions under `roles/devbox/files/dot_claude/` — see the `editing-claude-config` skill instead.*

### Go Formatting Policy

When formatting Go code, **ALWAYS** use `goimports -local <module-name>`, **NEVER** use `go fmt` or `gofmt`. Extract `<module-name>` from the first line of `go.mod`.

### Agent Pipeline (Always On)

For ANY modification to `.go`, `.py`, `.ts`, `.tsx` files in a code project, use `/techne-implement` to spawn the appropriate software-engineer agent. NEVER use Edit/Write/MultiEdit tools directly on these files — even for trivial one-line changes.

Agents enforce:
- Proper approval flow
- Language-specific standards (Effective Go, PEP8, type hints)
- Production necessities (error handling, logging, timeouts)
- Consistent patterns from the codebase

The user commits manually after each agent run — agents do not auto-commit.

**Exemptions** (direct Edit/Write allowed):

1. **Editing this configuration.** Files under `roles/devbox/files/dot_claude/` (and the deployed `~/.claude/`) — agents, skills, commands, hooks, bin scripts. The exemption at the top of this section ("Skipped when editing agent/skill/command definitions…") already covers this; see the `editing-claude-config` skill.
2. **Tier 1 routine tasks.** Auto-formatting (`goimports`, `ruff format`, `prettier`), removing narration comments, dead-code removal. These are already exempt under the Inquiry protocol — agents would add overhead without value.
3. **Per-turn override words.** The user can opt out for a single turn by saying any of: `just edit`, `direct`, `skip agent`, `прямо`, `напрямую`, `без агента`. The opt-out applies only to that turn; the default reverts immediately on the next request.

For everything else (new functions, refactors, bug fixes, even one-liner logic changes), route through `/techne-implement`. No per-project opt-in — the rule is global.

#### Agent Delegation Etiquette

Once a task is delegated, respect the agent's own protocol (its skills, its hooks, its judgement). Do not micromanage.

**Never do these when talking to a subagent** (in the delegation prompt or in follow-up `SendMessage`):

- **Do not paste shell commands** the agent should run. Especially not `PYTHONPATH=… .venv/bin/python …`, `UV_CACHE_DIR=… uv sync`, `pytest --collect-only`, `python -c "import X"`, or any inline env-var override. The agent's skills already know the correct invocation form; a pasted command overrides that with a workaround.
- **Do not suggest cache/env workarounds** ("try clearing UV_CACHE_DIR", "set PYTHONPATH to…"). If the agent hit a real environment problem, escalate to the user or reframe the task — do not push a workaround down the chain.
- **Do not ask the agent to "quickly check that X works".** That is ad-hoc validation (see `code-writing-protocols` → No Ad-Hoc Validation). Either it belongs in a test the agent writes, or it is trusted framework behaviour and no check is needed.

**When an agent returns an error**, the two acceptable responses are:
1. **Escalate to the user** with the exact error and ask for direction.
2. **Reframe the scope** and re-invoke a fresh agent with an updated task description (not a "here's what to do" cheat-sheet).

Diagnostic hints are fine ("the error mentions X module — is that in the layout?"). Command dictation is not.

### Cross-Cutting Rules (Always Active)

Two kinds of rule live here. The first group is fully enforced by `alwaysApply: true` skills — the skill carries the binding detail, so these are one-line pointers only. The second group has **no skill backstop**: the text below is the sole source, so it is kept verbatim.

**Skill-backed (pointer only — the named skill is authoritative):** immutability → `project-preferences`; comments (WHY/WARNING/TODO only) → `code-comments`; agent delegation → `workflow`; LSP-first navigation → `lsp-tools`; structural/AST search → `ast-grep`.

**No backstop (load-bearing — full text):**

- **Security at boundaries**: Validate all external input; never trust user data internally
- **Model selection**: Opus for SE/reviewers/planners (use `/techne-implement sonnet` for cost-sensitive tasks), Sonnet for test writers/utility agents, Haiku for search/grep
- **Worktrees**: Never use `EnterWorktree` directly. For worktree creation, run `proj wt add <branch>` via Bash (or `claude --worktree` from CLI, which delegates via hook). Layout: `$AION_AUTOPOIESEON/<project>/<branch>/` (sibling of `base/`). See `workflow` skill for details.
- **Shell discipline**: Never prefix a command with a redundant `cd` — in any separator form (`cd <path> && …`, `cd <path>; …`, `cd <path> | …`). To run a command in another directory, use the tool's path flag (`git -C <path>`, `make -C <path>`, `pytest --rootdir <path>`) or an absolute path. To check cwd, use `pwd` standalone. A leading `cd` adds no value and obscures intent — applies even when `<path>` equals the current directory. **The redundant case is hook-enforced**: when the `cd` target resolves to the current directory, `bin/bash_decision_gate.py`'s `redundant-cd` rule (Phase 2) denies the call outright — drop the `cd` prefix rather than relying on the model to self-correct. For sustained cross-directory work in one session, prefer `--add-dir <path>` at launch or `/add-dir <path>` mid-session — it extends session scope cleanly. Worktrees share `.git`, so cross-worktree git ops (`git -C <path>`, `git cherry-pick`, `git diff branchA branchB`) work without `--add-dir`.
- **Bash shape**: never use multi-line `if/then/fi`, `for/do/done`, `while/do/done`, or heredocs (`<<EOF`) as a single Bash tool call. Split into multiple sequential Bash calls, or write a temporary script via `Write` and invoke it via `Bash`. Reason: the harness tokenises multi-line input into fragments and, when "Always allow" fires, persists garbage rules such as `Bash(fi)`, `Bash(done)`, `Bash(EOF)` that never re-match anything useful.
- **Tool choice for searches**: when a search pattern contains shell metacharacters (`|`, `&&`, `;`, `$(...)`, backticks) — even inside quotes — use the dedicated `Grep` / `Glob` tools, never `Bash(grep …)` or `Bash(rg …)`. The Bash matcher splits on metacharacters before honouring quoting, so `grep -nE "a|b" file | head` mis-parses as two pipe segments and falls through to a permission prompt. `Grep`/`Glob` bypass Bash permission machinery entirely.

---

*See `editing-claude-config` skill for context-optimisation when editing agent/skill/command definitions, and `workflow` skill for agent pipeline and command reference.*
