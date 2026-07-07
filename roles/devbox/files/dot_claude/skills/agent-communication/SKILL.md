---
name: agent-communication
description: >
  Shared patterns for agent handoffs, escalation rules, completion formats, and user
  interaction. Use when agents need to communicate with each other or with users.
---

# Agent Communication Patterns

Standardised patterns for agent-to-agent handoffs, user communication, and escalation.

## Handoff Protocol

Every agent must define its position in the pipeline:

```markdown
**Receives from**: <upstream agent or "User"> (`document.md` + optionally `{stage}_output.json`)
**Produces for**: <downstream agent or "User">
**Deliverables**:
  - `document.md` — primary (human-readable reasoning and rationale)
  - `{stage}_output.json` — supplementary (structured contract for downstream agents, see `structured-output` skill)
**Completion criteria**: <what must be true before handoff>
```

When reading upstream output, check for `{stage}_output.json` first (faster, typed). Fall back to the markdown file if JSON is not available.

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
| **TPM** | *(user input)* | `spec.md`, `research.md`, `decisions.md`, `spec_output.json` |
| **Domain Expert** | `spec.md`, `spec_output.json` | `domain_analysis.md`, `domain_output.json` |
| **Domain Modeller** | `domain_analysis.md`, `domain_output.json`, `spec.md` | `domain_model.md`, `domain_model.json` |
| **Designer** | `spec.md`, `domain_analysis.md`, `plan.md`?, `api_design.md`? | `design.md`, `design_system.tokens.json`, `design_output.json` |
| **Impl Planner** | `spec.md`, `spec_output.json`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `plan.md`, `plan_output.json` |
| **Database Designer** | `plan.md`, `plan_output.json`, `spec.md`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `schema_design.md`, `migrations/` |
| **API Designer** | `plan.md`, `plan_output.json`, `spec.md`, `domain_analysis.md`, `domain_model.md`, `domain_model.json` | `api_design.md`, `api_spec.yaml`, `api_design_output.json` |
| **SE (backend)** | `plan.md`, `plan_output.json`, `api_spec.yaml`, `schema_design.md`, `domain_model.md`?, `domain_model.json`? | *(source code)*, `se_{lang}_output.json` |
| **SE (frontend)** | `plan.md`, `plan_output.json`, `design.md`, `design_output.json`, `api_spec.yaml`, `domain_model.md`?, `domain_model.json`? | *(source code)*, `se_frontend_output.json` |
| **Observability** | `plan.md`, `plan_output.json` | *(dashboards, alerts)* |
| **Test Writer** | `plan.md`, `spec.md`, `domain_model.json`?, `domain_model.md`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(test files)* |
| **Code Reviewer** | `plan.md`, `spec.md`, `domain_model.json`?, `domain_model.md`?, `design.md`?, `design_output.json`?, `se_{lang}_output.json`?, `se_frontend_output.json`? | *(review report — inline)* |
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

**Fallback**: If a JSON file doesn't exist, fall back to the corresponding markdown file. Never fail because a JSON file is missing (see `structured-output` skill — Graceful Degradation Rule).

### Work Stream Handoffs

When the planner produces work streams, downstream agents consume them via `plan_output.json`:

1. **Each `/techne-*` command reads** `plan_output.json` → extracts `work_streams` and `parallelism_groups`
2. **Each stream's agent** receives its assigned `requirements` list as scope
3. **API contract is the handshake** — frontend streams depend on API contract completion, not backend implementation
4. **Schema before backend** — if a schema stream exists, it must complete before backend implementation begins

---

## Completion Output Format

When an agent completes its work:

```markdown
> <One-line summary of what was done>
>
> **Next**: Run `<next-agent>` to <action>.
>
> Say **'continue'** to proceed, or provide corrections.
```

#### Examples

**Software Engineer:**
```markdown
> Implementation complete. Created/modified X files.
>
> **Next**: Run `/techne-test` to write tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Test Writer:**
```markdown
> Tests complete. X test cases covering Y scenarios.
>
> **Next**: Run `/techne-review` to review implementation and tests.
>
> Say **'continue'** to proceed, or provide corrections.
```

**API Designer:**
```markdown
> API design complete. 4 resources, 12 endpoints defined.
>
> **Next**: Run `/techne-implement` to begin backend implementation, or `/techne-design` for UI/UX design.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Designer (UI/UX):**
```markdown
> Design specification complete. 8 components specified, 42 tokens defined.
>
> **Next**: Run `/techne-implement` to have `software-engineer-frontend` implement from this spec.
>
> Say **'continue'** to proceed, or provide corrections.
```

**Code Reviewer (issues found):**
```markdown
> Review complete. Found X blocking, Y important, Z optional issues.
>
> **Next**: Address blocking issues with `/techne-implement`, then re-run `/techne-review`.
>
> Say **'fix'** to have SE address issues, or provide specific instructions.
```

**Code Reviewer (approved):**
```markdown
> Review complete. No blocking issues found.
>
> **Next**: Ready to commit and create PR.
>
> Say **'commit'** to proceed, or provide corrections.
```

