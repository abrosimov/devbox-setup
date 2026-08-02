# Anthropic Agent Authoring Reference

Cached reference from official Anthropic documentation (February 2026).
Source: https://code.claude.com/docs/en/sub-agents

## Agent .md File Structure

Two required parts:
1. YAML frontmatter (between `---` markers)
2. Markdown body containing the system prompt

## Frontmatter Schema — All Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier — lowercase letters and hyphens |
| `description` | Yes | When Claude should delegate to this subagent (used for automatic invocation) |
| `tools` | No | Tools the subagent can use. Inherits all tools if omitted |
| `disallowedTools` | No | Tools to deny, removed from inherited or specified list |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit`. Defaults to `inherit` |
| `permissionMode` | No | `default`, `acceptEdits`, `delegate`, `dontAsk`, `bypassPermissions`, or `plan` |
| `maxTurns` | No | Maximum agentic turns before the subagent stops |
| `skills` | No | Skills loaded into subagent's context at startup (full content injected) |
| `mcpServers` | No | MCP servers available to this subagent |
| `hooks` | No | Lifecycle hooks scoped to this subagent |
| `memory` | No | Persistent memory scope: `user`, `project`, or `local` |

### Fields NOT in Our System (verify if needed)

- `disallowedTools` — denylist approach (we use allowlist via `tools`)
- `maxTurns` — turn limits (we don't currently set these)
- `mcpServers` — MCP server scoping (some agents use MCP but via tool names)
- `hooks` — agent-scoped hooks (we use global hooks.json)
- `memory` — persistent memory (not currently used by any agent)

## Agent Scopes and Priority

| Location | Scope | Priority |
|----------|-------|----------|
| `--agents` CLI flag | Current session | 1 (highest) |
| `.claude/agents/` | Current project | 2 |
| `~/.claude/agents/` | All projects | 3 |
| Plugin's `agents/` | Where plugin enabled | 4 (lowest) |

Our agents deploy to `~/.claude/agents/` (scope 3 — all projects).

## Key Patterns from Anthropic

### Description Best Practices

- Write clear descriptions so Claude knows WHEN to delegate
- Include "use proactively" to encourage automatic delegation
- Be specific about task type and domain

### System Prompt (Body) Guidelines

- Subagents receive ONLY this system prompt (plus basic environment details)
- They do NOT receive the full Claude Code system prompt
- Keep focused on the specific task
- Include step-by-step instructions for complex workflows

### Context Isolation

- Subagents maintain separate context from main agent
- Prevents information overload in main conversation
- Results summarised and returned to main conversation
- Multiple subagents can run concurrently for parallel work

### Tool Restriction Patterns

| Pattern | Tools | Use Case |
|---------|-------|----------|
| Read-only | `Read, Grep, Glob` | Reviewers, analysers |
| Code modification | `Read, Edit, Grep, Glob, Bash` | Engineers |
| Full access | `Read, Write, Edit, Grep, Glob, Bash, WebSearch` | Designers, planners |

**Anthropic says**: Subagents cannot spawn their own subagents. Do not include `Task` in subagent's tools.

### Persistent Memory

```yaml
memory: user     # ~/.claude/agent-memory/<name>/
memory: project  # .claude/agent-memory/<name>/
memory: local    # .claude/agent-memory-local/<name>/
```

- First 200 lines of MEMORY.md automatically loaded
- Read, Write, Edit tools auto-enabled when memory is enabled
- Enables cross-session learning

## Multi-Agent Orchestration

### Subagents vs Agent Teams

| Feature | Subagents | Agent Teams |
|---------|-----------|-------------|
| Context | Own window; results return to caller | Own window; fully independent |
| Communication | Report results back to main only | Teammates message each other directly |
| Coordination | Main agent manages all work | Shared task list with self-coordination |
| Best for | Focused tasks where only result matters | Complex work requiring collaboration |
| Token cost | Lower: results summarised | Higher: each teammate is separate instance |

### When to Use Agent Teams

- Research and review (multiple perspectives)
- New modules (each teammate owns separate piece)
- Debugging with competing hypotheses (challenge each other)
- Cross-layer coordination (frontend, backend, tests)

## Validation Checklist (from Anthropic guidance)

- [ ] `name` is unique, lowercase, hyphenated
- [ ] `description` clearly states WHEN to delegate (not just what it does)
- [ ] Body is a complete system prompt (agent receives nothing else)
- [ ] Tools are minimal — only what the agent needs
- [ ] No `Task` tool in subagent tools list
- [ ] Model choice justified (opus for reasoning, sonnet for speed, haiku for simple)
- [ ] Skills listed actually exist and are relevant
