# Neovim Configuration

Leader key: `.` (dot)

## Key Discovery (which-key)

Press `.` and wait 200ms to see all available keybindings organized by group:

| Group | Prefix | Contents |
|-------|--------|----------|
| Find | `.f` | Telescope pickers (files, grep, buffers, keymaps) |
| Debug | `.d` | DAP breakpoints, continue, test debug |
| Test/Tree | `.t` | Neotest + Neo-tree toggle |
| Git | `.g` | Worktree switching |
| Diagnostics | `.x` | Trouble panel |
| Refactor/Run | `.r` | Rename, run main |
| Workspace | `.w` | Workspace symbols |
| Code | `.c` | Code actions |
| Prev | `[` | Previous diagnostic/function/class |
| Next | `]` | Next diagnostic/function/class |
| Go to | `g` | Definition, implementation, references |

**Fuzzy search all keymaps**: `.fk` opens Telescope keymap picker

## Navigation

| Key | Action |
|-----|--------|
| `gd` | Go to definition |
| `gi` | Go to implementation |
| `gr` | Find all references (usages) |
| `K` | Hover (show type/docs) |
| `.ds` | Document symbols (current file) |
| `.ws` | Workspace symbols (search across project) |
| `[d` / `]d` | Previous/next diagnostic |
| `[f` / `]f` | Previous/next function |
| `[c` / `]c` | Previous/next class |

## Editing

| Key | Action |
|-----|--------|
| `.rn` | Rename symbol |
| `.ca` | Code actions |
| `.i` | Resolve import (LSP code action) |
| `Ctrl+Space` | Trigger completion |
| `Ctrl+y` | Accept completion |
| `Enter` | Accept completion (or newline if no popup) |
| `Ctrl+e` | Dismiss completion |

## Search (Telescope)

| Key | Action |
|-----|--------|
| `.ff` | Find files |
| `.fg` | Live grep (ripgrep) |
| `.fb` | List buffers |
| `.fo` | Recent files |
| `.fk` | Search all keymaps |

## File Explorer (Neo-tree)

| Key | Action |
|-----|--------|
| `.t` | Toggle file explorer (right) |
| `.b` | Toggle buffer list (left) |

## Git

| Key | Action |
|-----|--------|
| `.gw` | Switch git worktree |

## Testing (Neotest)

| Key | Action |
|-----|--------|
| `.tr` | Run nearest test |
| `.tf` | Run file tests |
| `.ts` | Toggle test summary |
| `.to` | Toggle test output panel |

## Debugging (DAP)

| Key | Action |
|-----|--------|
| `.db` | Toggle breakpoint |
| `.dc` | Continue debug |
| `.dt` | Debug nearest test |

## Diagnostics

| Key | Action |
|-----|--------|
| `.e` | Show diagnostic float |
| `.q` | Open diagnostic quickfix list |
| `.xx` | Toggle Trouble diagnostics panel |

## Buffers & Windows

| Key | Action |
|-----|--------|
| `Tab` | Next buffer |
| `Shift+Tab` | Previous buffer |
| `Ctrl+h/j/k/l` | Move focus between splits |
| `Space` | Half page down |
| `Esc` | Close floating windows + clear search |

## Folding

| Key | Action |
|-----|--------|
| `za` | Toggle fold |
| `zc` | Close fold |
| `zo` | Open fold |
| `zM` | Close all folds |
| `zR` | Open all folds |

## Comments (Comment.nvim)

| Key | Mode | Action |
|-----|------|--------|
| `gcc` | Normal | Toggle line comment |
| `gc` | Visual | Toggle comment on selection |

## Running Code

| Key | Action |
|-----|--------|
| `.rm` | Run main (opens terminal split with appropriate runner) |

Supported: Go, Python, TypeScript, JavaScript, Rust, C, C++, Dart, Swift, OCaml

## Clipboard

Delete/change operations go to black hole register (don't pollute clipboard).
Use `.d` when you need "cut" (delete + copy to clipboard).