---

## Escalation Rules

### Model Downgrade Notice (Opus → Sonnet)

SE agents default to opus. When the `/techne-implement` command auto-downgrades to sonnet for a simple task, it shows:

```markdown
Task looks straightforward (N files, ~M lines). Using Sonnet for speed. Say 'opus' to override.
```

Code reviewers and implementation planners always use opus — no downgrade logic applies.

### User Escalation

Stop and ask the user when:

1. **Ambiguous requirements** — Multiple valid interpretations
2. **Trade-off decisions** — Significant impact either way
3. **Scope questions** — Unclear what's in/out of scope
4. **Blocking issues** — Cannot proceed without input

### How to Ask Questions

**CRITICAL: Batch all open doubts into a single `AskUserQuestion` call.** Do not drip-feed questions one at a time. See `CLAUDE.md` §Discipline Protocol — Inquiry for the binding rule.

**Format:**
```markdown
[Context]: Working on [X], encountered [situation].

Options:
A) [Option] — [trade-off]
B) [Option] — [trade-off]

Recommendation: [A/B] because [reason].

**[Awaiting your decision]**
```

**Example:**
```markdown
The `process_order` function can handle empty orders two ways:

A) Reject with ValidationError — Explicit, prevents downstream issues
B) Return empty result — Permissive, lets caller decide

Recommendation: A because empty orders indicate upstream bugs.

**[Awaiting your decision]**
```

## Approval Validation

Before implementation, agents must verify explicit approval exists.

### Valid Approval Phrases

- "yes", "yep", "y", "go ahead", "proceed", "do it"
- "approved", "looks good", "implement it"
- "option 1" / "option 2" (explicit choice)
- `/techne-implement` command

### NOT Approval (Keep Waiting)

- "interesting", "I see", "okay" (acknowledgment)
- Follow-up questions
- "let me think about it"
- Silence

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
| 2 | Standard | Quick consideration, check precedent, proceed |
| 3 | Design | Full exploration (5-7 options), present to user |

### Tier 1 Examples (Just Do It)
- Apply formatting
- Fix style violations
- Remove narration comments
- Add missing type hints

### Tier 2 Examples (Quick Decision)
- Error message wording
- Variable naming (when domain clear)
- Small refactoring choices

### Tier 3 Examples (Present Options)
- Pattern/architecture selection
- API design choices
- New abstraction boundaries

## Stop Conditions

Every agent has boundaries. When you catch yourself crossing them, STOP.

**Common stop conditions:**
- Writing code when job is review → STOP, report issues only
- Modifying production code when job is testing → STOP, test as-is
- Adding features not in plan → STOP, ask about scope
- Implementing without approval → STOP, request approval

## Human-Only Actions

Some side effects require a human owner and are never delegated to an agent, even with approval in-scope:

| Action | Why human-only | What agent does instead |
|---|---|---|
| **Create Jira issue** (`mcp__atlassian__createJiraIssue`) | Issue creation binds tracking metadata (project, reporter, labels) that only the human owns; blocked in `settings.json` `permissions.deny` | Draft the issue text (title + description + acceptance criteria) in the chat or in a file; user creates the issue and pastes the URL back |
| **Create Jira issue link** (`mcp__atlassian__createIssueLink`) | Same rationale; blocked | Suggest the link (source key → target key + link type) in chat; user creates it |
| **Push commits, open PRs, approve/merge PRs** | Externally visible state change | Prepare the commit/PR body in the working branch; user executes `git push` / `gh pr create` |
| **Delete/close Jira issues or Confluence pages** | Irreversible from the agent's side | Never — always defer |

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

## Structured Handoff Protocol

When chaining `/techne-*` commands (especially during long sessions or after compaction), include structured context in the next agent's prompt to preserve critical state.

### Handoff Schema

```json
{
  "handoff": {
    "from_agent": "string (agent name)",
    "to_agent": "string (target agent name)",
    "status": "complete | partial | blocked",
    "branch": "string (current git branch)",
    "files_modified": ["string (relative paths)"],
    "decisions_made": [
      { "question": "string", "decision": "string", "rationale": "string" }
    ],
    "blocking_issues": ["string (issues requiring resolution)"],
    "context_keys": {
      "jira_issue": "string",
      "plan_path": "string",
      "output_json": "string (path to structured output)"
    }
  }
}
```

### When to Use

| Situation | Use Structured Handoff? |
|-----------|------------------------|
| `/techne-implement` → `/techne-test` → `/techne-review` chain | Yes — pass via prompt context |
| After context compaction | Yes — restore from `pre_compact_mask` output |
| Single-agent interactive session | No — free-text is fine |

### Compaction Survival

The `pre_compact_mask` hook (in `hooks.json`) automatically captures branch, modified files, and key context before compaction. After compaction, the preserved context helps the next agent resume work without re-reading the entire codebase.

For multi-step sessions, each agent should include `context_keys` in its completion output so the next agent can quickly locate all relevant artifacts without searching.
