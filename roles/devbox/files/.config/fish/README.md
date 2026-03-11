# Fish Shell

## Git Abbreviations

| Abbreviation | Expands To |
|--------------|------------|
| `co` | `git checkout` |
| `cob` | `git checkout -b` |
| `st` | `git status` |
| `gd` | `git diff` |
| `gdc` | `git diff --cached` |
| `add` | `git add` |
| `ci` | `git commit -m '...'` (cursor inside quotes) |
| `am` | `git commit --amend` |
| `br` | `git branch` |
| `pull` | `git pull origin` |
| `push` | `git push origin` |
| `merge` | `git merge` |
| `stash` | `git stash` |
| `gg` | `git grep -n '...'` (cursor inside quotes) |

## Editor Abbreviations

| Abbreviation | Expands To |
|--------------|------------|
| `vi` / `vim` | `nvim` |
| `vimdiff` / `vd` | `nvim -d` |

## Claude Code Abbreviations

| Abbreviation | Expands To |
|--------------|------------|
| `code` | `claude --model claude-opus-4-5` |
| `code_smart` | `claude --model claude-opus-4-6` |

## Custom Functions

### Project Management (`proj`)

| Command | Description |
|---------|-------------|
| `proj clone <url>` | Clone repo into `$PROJECTS_DIR/<name>/base/` |
| `proj ls` | List projects |
| `proj <name>` | `cd` into project directory |

### Git Worktrees (`wt`)

| Command | Description |
|---------|-------------|
| `wt add <branch>` | Create git worktree (auto-detects base branch) |
| `wt ls` | List worktrees |
| `wt rm <name>` | Remove worktree |
| `wt <name>` | `cd` to worktree directory |

### Kubernetes (`k`)

Run `k` with no arguments for full usage. Wrapper around kubectl with context/namespace helpers.

## Plugins

Managed via [Fisher](https://github.com/jorgebucaran/fisher):

- [tide](https://github.com/IlanCosman/tide) — prompt theme
- [fish_ssh_agent](https://github.com/ivakyb/fish_ssh_agent) — SSH agent management
