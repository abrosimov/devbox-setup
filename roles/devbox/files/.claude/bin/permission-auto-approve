#!/bin/sh
# permission-auto-approve — PermissionRequest hook that auto-approves safe operations.
#
# Fires when a permission dialog would appear AFTER sandbox + allow/deny rules.
# Reads JSON from stdin, outputs hookSpecificOutput JSON to auto-approve or falls through.
#
# Safety layers (in order):
#   1. settings.json deny rules → hard block (never reaches this hook)
#   2. settings.json allow rules → auto-approved (never reaches this hook)
#   3. Sandbox auto-allow → auto-approved for sandboxed bash (never reaches this hook)
#   4. THIS HOOK → catches remaining edge cases with known-safe patterns
#   5. User prompt → anything not caught above asks the user
#
# Exit 0 with no output = fall through to user prompt.
# Exit 0 with JSON = apply the decision (allow/deny).

set -e

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(printf '%s' "$INPUT" | jq -r '.tool_input // empty')

# --- Auto-approve: Bash commands that are safe but might escape sandbox allow rules ---
if [ "$TOOL_NAME" = "Bash" ]; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')

  # Auto-approve common read-only / diagnostic commands that might not match allow patterns
  case "$CMD" in
    echo\ *|printf\ *|'echo'|'printf')
      # Plain echo/printf with no redirection (redirection blocked by deny rules)
      case "$CMD" in
        *'>'*|*'|'*) ;; # contains redirection or pipe — fall through to user
        *)
          printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
          exit 0
          ;;
      esac
      ;;
    type\ *|command\ -v\ *|hash\ *)
      # Command existence checks — read-only
      printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
      exit 0
      ;;
    id|id\ *|whoami|hostname|uname\ *|uname|arch|sw_vers*)
      # System info — read-only
      printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
      exit 0
      ;;
    tput\ *|stty\ *|locale|locale\ *)
      # Terminal/locale queries — read-only
      printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
      exit 0
      ;;
  esac

  # --- Auto-approve: commands prefixed with `cd /path &&` ---
  # Agents often generate: cd /path/to/project && go build ./...
  # The bare command (go build) matches allow rules, but the cd prefix breaks glob matching.
  # Normalize by stripping the cd prefix, then check against known-safe command families.

  NORMALIZED="$CMD"

  # Strip leading: cd <path> && (with optional quotes around path)
  NORMALIZED=$(printf '%s' "$NORMALIZED" | sed -E 's/^cd[[:space:]]+[^&]+&&[[:space:]]*//')

  # Strip leading env var assignments: VAR=value VAR2=value ...
  while printf '%s' "$NORMALIZED" | grep -qE '^[A-Z_][A-Z0-9_]*='; do
    NORMALIZED=$(printf '%s' "$NORMALIZED" | sed -E 's/^[A-Z_][A-Z0-9_]*=[^[:space:]]*[[:space:]]*//')
  done

  # Strip trailing 2>&1
  NORMALIZED=$(printf '%s' "$NORMALIZED" | sed -E 's/[[:space:]]*2>&1[[:space:]]*$//')

  # If normalization changed anything AND the core command is safe, approve it
  if [ "$NORMALIZED" != "$CMD" ]; then
    SAFE=0
    case "$NORMALIZED" in
      go\ build*|go\ test*|go\ vet*|go\ mod*|go\ get*|go\ install*|go\ generate*|go\ run*) SAFE=1 ;;
      goimports*|golangci-lint*|mockery*|sqlc*) SAFE=1 ;;
      uv\ *|uvx\ *|pytest*|ruff\ *|mypy\ *|python\ *|python3\ *) SAFE=1 ;;
      npm\ *|npx\ *|pnpm\ *|node\ *) SAFE=1 ;;
      make\ *|make) SAFE=1 ;;
      cargo\ *|rustc\ *) SAFE=1 ;;
    esac

    if [ "$SAFE" = "1" ]; then
      # Reject if normalized command contains shell metacharacters
      case "$NORMALIZED" in
        *'&&'*|*'||'*|*'|'*|*';'*|*'$('*|*'`'*) ;; # contains chaining — fall through
        *)
          printf '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}\n'
          exit 0
          ;;
      esac
    fi
  fi
fi

# --- Everything else: fall through to the standard permission prompt ---
exit 0
