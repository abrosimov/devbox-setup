---
name: go-engineer
description: Write, modify, debug, and refactor idiomatic production Go code. Use when implementing Go services, handlers, APIs, packages, interfaces, error handling, concurrency, middleware, migrations, or other changes to .go files while preserving repository conventions and validating the result.
---

# Go Engineer

Implement the requested Go change within the user's scope and the repository's local instructions.
Treat repository conventions as authoritative when they differ from general Go preferences.

## Workflow

1. Read the nearest `AGENTS.md`, `go.mod`, task-specific instructions, and relevant implementation
   plans or design documents. Do not assume Jira, a particular branch naming convention, or a fixed
   plans directory; use context supplied by the caller or discover repository-local artifacts.
2. Trace the affected call paths, interfaces, tests, configuration, and public consumers before editing.
   Check references before changing exported names, interfaces, or function signatures.
3. For a multi-file or uncertain change, assess the existing branch with the bundled
   `scripts/complexity_check.sh`. Resolve the directory containing this `SKILL.md` rather than assuming
   the skill is in the current working directory. A `high` result calls for an explicit implementation
   sequence, broader call-path inspection, and stronger validation; it does not select a vendor model.
4. Implement the smallest coherent change that satisfies the request. Preserve domain language and
   compatibility unless the task explicitly changes them.
5. Add or update tests for changed behaviour unless testing is explicitly assigned elsewhere or excluded
   from scope. Use `go-testing` when it is available and relevant.
6. Format and validate using the repository's own commands. Start with checks closest to the changed
   package, then broaden in proportion to risk.
7. Review the final diff for accidental scope expansion, generated-file drift, weak error handling,
   concurrency leaks, and unrelated user changes.

## Implementation Principles

- Keep APIs and interfaces as small as their consumers permit. Define interfaces at the point of use.
- Wrap errors with useful operation or entity context while preserving the cause with `%w` when callers
  may inspect it. Prefer `errors.Is` and `errors.As` over string matching.
- Thread `context.Context` through blocking or request-scoped operations. Do not store it in structs.
- Give every goroutine an explicit lifetime, cancellation path, and ownership model. Avoid starting
  background work that cannot be stopped or observed.
- Validate data at trust boundaries. Do not add speculative nil checks or abstractions that conflict with
  established package invariants.
- Close resources on every path and make retry behaviour bounded, observable, and safe for the operation.
- Follow the repository's logging package and field conventions; do not introduce a logger merely because
  a generic checklist mentions one.
- For schema changes, read the repository's migration plan. Keep application code compatible across the
  expand/deploy/contract window and do not depend on a contract migration having already run.
- Use comments only to explain non-obvious constraints or decisions. Prefer clear names and structure over
  narration.

## Toolchain and Sandbox

Do not assume that the active AI client has preconfigured Go cache or toolchain variables. Inspect the
actual repository and environment when a command fails:

```bash
go version
go env GOCACHE GOMODCACHE GOTOOLCHAIN
```

Report the concrete failure: toolchain mismatch, unavailable dependency download, permissions, compile
error, test failure, or linter failure. Respect the active sandbox and approval policy; do not silently
change global Go settings or install a toolchain to bypass it.

Prefer project wrappers and documented targets. When the repository provides no stronger convention, use
the applicable subset of:

```bash
go test ./path/to/changed/package/...
go test ./...
go test -race ./...
go vet ./...
```

Always format changed Go source with `goimports -local <module-path>`, obtaining the module path from the
module directive in `go.mod`. Use a repository-owned formatting command only when it preserves that policy.
Do not use `go fmt` or `gofmt`, and do not format unrelated files merely because the formatter accepts a
package-wide target. Run `golangci-lint` only when the repository configures or documents it; do not assume
every Go project uses it.

## Completion

Return a concise hand-off covering changed behaviour, files touched, validation performed, and residual
risks or checks that could not run. Do not prescribe a client-specific slash command or a particular
model as the next step.
