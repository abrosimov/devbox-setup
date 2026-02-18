---
description: Initialise agent workflow for the current project
---

You are setting up the agent workflow for the current project by creating `.claude/workflow.json`.

## Parse Arguments

- `/init-workflow full` → full preset
- `/init-workflow light` → lightweight preset
- `/init-workflow` (no argument) → ask user to choose

## Presets

| Preset | `agent_pipeline` | `auto_commit` | `complexity_escalation` |
|--------|-----------------|---------------|------------------------|
| **full** | `true` | `true` | `true` |
| **light** | `true` | `false` | `false` |

### Flag Reference

| Flag | `true` | `false` |
|------|--------|---------|
| `agent_pipeline` | Code changes MUST go through agents (`/implement`) | Direct Edit/Write on code files allowed |
| `auto_commit` | Commands auto-commit via `git-safe-commit` after each phase | User commits manually |
| `complexity_escalation` | Auto-downgrade SE agents to Sonnet for simple tasks | Always use agent's default model (opus) |

## Steps

### 1. Check for Existing Config

```bash
[ -f .claude/workflow.json ] && echo "EXISTS" || echo "MISSING"
```

If it already exists, show current settings and ask:

> `.claude/workflow.json` already exists:
> ```json
> {current contents}
> ```
> **Overwrite with new settings, or keep current?**

### 2. Determine Preset

If no argument was passed, ask:

> Which workflow preset?
>
> **A) Full** — agents required, auto-commit, auto-downgrade for simple SE tasks
> **B) Lightweight** — agents required, manual commits, always opus (no downgrade)
> **C) Custom** — pick individual settings

For **Custom**, ask about each flag individually.

### 3. Create the Config

```bash
mkdir -p .claude
```

Then use the Write tool to create `.claude/workflow.json` with the chosen settings:

**Full preset:**
```json
{
  "agent_pipeline": true,
  "auto_commit": true,
  "complexity_escalation": true
}
```

**Light preset:**
```json
{
  "agent_pipeline": true,
  "auto_commit": false,
  "complexity_escalation": false
}
```

### 4. Confirm

> Agent workflow initialised for this project.
>
> Settings:
> - Agent pipeline: **{enabled/disabled}**
> - Auto-commit: **{enabled/disabled}**
> - Complexity escalation: **{enabled/disabled}**
>
> Config: `.claude/workflow.json`
>
> To change later: `/init-workflow` or edit `.claude/workflow.json` directly.
> To disable: delete `.claude/workflow.json`.

### 5. Offer Project Settings

Detect the project stack:

```bash
[ -f go.mod ] && echo "GO"
[ -f pyproject.toml ] || [ -f requirements.txt ] && echo "PYTHON"
[ -f package.json ] || [ -f tsconfig.json ] && echo "FRONTEND"
```

If a stack is detected AND no `.claude/settings.json` exists in the project, ask:

> Detected: **{stack(s)}** project. Create project-level `.claude/settings.json` with stack-specific permissions?
>
> **A) Yes** — add stack-appropriate tooling permissions
> **B) No** — use global defaults

If user says yes, create `.claude/settings.json` with permissions for the detected stack(s):

**Go project:**
```json
{
  "permissions": {
    "allow": [
      "Bash(go test *)",
      "Bash(go build *)",
      "Bash(go run *)",
      "Bash(go mod *)",
      "Bash(go get *)",
      "Bash(go generate *)",
      "Bash(go vet *)",
      "Bash(goimports *)",
      "Bash(golangci-lint *)",
      "Bash(mockery *)"
    ]
  }
}
```

**Python project:**
```json
{
  "permissions": {
    "allow": [
      "Bash(uv run *)",
      "Bash(uv sync *)",
      "Bash(uv add *)",
      "Bash(uv pip *)",
      "Bash(uv lock *)",
      "Bash(uvx *)",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)",
      "Bash(python *)",
      "Bash(python3 *)"
    ]
  }
}
```

**Frontend project:**
```json
{
  "permissions": {
    "allow": [
      "Bash(pnpm *)",
      "Bash(npm *)",
      "Bash(npx *)",
      "Bash(node *)"
    ]
  }
}
```

For **fullstack** projects, combine the relevant lists.

**Note:** If the global `~/.claude/settings.json` already covers these tools (it does by default), the project settings are additive and redundant — but they serve as documentation of what the project uses and as a safety net if the global config changes.

### 6. Gitignore Check

Check if `.claude/workflow.json` should be tracked:

```bash
git check-ignore -q .claude/workflow.json 2>/dev/null && echo "IGNORED" || echo "TRACKED"
```

If tracked (not ignored), mention:

> `.claude/workflow.json` will be tracked by git. This means the workflow settings are shared with your team. If you prefer per-developer settings, add `.claude/workflow.json` to `.gitignore`.
