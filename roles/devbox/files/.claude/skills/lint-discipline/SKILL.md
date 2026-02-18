---
name: lint-discipline
description: Lint discipline rules — agents must fix lint issues, never suppress them with directives like noqa, nolint, or eslint-disable.
version: 1
triggers:
  - lint
  - linter
  - noqa
  - nolint
  - eslint-disable
  - ts-ignore
  - type: ignore
  - suppress
  - silence
alwaysApply: true
---

# Lint Discipline

**Agents MUST fix lint issues, not suppress them.**

## Fix Hierarchy (in order of preference)

1. **Fix the code** — change the implementation so the lint rule passes
2. **Refactor to avoid the pattern** — restructure if the fix is non-trivial
3. **Ask the user** — explain the issue and why fixing is hard; wait for guidance
4. **Suppress with user approval** — ONLY after user explicitly says "suppress it" or "add noqa"

Steps 1-2 are the agent's responsibility. Step 3 is mandatory before step 4.

## Suppression Rules

### Never Do (agent MUST NOT, under any circumstances)

- Add suppression directives (`// nolint`, `# noqa`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `@SuppressWarnings`) without explicit user approval
- Use blanket suppressions: `# type: ignore` (must be `# type: ignore[code]`), `// nolint` (must be `// nolint:lintername`), `eslint-disable` (must be `eslint-disable rule-name`)
- Suppress a lint error just because fixing it is inconvenient or time-consuming
- Remove or weaken linter configuration files (`.eslintrc`, `.golangci.yml`, `ruff.toml`, `pyproject.toml` lint sections)
- Use `--no-verify` to bypass pre-commit hooks

### When User Approves Suppression

If the user explicitly approves suppression, follow these rules:

1. **Be specific** — target the exact rule, never blanket-suppress:
   ```go
   //nolint:errcheck // user approved: return value intentionally unused in fire-and-forget call
   ```
   ```python
   import side_effect_module  # noqa: F401 — imported for side effects
   ```
   ```typescript
   // eslint-disable-next-line @typescript-eslint/no-explicit-any -- user approved: third-party API returns untyped data
   ```

2. **Use narrowest scope** — prefer line-level over block-level over file-level
3. **Add justification comment** — explain WHY the suppression is necessary
4. **Prefer `@ts-expect-error` over `@ts-ignore`** — it auto-expires when the underlying issue is fixed

### Existing Suppressions

- Do NOT remove suppression directives you didn't add (they were presumably approved)
- Do NOT modify existing suppressions unless fixing the underlying issue
- If fixing code makes a suppression unnecessary, remove both the fix target and the directive

## What to Do When Lint Fails

```
Lint error reported
    │
    ├─ Can I fix the code? ──────── YES → Fix it. Done.
    │
    ├─ Can I refactor around it? ── YES → Refactor. Done.
    │
    ├─ Is this a false positive? ── MAYBE → Explain to user, show the code,
    │                                        describe why the linter flags it,
    │                                        ask: "Should I fix differently or
    │                                        suppress this specific rule?"
    │                                        WAIT for response.
    │
    └─ I'm stuck ────────────────── Tell the user: "I can't resolve this lint
                                     issue. Here's what I tried: [attempts].
                                     How would you like to proceed?"
                                     WAIT for response.
```

## Common Fixes (Instead of Suppressing)

| Lint Rule | Lazy Way | Correct Way |
|-----------|----------|-------------|
| unused variable | `_ = x` or `# noqa: F841` | Remove the variable, restructure logic |
| unused import | `# noqa: F401` | Remove the import (unless side-effect — ask user) |
| `any` type (TS) | `// @ts-ignore` | Use `unknown` + type guard or proper typing |
| unchecked error (Go) | `//nolint:errcheck` | Handle the error or use `_ = fn()` with explicit intent |
| too many arguments | suppress complexity lint | Extract a config/options struct |
| line too long | `# noqa: E501` | Break the line, extract variables |
| missing return type | suppress | Add the return type annotation |
