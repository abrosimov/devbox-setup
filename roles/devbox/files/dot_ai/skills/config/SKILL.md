---
name: config
description: >
  Task context and vault layout for agents and commands: PROFILE, VAULT, BRANCH, JIRA_ISSUE,
  BRANCH_NAME from resolve_context.py, the delivery-unit homes in the kadmos vault, and the
  settings hierarchy. Use when resolving where artefacts live, reading configuration
  variables, or placing a note.
problem: "Agents and commands hard-code paths and task variables, leading to inconsistent vault and branch resolution."
related: [shared-utils, workflow]
---

# Claude Code Configuration

Configurable paths and the task context every command and agent starts from.

## Task Context

**IMPORTANT**: Commands compute context ONCE and pass it to agents. Agents do not re-compute.

```bash
CONTEXT_JSON=$(~/.claude/bin/resolve_context.py)   # exit 0 = resolved; exit 1 = stderr says what is missing
DEFAULT_BRANCH=$(.claude/bin/git-default-branch)
```

| Variable | Source | Example |
|----------|--------|---------|
| `PROFILE` | `MNEMOSYNE_PERISTASEOS`, always read first; unset is an error, not a default | `personal` |
| `VAULT` | `.vault-root` at the repository top level, read under the profile's rule (below) | `/home/me/Projects/app/docs` |
| `BRANCH` | `git branch --show-current` | `PROJ-123_add_user_auth` |
| `JIRA_ISSUE` | first segment of the branch when it is `PROJ-123_...`; otherwise `null` | `PROJ-123` |
| `BRANCH_NAME` | the rest of the branch after that segment, or the whole branch | `add_user_auth` |
| `DEFAULT_BRANCH` | `.claude/bin/git-default-branch` | `main` |

A Jira issue is optional. It is the value of the `issue` field on the notes a task produces, never a
directory.

### Where the vault is

| `MNEMOSYNE_PERISTASEOS` | `.vault-root` holds | `VAULT` |
|---|---|---|
| `personal` | the name of one immediate child (`docs`) | `<repo>/docs` |
| `personal` | an absolute path, or the file is missing | error: on a personal machine the vault lives inside the repository |
| `work` | an absolute path (or `~/...`) outside the repository | that directory |
| `work` | a child name, or the file is missing | error: on a work machine the vault lives outside the repository |
| unset | anything | error: `make personal` / `make work` render the variable into the shell rc |

The vault is a kadmos vault: `.vault-profile` inside it, kadmos's own folders (`decisions/`,
`open_questions/`, `standards/`, `templates/`, ...) and the delivery-unit homes below. The repository
binds to it through `.vault-root` only; the materialiser never writes that file.

When invoking agents via the Task tool, include in the prompt:
```
Context: PROFILE={value}, VAULT={path}, BRANCH={value}, JIRA_ISSUE={value or null}, BRANCH_NAME={value}, DEFAULT_BRANCH={value}
```

## Default Branch Detection

`.claude/bin/git-default-branch` picks, in order: `claude.defaultBranch` git config, the remote HEAD,
`init.defaultBranch`, then `main`. Override per repository with
`git config --local claude.defaultBranch develop`. An optional
`git config --local claude.integrationBranch build/stable` makes commands offer a local merge
alongside push and PR.

## Delivery Units

Pipeline artefacts are notes in the vault, one per unit, with a typed id and links in frontmatter.
The homes and subtypes are kadmos's (CAD-FR-19); coverage is derived by following links and is never
written by hand.

| Unit | Home | Id | Written by | Read by |
|------|------|----|------------|---------|
| Requirement (`kind: functional` or `quality`) | `requirements/` | `REQ-NNNNN` | TPM | planner, bdd-spec-writer, reviewer |
| Invariant (`status: prose` → `formal` → `checked`) | `invariants/` | `INV-NNNNN` | domain-expert (prose), domain-modeller (predicate) | SE, tests, formal-model-writer, observability-engineer |
| Scenario (one Given/When/Then; `covers`, `exercises`) | `scenarios/` | `SC-NNNNN` | bdd-spec-writer | planner, SE, integration tests, reviewer |
| Work stream (`implements`, `verifies`, `depends_on`, `agent`) | `workstreams/` | `WS-NNNNN` | implementation-planner | the one agent that executes it |
| Decision, open question | `decisions/`, `open_questions/` | `D-NNN`, `OQ-NNN` | any agent, per kadmos's skills | all |

Each home follows kadmos's dated layout (`requirements/2026/10/REQ-00012-fast-search.md`). A note
body is immutable once landed; a change is a successor note. An agent receives one id in its brief
(a `WS` for an implementer, a `REQ` for a scenario writer) and follows links from it; it never loads
a home wholesale.

Code and specs point back at notes with kadmos code anchors, one comment line:
`ariadne-kadmou[<slug>|implements|kadmos://oikos/requirements/2026/10/REQ-00012-fast-search.md]`
(`tests` for a test, `evidences` for a TLA+ property against `invariants/...#Statement`).

Structured outputs that are not notes (`se_<lang>_output.json`, rendered dashboards, migrations)
stay where their tool expects them in the repository, named in the work stream that produced them.

## Settings Hierarchy

Claude Code merges settings from multiple scopes. **More specific scopes override broader ones.**

| Priority | File | Scope | Tracked? |
|----------|------|-------|----------|
| 1 (highest) | `.claude/settings.local.json` | Per-project, per-developer | gitignored |
| 2 | `.claude/settings.json` | Per-project, shared | committed |
| 3 (lowest) | `~/.claude/settings.json` | Global baseline | Ansible-deployed |

**Merge rules:**
- `defaultMode`: overridden by more specific scope
- `allow` / `deny` arrays: **additive** (concatenated across all scopes)
- Evaluation order: deny (checked first) > allow (checked last)

### Global `~/.claude/settings.json`

Deployed by Ansible. Contains:
- **deny**: Security floor (destructive ops, secrets, force push, publishing) — projects can't weaken these
- **allow**: All language tooling (Go, Python, Frontend, Docker, Observability), git safe ops, system utils

### Project `.claude/settings.json`

Optional. Use when a project needs additional permissions beyond the global baseline, or wants to restrict certain operations. Create manually as needed.

### `settings.local.json` — Personal Overrides

For per-developer customization. Common use cases:

| Use Case | What to Add |
|----------|-------------|
| **Push without prompting** | `"allow": ["Bash(git push *)"]` |
| **Database CLIs** | `"allow": ["Bash(psql *)", "Bash(mongosh *)", "Bash(redis-cli *)"]` |
| **API testing** | `"allow": ["Bash(curl *)", "Bash(http *)"]` |
| **Ansible (devbox project)** | `"allow": ["Bash(ansible *)", "Bash(ansible-playbook *)", "Bash(ansible-lint *)", "Bash(ansible-galaxy *)"]` |
| **Stricter mode** | `"defaultMode": "plan"` |

Example `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git push *)",
      "Bash(psql *)"
    ]
  }
}
```

**Note:** `settings.local.json` is gitignored and preserved across Ansible deploys. Each developer maintains their own.
