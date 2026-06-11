---
description: Show available capabilities, commands, and workflow examples
---

You are showing the user what this Claude Code environment can do. Print the guide below verbatim (adjusting formatting if needed), then ask if they want details on any section.

---

Print this:

## What I Can Do

This environment has **19 slash commands**, **33 specialised agents**, and **79 knowledge skills**. Here's how to use them.

---

### Writing Code

The recommended flow for any code change:

```
/techne-implement          → spawns a software engineer agent (Go, Python, or Frontend)
/techne-test               → generates tests for what you just changed
/techne-review             → code review by a specialised reviewer agent
/techne-verify             → pre-PR quality gate (build, lint, typecheck, test)
```

**Example:** "Add a retry middleware to the HTTP client"
→ `/techne-implement` detects Go, spawns the Go software engineer agent, writes the code, formats with `goimports`.

You can also skip the pipeline and ask me to edit code directly — the agent workflow is opt-in per project via `/techne-init-workflow`.

---

### Planning Before Coding

```
/techne-plan               → create an implementation plan from requirements or a spec
/techne-domain-analysis    → challenge assumptions with a domain expert agent
/techne-api-design         → design REST/OpenAPI or Protobuf/gRPC contracts
/techne-schema             → design a database schema (Postgres, MySQL, Mongo, CockroachDB)
/techne-design             → create UI/UX spec with design tokens
```

**Example:** "Design a notification system"
→ `/techne-plan` reads the codebase, produces a step-by-step plan, waits for your approval before any implementation.

---

### Full Development Cycle

```
/techne-full-cycle         → runs the complete pipeline with milestone gates:
                      TPM → Domain → Model → Design → Plan → API → Implement → Test → Review
```

Each phase produces output consumed by the next. You approve at each gate.

---

### Project Setup

```
/techne-init-workflow      → enable the agent pipeline for this project
                      (full = auto-commit + complexity escalation, or lightweight)
/techne-devcontainer       → scaffold a Docker sandbox with iptables egress firewall
                      (language auto-detection, domain allowlist from settings.json)
```

**Devcontainer CLI** (outside Claude Code):
```
claude-devcontainer init      → copy template, detect languages
claude-devcontainer build     → build the Docker image
claude-devcontainer run       → run Claude Code inside the container
claude-devcontainer run --bypass  → run with --dangerously-skip-permissions
```

---

### Session Management

```
/techne-checkpoint         → save context before exiting or when context gets large
/techne-checkpoint resume  → restore context in a new session
```

---

### Meta: Building Agents & Skills

```
/techne-build-agent        → create or validate an agent definition (with adversarial meta-review)
/techne-build-skill        → create or validate a skill module
/techne-audit              → audit the library for freshness and consistency
/techne-validate-config    → check cross-references and frontmatter integrity
/techne-learn              → extract a pattern from this session into a reusable skill
```

---

### Available Agents (by Category)

**Software Engineers:** Go, Python, Frontend (TypeScript/React/Next.js)
**Code Reviewers:** Go, Python, Frontend
**Test Writers:** Unit tests (Go, Python, Frontend), Integration tests (Go, Python)
**Planners:** Implementation planner (Go, Python, Python monolith)
**Designers:** API designer, Database designer, UI/UX designer, Domain modeller
**Architecture:** Architect, Technical product manager, Domain expert
**Quality:** Build resolver (Go), Refactor/cleaner, TDD guide, Doc updater, Observability engineer
**Meta:** Agent builder, Skill builder, Meta reviewer, Freshness auditor, Consistency checker

---

### Tips

- **I follow an approval protocol.** When you ask me to analyse or recommend, I present options and wait. Say "go ahead" or "do it" to proceed.
- **Model routing matters.** I use Haiku for search tasks, Sonnet for implementation, Opus for architecture and complex reviews.
- **Skills load automatically** based on context — I know Go, Python, frontend, DDD, security, database patterns, observability, and more without you needing to activate anything.
- **Hooks run automatically** on tool calls — formatting, linting, and security guards are built in.

---

> Want details on any command? Just ask, or run any `/command` directly.
