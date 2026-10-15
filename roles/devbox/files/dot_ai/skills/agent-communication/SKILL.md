---
name: agent-communication
description: >
  Shared patterns for agent handoffs, escalation rules, completion formats, and user
  interaction. Use when agents need to communicate with each other or with users.
problem: "Agent handoffs, escalation, and completion formats fragment without a shared inter-agent contract."
related: [config, structured-output]
---

# Agent Communication Patterns

Standardised patterns for agent-to-agent handoffs, user communication, and escalation.

## Handoff Protocol

Every agent must define its position in the pipeline:

```markdown
**Receives from**: <upstream agent or "User"> (`document.md`)
**Produces for**: <downstream agent or "User">
**Deliverables**:
  - `document.md` — primary (human-readable reasoning and rationale)
**Completion criteria**: <what must be true before handoff>
```

SE agents optionally emit `se_{lang}_output.json` / `se_frontend_output.json` alongside the source code — read by the Test Writer and Code Reviewer (see `structured-output` skill).

### Common Sequences

Each agent runs one-shot via its `/techne-*` command. The user drives the order by choosing what to invoke next. Typical sequences:

| Sequence | Flow |
|----------|------|
| Backend feature | TPM → Domain Expert → Planner → API Designer → SE-backend → Test Writer → Reviewer |
| UI feature | TPM → Domain Expert → Designer → Planner → API Designer → SE-frontend → Test Writer → Reviewer |
| Fullstack feature | TPM → Domain Expert → Planner → API Designer → Designer → [SE-backend, SE-frontend] → Test Writer → Reviewer |
| API design only | User → API Designer → SE |
| UI design only | User → Designer → SE-frontend |
| Quick fix (backend) | User → SE-backend → Test Writer → Reviewer |
| Quick fix (frontend) | User → SE-frontend → Test Writer → Reviewer |
| Quick fix (fullstack) | User → [SE-backend, SE-frontend] → Test Writer → Reviewer |
| Test only | User → Test Writer → Reviewer |
| Review only | User → Reviewer |
| Build (3-gate) | User → Builder → G1 → Meta-Reviewer → G2 → Content Reviewer → G3 |
| Audit (full) | User → [Freshness Auditor + Consistency Checker] → merged report |
| Audit (fix) | User → [Freshness Auditor + Consistency Checker] → Builder(s) per artifact |

### Artifact Registry (Single Source of Truth)

Every file in the pipeline is listed here. Agents reference this table in their Step 1 to know what to read.

All paths are relative to `{PROJECT_DIR}` (see `config` skill: `{PLANS_DIR}/{JIRA_ISSUE}/{BRANCH_NAME}/`).

| Agent | Reads | Writes |
|-------|-------|--------|
| **TPM** | *(user input)* | `spec.md`, `research.md`, `decisions.md` |
| **Domain Expert** | `spec.md` | `domain_analysis.md` |
| **Domain Modeller** | `domain_analysis.md`, `spec.md` | `domain_model.md` |
| **Designer** | `spec.md`, `domain_analysis.md`, `plan.md`?, `api_design.md`? | `design.md`, `design_system.tokens.json` |
| **Impl Planner** | `spec.md`, `domain_analysis.md`, `domain_model.md` | `plan.md` |
| **Database Designer** | `plan.md`, `spec.md`, `domain_analysis.md`, `domain_model.md` | `schema_design.md`, `migrations/` |
| **API Designer** | `plan.md`, `spec.md`, `domain_analysis.md`, `domain_model.md` | `api_design.md`, `api_spec.yaml` |
| **SE (backend)** | `plan.md`, `api_spec.yaml`, `schema_design.md`, `domain_model.md`? | *(source code)*, `se_{lang}_output.json` |
| **SE (frontend)** | `plan.md`, `design.md`, `api_spec.yaml`, `domain_model.md`? | *(source code)*, `se_frontend_output.json` |
| **Observability** | `plan.md` | *(dashboards, alerts)* |
| **Test Writer** | `plan.md`, `spec.md`, `domain_model.md`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(test files)* |
| **Code Reviewer** | `plan.md`, `spec.md`, `domain_model.md`?, `design.md`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(review report — inline)* |
| **Content Reviewer** | agent/skill artifact, 2-3 referenced skills | `<audit-findings>` XML (inline) |
| **Freshness Auditor** | all `agents/*.md`, all `skills/*/SKILL.md` | `<audit-findings scope="library">` XML (inline) |
| **Consistency Checker** | all `agents/*.md`, all `skills/*/SKILL.md`, all `commands/*.md` | `<audit-findings scope="library">` XML (inline) |
| **DSS (via /techne-options)** | `spec.md`, `domain_analysis.md`, `plan.md`?, `design.md`? | `dss_output.json` |
| **Architect** | `spec.md`, `domain_analysis.md`, `plan.md`? | *(architecture analysis — inline)* |
| **TDD Guide** | *(user query)* | *(TDD guidance — inline)* |
| **Build Resolver (Go)** | *(build error logs)* | *(code fixes — direct edits)* |
| **Doc Updater** | *(code changes)* | *(documentation file updates)* |
| **Database Reviewer** | `schema_design.md`, `migrations/` | *(review feedback — inline)* |
| **Refactor Cleaner** | *(source code)* | *(refactored code — direct edits)* |

