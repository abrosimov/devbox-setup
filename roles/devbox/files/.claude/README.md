# Claude Code Configuration

Global Claude Code configuration deployed to `~/.claude/`.

## Agents

Specialised subagents for different tasks. Spawned via `/implement`, `/test`, `/review` commands or Task tool.

| Category | Examples |
|----------|----------|
| Software Engineers | `software-engineer-go`, `software-engineer-python`, `software-engineer-frontend` |
| Test Writers | `unit-test-writer-go`, `unit-test-writer-python`, `unit-test-writer-frontend` |
| Reviewers | `code-reviewer-go`, `code-reviewer-python`, `code-reviewer-frontend` |
| Planners | `technical-planner`, `domain-expert`, `api-designer`, `database-designer` |
| Utilities | `explorer`, `researcher`, `ui-designer` |

## Skills

Reusable knowledge modules automatically loaded based on context. Categories:

- **Languages** — `go-engineer`, `python-engineer`, `frontend-engineer`
- **Testing** — `go-testing`, `python-testing`, `frontend-testing`
- **Tooling** — `python-tooling`, `frontend-tooling`, `docker-validation`
- **Patterns** — `iterative-retrieval`, `diverge-synthesize-select`, `verification-loop`
- **Protocols** — `agent-base-protocol`, `code-writing-protocols`, `agent-communication`

## Commands

Slash commands for common workflows:

| Command | Description |
|---------|-------------|
| `/implement` | Spawn software engineer agent for code changes |
| `/test` | Write tests for recent changes |
| `/review` | Code review with language-specific reviewer |
| `/plan` | Create implementation plan from requirements |
| `/design` | UI/UX design specification |
| `/api-design` | Design API contracts (REST/gRPC) |
| `/schema` | Database schema design |
| `/options` | Generate diverse solution options (DSS protocol) |
| `/think` | Structured systems thinking (FPF) |
| `/verify` | Pre-PR quality gate (build, lint, test) |
| `/status` | Show pipeline progress |
| `/guide` | Show available capabilities |
| `/devcontainer` | Set up Docker sandbox for isolated runs |
| `/checkpoint` | Save/restore session context |

## Hooks

Pre/post tool-call guards in `hooks.json`:

- Sandbox enforcement
- Format-on-save triggers
- Lint checks

## MCP Servers

| Server | Purpose |
|--------|---------|
| Sequential Thinking | Structured multi-step reasoning |
| Playwright | Browser automation and testing |
| Memory Graph | Persistent knowledge across sessions |
| Figma | Design file integration |

## Devcontainer Template

Docker sandbox with network-level isolation for agent runs. Features:

- iptables egress firewall with domain allowlist
- Language toolchains (Go, Python, Node, Rust, OCaml)
- Host settings.json bind-mounted read-only

Use via `/devcontainer init` command.

## Validation

```bash
make validate-claude  # Check cross-references between agents, skills, commands
```
