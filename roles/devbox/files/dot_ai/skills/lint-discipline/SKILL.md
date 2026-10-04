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
  - pyrefly
  - suppress
  - silence
problem: "Agents suppress lint diagnostics with noqa / nolint / eslint-disable rather than fixing the underlying issue."
related: [code-comments, code-writing-protocols]
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

- Add suppression directives (`// nolint`, `# noqa`, `# type: ignore`, `# pyrefly: ignore`, `@ts-ignore`, `@ts-expect-error`, `eslint-disable`, `@SuppressWarnings`) without explicit user approval
- Use blanket suppressions: `# type: ignore` (must be `# type: ignore[code]`), `# pyrefly: ignore` and `# pyrefly: ignore-errors` (must be `# pyrefly: ignore [error-kind]` — note the space before the bracket, which is what pyrefly itself writes), `// nolint` (must be `// nolint:lintername`), `eslint-disable` (must be `eslint-disable rule-name`)
- Run a tool whose job is to insert suppressions: `pyrefly suppress` and `pyrefly check --suppress-errors` rewrite every erroring line in the source tree with `# pyrefly: ignore [kind]`. One command, hundreds of unreviewed suppressions. Fix the errors instead.
- Suppress import errors from the command line: `pyrefly check --replace-imports-with-any`, `--replace-untyped-imports-with-any`, `--ignore-missing-imports`. These are legitimate as **committed** `[tool.pyrefly]` keys, where "this dependency ships no type information" is a reviewable statement; as ad-hoc flags they make a failing typecheck pass for you and nobody else.
- Suppress a lint error just because fixing it is inconvenient or time-consuming
- Remove or weaken linter configuration files (`.eslintrc`, `.golangci.yml`, `ruff.toml`, `pyproject.toml` lint sections)
- Use `--no-verify` to bypass pre-commit hooks

**Removing a stale suppression is not suppression.** `pyrefly suppress --remove-unused` and `pyrefly check --remove-unused-ignores` delete ignore comments that no longer suppress anything. That is cleanup in the direction this skill wants, and nothing blocks it.

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

## Hook Enforcement Chain

Six hooks enforce lint and type discipline automatically:

1. **`pre-edit-lint-guard`** (PreToolUse) — **BLOCKS** edits that add suppression directives OR lazy typing patterns (`Any`, `any`, `interface{}`). The edit is rejected before it happens.
2. **`pre-bash-suppression-guard`** (PreToolUse:Bash) — **BLOCKS** Bash commands that write suppression directives to files via sed/echo/perl/etc. For the Python type-checker comments it carries both spacings — with and without the space after the colon — so neither the spelling a tool emits nor the one a human types gets through.
3. **`pre-bash-toolchain-guard`** (PreToolUse:Bash) — **BLOCKS** invocations of tools whose function is to suppress rather than to report: `pyrefly suppress`, `pyrefly check --suppress-errors`, and the three `--*imports*` flags that swap an import for `Any`. A command asking only to *remove* unused ignores is exempt.
4. **`post-edit-lint`** (PostToolUse, **synchronous**) — Runs linter after every edit, outputs results via `additionalContext`. You MUST address reported issues before proceeding.
5. **`post-edit-typecheck`** (PostToolUse, async) — Runs type checker (tsc for TS, pyrefly for Python) after edits.
6. **`stop-lint-gate`** (Stop) — Runs linters AND type checkers on all git-modified files before task completion. If any file has lint or type issues, you cannot finish.

**You cannot bypass this chain.** Suppression directives and lazy types are blocked at write time. Bash bypass is guarded, both the hand-written kind and the mass-insertion subcommand. Lint results are synchronous (not hidden). Task completion is gated on clean lint AND clean types.

## Lazy Typing — Blocked Patterns

The `pre-edit-lint-guard` hook blocks lazy typing patterns at write time. These are treated the same as suppression directives — you must use proper types.

### Python — Never Use `Any`

| Blocked | Use Instead |
|---------|-------------|
| `from typing import Any` | Import specific types |
| `: Any` | `: str`, `: int`, `: dict[str, X]`, `: Protocol` |
| `-> Any` | `-> SpecificType`, overloads for multiple returns |

If you genuinely need dynamic typing (e.g., third-party API returning untyped data), ask the user for approval. Prefer `object` or a `Protocol` over `Any`.

### TypeScript — Never Use `any`

| Blocked | Use Instead |
|---------|-------------|
| `: any` | `: unknown` + type guard, or specific type/interface |
| `as any` | `as SpecificType`, fix the type mismatch |
| `<any>` | `<SpecificType>` generic parameter |

### Go — Never Use `interface{}`

| Blocked | Use Instead |
|---------|-------------|
| `interface{}` | `any` (Go 1.18+) for genuine dynamic, or a concrete type/interface |

## Common Fixes (Instead of Suppressing)

| Lint Rule | Lazy Way | Correct Way |
|-----------|----------|-------------|
| unused variable | `_ = x` or `# noqa: F841` | Remove the variable, restructure logic |
| unused import | `# noqa: F401` | Remove the import (unless side-effect — ask user) |
| `any` type (TS) | `// @ts-ignore` | Use `unknown` + type guard or proper typing |
| unchecked error (Go) | `//nolint:errcheck` | Handle the error or use `_ = fn()` with explicit intent |
| many type errors after a refactor | `pyrefly suppress` | Fix them; narrow the run with `pyrefly check --only <error-kind>` to work through one kind at a time |
| untyped third-party import | `pyrefly check --ignore-missing-imports <mod>` | Add the module to `replace-imports-with-any` in `[tool.pyrefly]` so the decision is committed |
| too many arguments | suppress complexity lint | Extract a config/options struct |
| line too long | `# noqa: E501` | Break the line, extract variables |
| missing return type | suppress | Add the return type annotation |

## Recommended Project-Level Linter Config

Configure your project linters to catch lazy patterns at the tool level:

### Python (`pyproject.toml`)

```toml
[tool.ruff.lint]
extend-select = ["ANN"]  # flake8-annotations

[tool.ruff.lint.flake8-annotations]
allow-star-arg-any = false
suppress-none-returning = true

[tool.pyrefly]
preset = "strict"
# The sanctioned home for "this dependency ships no type information". Listed
# here it is reviewable and applies to everyone; passed as a command-line flag
# it is invisible and applies to one invocation.
replace-imports-with-any = ["untyped_dep", "untyped_dep.*"]
```

### TypeScript (`eslint.config.js` / `.eslintrc`)

```json
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unsafe-assignment": "error",
    "@typescript-eslint/no-unsafe-return": "error"
  }
}
```

### Go (`.golangci.yml`)

```yaml
linters-settings:
  govet:
    check-shadowing: true
  revive:
    rules:
      - name: empty-block
```

These rules make the linter catch what the hooks also catch — defense in depth.
