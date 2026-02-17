---
description: Set up a devcontainer sandbox for the current project
---

You are setting up a Docker devcontainer for sandboxed Claude Code development. The template lives at `~/.claude/templates/devcontainer/`.

## Parse Arguments

- `/devcontainer` or `/devcontainer init` → initialise devcontainer for this project
- `/devcontainer add-domain <domain>` → append domain to `.devcontainer/domains.conf`
- `/devcontainer strip <lang>` → disable a language in `.devcontainer/devcontainer.json` build args

## Subcommand: init

### 1. Check for Existing Config

```bash
[ -d .devcontainer ] && echo "EXISTS" || echo "MISSING"
```

If `.devcontainer/` already exists, ask:

> `.devcontainer/` already exists. **Overwrite with fresh template, or keep current?**

### 2. Copy Template

```bash
cp -r ~/.claude/templates/devcontainer/ .devcontainer/
```

### 3. Detect Project Type

```bash
[ -f go.mod ] && echo "GO"
[ -f pyproject.toml ] || [ -f setup.py ] || [ -f requirements.txt ] && echo "PYTHON"
[ -f Cargo.toml ] && echo "RUST"
[ -f dune-project ] || [ -f *.opam ] 2>/dev/null && echo "OCAML"
[ -f package.json ] && echo "NODE"
```

For each detected language, set the corresponding `INSTALL_<LANG>` build arg to `"true"` in `.devcontainer/devcontainer.json`.

Node/TypeScript is always available (base image is `node:20-bookworm`), so no flag needed.

Use the Edit tool to modify `.devcontainer/devcontainer.json`:

```json
{
  "build": {
    "args": {
      "INSTALL_GO": "true",
      ...
    }
  }
}
```

### 4. Merge Domains from Project Settings

Check if the project has a `.claude/settings.json` with `sandbox.network.allowedDomains`:

```bash
[ -f .claude/settings.json ] && jq -r '.sandbox.network.allowedDomains[]? // empty' .claude/settings.json 2>/dev/null
```

If project-specific domains exist that aren't in `.devcontainer/domains.conf`, append them:

```
# --- Project-specific domains ---
extra-domain.example.com
```

### 5. Gitignore Suggestion

Check if `.devcontainer/` is git-tracked:

```bash
git check-ignore -q .devcontainer/ 2>/dev/null && echo "IGNORED" || echo "TRACKED"
```

If tracked, mention:

> `.devcontainer/` will be tracked by git. This is usually fine — team members benefit from shared container config.

### 6. Confirm

> Devcontainer initialised for this project.
>
> Languages: **{detected list}**
> Template: `.devcontainer/`
>
> Next steps:
> - **VS Code**: "Reopen in Container" from command palette
> - **CLI**: `claude-devcontainer build && claude-devcontainer run`
> - **Add domains**: `/devcontainer add-domain example.com`
> - **Remove a language**: `/devcontainer strip rust`

## Subcommand: add-domain

### 1. Validate Input

The argument after `add-domain` is the domain. It should look like a domain name (`example.com`, `*.example.com`).

### 2. Append to domains.conf

Check if `.devcontainer/domains.conf` exists:

```bash
[ -f .devcontainer/domains.conf ] && echo "EXISTS" || echo "MISSING"
```

If missing, inform the user to run `/devcontainer init` first.

If present, use the Edit tool to append the domain at the end of the file.

### 3. Confirm

> Added `{domain}` to `.devcontainer/domains.conf`. Rebuild the container to apply.

## Subcommand: strip

### 1. Validate Input

The argument after `strip` should be one of: `go`, `python`, `rust`, `ocaml`.

Map to build arg:
- `go` → `INSTALL_GO`
- `python` → `INSTALL_PYTHON`
- `rust` → `INSTALL_RUST`
- `ocaml` → `INSTALL_OCAML`

### 2. Update devcontainer.json

Read `.devcontainer/devcontainer.json` and set the corresponding build arg to `"false"`.

### 3. Confirm

> Disabled **{lang}** in `.devcontainer/devcontainer.json`. Rebuild the container to apply.
