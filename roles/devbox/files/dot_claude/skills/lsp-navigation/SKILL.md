---
name: lsp-navigation
description: >
  Enforces LSP-first code navigation. Grep discovers files and text.
  LSP understands code. This skill ensures agents use the right tool for the job.
alwaysApply: true
---

# Code Navigation: Grep Discovers, LSP Understands

## Tool Selection

| Need | Tool | NOT |
|------|------|----|
| Find a symbol definition | LSP `workspaceSymbol` or `goToDefinition` | Grep |
| All callers/usages of a symbol | LSP `findReferences` | Grep |
| Type signature or docs | LSP `hover` | Read entire file |
| File structure overview | LSP `documentSymbol` | Read entire file |
| Interface implementations | LSP `goToImplementation` | Grep |
| Call hierarchy | LSP `incomingCalls` / `outgoingCalls` | Manual tracing |
| Text in comments/strings/logs | Grep | LSP |
| Config/YAML/JSON/env files | Grep / Read | LSP |
| File discovery by name | Glob | LSP |

## Mandatory Rules

1. **No modifying unfamiliar code without `goToDefinition` first** — understand before changing
2. **No refactoring without `findReferences`** — know the blast radius before renaming or changing signatures
3. **No claiming success without checking LSP diagnostics** — fix all type errors and missing imports after every edit
4. **Never Grep for function definitions** — use `workspaceSymbol` (by name) or `documentSymbol` (by file)

## When LSP Fails

LSP returns "No server available" → retry once (cold start). Still fails → fall back to Grep, flag reduced accuracy. See `lsp-tools` skill for full error handling, coordinate bridge patterns, and language-specific notes.
