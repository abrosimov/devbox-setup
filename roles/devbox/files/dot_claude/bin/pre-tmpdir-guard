#!/bin/sh
# pre-tmpdir-guard — blocks writes to /tmp/ and /var/tmp/, redirects to project-local tmp/
#
# Called as PreToolUse hook for Bash and Write tools.
# Env: CC_BASH_COMMAND, CC_TOOL_INPUT_FILE_PATH
# Exit 2 to block, 0 to allow.

blocked=false

# Check Bash commands for /tmp/ or /var/tmp/ paths
case "$CC_BASH_COMMAND" in
  */tmp/*|*/var/tmp/*) blocked=true ;;
esac

# Check Write tool file path
case "$CC_TOOL_INPUT_FILE_PATH" in
  /tmp/*|/var/tmp/*) blocked=true ;;
esac

if [ "$blocked" = true ]; then
  # Find project root
  root=$(git rev-parse --show-toplevel 2>/dev/null) || root="$PWD"

  # Auto-create project-local tmp/
  mkdir -p "$root/tmp"

  # Ensure .gitignore covers tmp/
  gi="$root/.gitignore"
  if [ -f "$gi" ]; then
    grep -qx 'tmp/' "$gi" 2>/dev/null || printf '\ntmp/\n' >> "$gi"
  else
    echo 'tmp/' > "$gi"
  fi

  echo "BLOCKED: Do not use /tmp/ or /var/tmp/. Use $root/tmp/ instead (project-local). The directory has been auto-created and added to .gitignore." >&2
  exit 2
fi

exit 0
