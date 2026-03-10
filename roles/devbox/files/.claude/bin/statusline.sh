#!/usr/bin/env bash
# Claude Code statusline — Kanagawa Paper Ink theme
# Matches the fish/Tide prompt aesthetic from the terminal theme.
#
# Receives JSON on stdin from Claude Code with session context.

input=$(cat)

# ── Parse fields ────────────────────────────────────────────────────────────
cwd=$(echo "$input" | jq -r '.cwd // .workspace.current_dir // "?"')
model=$(echo "$input" | jq -r '.model.display_name // "?"')
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
context_size=$(echo "$input" | jq -r '.context_window.context_window_size // 0')

# ── Shorten path (replace $HOME with ~) ─────────────────────────────────────
home="$HOME"
short_cwd="${cwd/#$home/~}"

# ── Kanagawa Paper Ink palette (ANSI 256 via \e[38;2;R;G;Bm truecolor) ──────
# Using printf with truecolor escapes. The terminal (kitty) supports this.
#
# Colors chosen from current-theme.conf:
#   fg_muted   #9e9b93  — inactive/separator
#   gold       #c4b28a  — yellow (cursor color, warm accent)
#   teal       #8ea49e  — cyan (pwd)
#   blue       #698a9b  — context bar
#   green      #699469  — context ok
#   red        #c4746e  — context critical
#   fg_main    #DCD7BA  — main foreground

RESET=$'\e[0m'
BOLD=$'\e[1m'
DIM=$'\e[2m'

c_gold=$'\e[38;2;196;178;138m'      # #c4b28a — model / accents
c_teal=$'\e[38;2;142;164;158m'      # #8ea49e — working dir
c_blue=$'\e[38;2;105;138;155m'      # #698a9b — context label
c_green=$'\e[38;2;105;148;105m'     # #699469 — context good
c_yellow=$'\e[38;2;212;193;150m'    # #d4c196 — context warning
c_red=$'\e[38;2;196;116;110m'       # #c4746e — context critical
c_muted=$'\e[38;2;158;155;147m'     # #9e9b93 — separators / dim text
c_fg=$'\e[38;2;220;215;186m'        # #DCD7BA — main text

SEP="${c_muted}│${RESET}"

# ── Context section ──────────────────────────────────────────────────────────
ctx_segment=""
if [ -n "$remaining" ]; then
    remaining_int=${remaining%.*}  # truncate to integer
    # Color the percentage based on how much is left
    if [ "$remaining_int" -ge 50 ] 2>/dev/null; then
        ctx_color="$c_green"
    elif [ "$remaining_int" -ge 20 ] 2>/dev/null; then
        ctx_color="$c_yellow"
    else
        ctx_color="$c_red"
    fi

    # Build a compact mini bar (10 chars wide)
    filled=$(( remaining_int / 10 ))
    empty=$(( 10 - filled ))
    bar=""
    for i in $(seq 1 $filled); do bar="${bar}▪"; done
    for i in $(seq 1 $empty);  do bar="${bar}·"; done

    ctx_segment="${c_blue}ctx ${ctx_color}${remaining_int}%${c_muted} ${bar}"
else
    ctx_segment="${c_muted}ctx —"
fi

# ── Git branch (optional, fast with --no-optional-locks) ────────────────────
git_segment=""
branch=$(git --no-optional-locks -C "$cwd" branch --show-current 2>/dev/null)
if [ -n "$branch" ]; then
    git_segment="${c_muted} ${SEP} ${c_gold} ${branch}"
fi

# ── Assemble the line ────────────────────────────────────────────────────────
printf '%s%s%s' "$c_teal" "$short_cwd" "$RESET"
printf ' %s ' "$SEP"
printf '%s%s' "$ctx_segment" "$RESET"
if [ -n "$git_segment" ]; then
    printf '%s%s' "$git_segment" "$RESET"
fi
printf ' %s ' "$SEP"
printf '%s%s%s' "$c_muted" "$model" "$RESET"
printf '\n'
