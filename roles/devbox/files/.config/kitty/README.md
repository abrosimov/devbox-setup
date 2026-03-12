# Kitty Terminal

All custom shortcuts use native macOS key codes (`0x##`) for layout-independent mapping — they work regardless of keyboard layout (English, Russian, etc.).

## Splits

| Key | Action |
|-----|--------|
| `Cmd+D` | Split vertically (side by side) |
| `Cmd+Shift+D` | Split horizontally (top/bottom) |
| `Cmd+Opt+←/→/↑/↓` | Navigate between panes |
| `Cmd+Shift+Enter` | Toggle maximize current pane (stack layout) |

## Tabs

| Key | Action |
|-----|--------|
| `Cmd+T` | New tab |
| `Cmd+Shift+T` | New tab (same cwd) |
| `Cmd+W` | Close pane (or tab if last pane) |
| `Cmd+1` — `Cmd+9` | Jump to tab N |

## Hints (select text patterns from terminal output)

| Key | Action |
|-----|--------|
| `Ctrl+Shift+E` | Select URL, open in browser |
| `Cmd+Shift+P` | Select file path, insert in terminal |
| `Cmd+Shift+G` | Select file:line, open in editor |
| `Cmd+Shift+H` | Select git hash, copy to clipboard |

## Scrollback & Shell Integration

| Key | Action |
|-----|--------|
| `Ctrl+Shift+H` | Full scrollback in bat pager |
| `Ctrl+Shift+G` | Last command output in pager |
| `Ctrl+Shift+Z` | Jump to previous shell prompt |
| `Ctrl+Shift+X` | Jump to next shell prompt |

## Other

| Key | Action |
|-----|--------|
| `Cmd+Shift+O` | File picker (choose-files kitten) |
| `Cmd+=` / `Cmd+-` | Font size up/down |
| `Cmd+0` | Reset font size |
| `Ctrl+Shift+F5` | Reload config |
| `Ctrl+Shift+F6` | Debug config |

## Layout-Independent Key Codes

Custom shortcuts use macOS virtual key codes for physical key mapping:

| Key | Code | Key | Code |
|-----|------|-----|------|
| D | 0x02 | T | 0x11 |
| W | 0x0D | E | 0x0E |
| P | 0x23 | G | 0x05 |
| H | 0x04 | O | 0x1F |
| Enter | 0x24 | | |

To find a key's native code, run `kitty --debug-input` and press the key.