`?` = optional, read if available.

**Rule**: When an agent's Step 1 lists files to check, it MUST match this table. If you add a new agent or artifact, update this table first.

**Fallback**: Optional `se_*_output.json` reads are best-effort — never fail because one is missing (see `structured-output` skill — Graceful Degradation Rule).

---

## Completion Output Format

An agent's completion message is a result for whoever launched it, not a conversation with the user.

- **Subagent (launched by an orchestrator):** report the result to the orchestrator — outcome first, then the evidence (files changed, checks run, open issues), then the decisions it took with their reasons, then only the open items that pass the core's stop list, each with a recommended answer. The orchestrator resolves those items itself where its context allows and relays only the residue (core §6), so a subagent's list is never forwarded verbatim. No prompt to the user such as "say 'continue'": the orchestrator waits until every agent it launched has returned and then gives the user one consolidated answer (core §6), so a per-agent hand-off would fragment that answer.
- **Single-agent command run** (one `/techne-*` command, one agent): the final report follows template T1 in the `response-templates` skill and may end with one line naming the next command, because here the user does drive the order.

```markdown
Implementation complete: 3 files changed in `internal/orders/` (validation of empty orders), `make test` passes.

Next: `/techne-test` to write tests for the new validation path.
```

Typical next commands: SE → `/techne-test`; Test Writer → `/techne-review`; API Designer → `/techne-implement` for backend and frontend (both read the contract); Designer → `/techne-implement` for `software-engineer-frontend`; Code Reviewer with blocking issues → `/techne-implement`, then `/techne-review` again; Code Reviewer with no blocking issues → ready to commit (the user commits).

---

## Escalation Rules

### Model Downgrade Notice (Opus → Sonnet)

SE agents default to opus. When the `/techne-implement` command auto-downgrades to sonnet for a simple task, it shows:

```markdown
Task looks straightforward (N files, ~M lines). Using Sonnet for speed. Say 'opus' to override.
```

Code reviewers and implementation planners always use opus — no downgrade logic applies.

### User Escalation

Escalate only what passes the core's §1 stop list — the answer cannot be derived from the repository, the docs, or the conversation (earlier answers, analogies, stated principles); only the user can supply it; and a wrong guess would be costly to undo or would make the work useless. Typical survivors:

1. **Goal or scope** — the work would cross the named scope, or two readings of the goal remain after derivation and building the wrong one would waste the work
2. **A value choice with no signal** — the candidates differ in what the user gets and nothing in the conversation points to one
3. **A fact only the user holds** — credentials, an external constraint, access
4. **An approval-class action** — destructive, irreversible, or externally visible

Everything else — design and implementation choices inside the user's direction — is decided and stated in one line of the report.

### How to Ask Questions

The rules live in `agent-base-protocol` (§How to ask); the question template and bad/good examples are in the `writing-for-the-reader` skill, and the decision card is template T2 in `response-templates`. In short: every question carries its context, the rendered outcome of each option, and your recommended answer as the default; one batched round per topic; and a subagent returns its residue to the orchestrator, which resolves what it can before relaying.

## Approval Validation

