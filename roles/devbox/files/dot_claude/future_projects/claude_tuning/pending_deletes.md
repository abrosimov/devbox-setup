# Pending Deletes — Claude Tuning W2

Deletes deferred to user action (Claude cannot run `rm` under current permissions). Run these locally after visual review; each is safe and reference-free at time of listing.

## From W2 Phase 1a (LSP merge)

- `roles/devbox/files/dot_claude/skills/lsp-navigation/SKILL.md` — content fully covered by `skills/lsp-tools/SKILL.md`; UAP updated to point only at `lsp-tools`; no agent's `skills:` list references `lsp-navigation`.
- `roles/devbox/files/dot_claude/skills/lsp-navigation/` — the containing directory (empty after the file above is removed).

Suggested one-liner:
```
rm roles/devbox/files/dot_claude/skills/lsp-navigation/SKILL.md \
  && rmdir roles/devbox/files/dot_claude/skills/lsp-navigation
```

After delete: re-run `make rules-budget` — expect always-on flat drop from 119 to 115 (−4 rules from `lsp-navigation`).
