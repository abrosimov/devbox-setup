# Claude Code Configuration

Global Claude Code configuration deployed to `~/.claude/`.

## Agents

Specialised subagents for different tasks. Spawned via `/techne-implement`, `/techne-test`, `/techne-review` commands or Task tool.

| Category | Examples |
|----------|----------|
| Software Engineers | `software-engineer-go`, `software-engineer-python`, `software-engineer-frontend` |
| Test Writers | `unit-test-writer` (polyglot: Go, Python, Frontend) |
| Reviewers | `code-reviewer` (polyglot: Go, Python, Frontend) |
| Planners | `technical-planner`, `domain-expert`, `api-designer`, `database-designer` |
| Utilities | `explorer`, `researcher`, `ui-designer` |

## Skills

Reusable knowledge modules automatically loaded based on context. Categories:

- **Languages** — `go-engineer`, `python-engineer`, `frontend-engineer`
- **Testing** — `go-testing`, `python-testing`, `frontend-testing`
- **Tooling** — `python-tooling`, `frontend-tooling`, `docker-validation`
- **Patterns** — `iterative-retrieval`, `diverge-synthesize-select`
- **Protocols** — `agent-base-protocol`, `code-writing-protocols`, `agent-communication`

## Commands

Slash commands for common workflows:

| Command | Description |
|---------|-------------|
| `/techne-implement` | Spawn software engineer agent for code changes |
| `/techne-test` | Write tests for recent changes |
| `/techne-review` | Code review with language-specific reviewer |
| `/techne-plan` | Create implementation plan from requirements |
| `/techne-design` | UI/UX design specification |
| `/techne-api-design` | Design API contracts (REST/gRPC) |
| `/techne-schema` | Database schema design |
| `/techne-options` | Generate diverse solution options (DSS protocol) |
| `/techne-think` | Structured systems thinking (FPF) |
| `/techne-verify` | Pre-PR quality gate (build, lint, test) |
| `/techne-guide` | Show available capabilities |
| `/techne-devcontainer` | Set up Docker sandbox for isolated runs |

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

Use via `/techne-devcontainer init` command.

## Validation

```bash
make validate-claude  # Check cross-references between agents, skills, commands
```