Before implementation, agents verify that explicit approval exists. What counts as approval is engine policy and lives in the engine adapter (for Claude Code, the Approval policy section of the deployed `CLAUDE.md`); this skill does not restate the list, so the two cannot drift.

### Approval Check Format

```markdown
✓ Approval found: "[quote the approval phrase]"
Proceeding with implementation...
```

Or if not found:

```markdown
⚠️ **Approval Required**

This agent requires explicit user approval before implementation.

**To proceed**: Reply with "yes", "go ahead", or use `/techne-implement`.
```

## Decision Classification

Classify decisions before acting:

| Tier | Type | Action |
|------|------|--------|
| 1 | Routine | Apply rule directly, no approval needed |
| 2 | Standard | Quick consideration, check precedent, proceed; state the choice in one line |
| 3 | Design (core §2 threshold holds) | Explore, then show 3–7 candidates as the decision card (`response-templates` T2), led by the recommendation; a subagent returns the card to the orchestrator, which takes the recommendation itself unless the choice passes the stop list |

### Tier 1 Examples (Just Do It)
- Apply formatting
- Fix style violations
- Remove narration comments
- Add missing type hints

### Tier 2 Examples (Quick Decision)
- Error message wording
- Variable naming (when domain clear)
- Small refactoring choices

### Tier 3 is decided by the threshold, not the topic
An architecture, API, or abstraction choice is Tier 2 when the conversation settles it or its candidates give the user the same result; it is Tier 3 only when the user asked for options or the candidates differ in what the user gets with no signal for one of them. Example: "REST or gRPC for a new internal service" is Tier 2 when the repository already serves gRPC everywhere; it is Tier 3 when the user said "it will also be called from browsers" and nothing settles the trade-off.

## Stop Conditions

Every agent has boundaries. When you catch yourself crossing them, STOP.

**Common stop conditions:**
- Writing code when job is review → STOP, report issues only
- Modifying production code when job is testing → STOP, test as-is
- Adding features not in plan → STOP, leave them out and mention them in the report
- Implementing without approval → STOP, request approval

## Human-Only Actions

Some side effects require a human owner and are never delegated to an agent, even with approval in-scope:

| Action | Why human-only | What agent does instead |
|---|---|---|
| **Push commits, open PRs, approve/merge PRs** | Externally visible state change | Prepare the commit/PR body in the working branch; user executes `git push` / `gh pr create` |
| **Delete/close Jira issues or Confluence pages** | Irreversible from the agent's side | Never — always defer |

### Jira issue creation — only on the user's explicit request

`mcp__atlassian__createJiraIssue` and `mcp__atlassian__createIssueLink` are permitted, but only when the user has explicitly asked for issues to be created in this conversation. Issue creation is visible to the whole team and cannot be undone from the agent's side, so inferred intent ("the plan looks done, I'll publish it") never counts.

1. Draw the tree that would be created — epic, children, sub-children — with the exact title of every issue, its type, and the links between them.
2. Wait for the user to approve that tree (all of it or named items). A new or changed tree needs a new approval.
3. Create exactly the approved items, parents before children, links last; report every created key.

Without an explicit request, draft the issue text (title, description, acceptance criteria) in chat or in a file instead.

Agent-safe Jira operations: `getJiraIssue`, `searchJiraIssuesUsingJql`, `addCommentToJiraIssue`, `editJiraIssue`, `transitionJiraIssue`, `addWorklogToJiraIssue`. Comments and transitions are reversible; issue create is not.

## Feedback Format

When reporting issues back to another agent or user:

```markdown
### 🔴 Must Fix (Blocking)
- [ ] `file.py:42` — **Issue**: <description>
  **Fix**: <conceptual fix, not code>

### 🟡 Should Fix (Important)
- [ ] `file.py:87` — **Issue**: <description>
  **Fix**: <conceptual fix>

### 🟢 Consider (Optional)
- [ ] `file.py:120` — **Suggestion**: <improvement idea>

### Summary
Review: X blocking | Y important | Z suggestions
Action: [Fix blocking and re-review] or [Ready to proceed]
```

---

## Compaction Survival

The `pre_compact_mask` hook (in the `hooks` block of `settings.json`) automatically captures branch, modified files, and key context before compaction. After compaction, the preserved context helps the next agent resume work without re-reading the entire codebase.
