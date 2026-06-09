# Test Strategy — Agent & Skill Redesign

**Status**: Proposal / design ledger. No agent or skill changes applied yet.
**Scope of this iteration**: semantics only — skills and agent bodies. Agent I/O
(structured-output schemas, `plan.md` structure, handoff files) is explicitly
**out of scope** and tracked as a separate future workstream (see "Parked" below).
**Date**: 2026-06-09
**Branch**: `claude/go-agent-test-strategy-VydXm`

## What This Is

The Go development pipeline (`implementation-planner-go` → `software-engineer-go`
→ `unit-test-writer` / `integration-tests-writer-go` → `code-reviewer`) only
knows how to reason about **unit tests**. It has no shared notion of *which kinds
of tests a change actually needs*, no guidance on test **isolation** (mocking
time, randomness, IO) or `t.Parallel()`, and no taught body of **distributed-
systems** design knowledge — even though the reviewer and test writer already
*enforce* distributed patterns the engineer was never given.

This document captures the agreed design for closing those gaps **without
touching agent input/output contracts**.

## Motivating Problems

1. **Test-type blindness.** `unit-test-writer` writes only unit tests.
   Property-based (`pgregory.net/rapid`), fuzzing (`go test -fuzz`), functional,
   and mutation testing are absent. Nothing decides *which* test types a change
   warrants based on scope / invariants / blast radius.
2. **No isolation guidance.** `go-testing` is a 12-line checklist. It says
   nothing about injecting time/randomness/IO for deterministic tests, and
   nothing about `t.Parallel()` — which is both a force multiplier and a
   foot-gun (especially against the mandated testify suites).
3. **Knowledge asymmetry on distributed systems.** The reviewer checks
   "transaction patterns correct (fetch before tx, side effects after commit,
   outbox in same tx)" and the test writer tests "idempotency keys, transactional
   outbox, retry/backoff" — but `go-engineer` teaches none of it. We review and
   test against a standard the implementer never received.
4. **Tautological tests slip through.** A test writer can copy the
   implementation into the test and assert it against itself: green suite, full
   coverage, zero bug-catching power. Only a reviewer looking at test and code
   side by side can catch it. Today this is a single line in the reviewer
   ("no copied implementation logic") with no procedure.
5. **Review ordering rationale is implicit.** The reviewer already runs after
   the test writers, but *why* (tests are an executable behavioural contract and
   a review artefact in their own right) is never stated, and there is no
   checkpoint for **test-strategy adequacy** (were the right kinds of tests
   chosen for the risk?).

## Design Principles (the lens)

1. **Do not touch agent I/O.** Contracts, JSON schemas, `plan.md` structure, and
   handoff files stay structurally unchanged. We change only *semantics*: skills,
   agent bodies, and human-readable reports. I/O redesign is a separate workstream.
2. **Two axes of skills.** Language-idiom skills (`{lang}-engineer`,
   `{lang}-testing`, `{lang}-review-checklist`) hold syntax/tooling/idioms.
   **Cross-cutting concept skills** (like `code-writing-protocols`,
   `lint-discipline`) hold language-agnostic principles. Concepts go in agnostic
   skills; idioms stay in `{lang}-*`.
3. **Cross-role contract = one shared skill, not a new agent.** When a concept is
   *implemented* by SE, *tested* by the test writer, and *verified* by the
   reviewer, it must have a single source of truth all three read — otherwise the
   three drift (exactly the distributed-systems asymmetry above).
4. **Derive facts; ask only for intent.** Symbol-level changesets (which
   functions/types/methods were added/removed/moved, and where) are derivable
   deterministically from `git diff` + LSP/AST. Do not ask SE to self-declare a
   manifest — it is redundant and unverifiable (the whole reason the reviewer
   exists is that SE output cannot be trusted on its word). Intent/invariants/
   blast-radius *are* the engineer's to state, and SE already emits them
   (`invariants_implemented`, `autonomous_decisions` in `se_go_output.json`).
5. **Graceful degradation by tiers.** Test-strategy reasoning works at three
   input richness levels: explicit strategy (future planner) → existing
   `Test Mandate` (read as-is) → diff-only. The diff-only tier is needed anyway,
   because many runs have no plan.
6. **Conditional loading by concern-signal, not language.** Cross-cutting skills
   load when the *concern* is present in the diff (a transaction, a queue publish,
   external IO near a state write, ambient non-determinism), not based on which
   language was detected.

## Proposals

| # | Proposal | Change type | Consumers | Loading |
|---|----------|-------------|-----------|---------|
| A | **`test-strategy` skill** — decision matrix "signal in code → test type" (rapid / fuzz / integration / functional; when each) | new agnostic concept skill | test-writer planning phase, reviewer | concern-signal |
| B | **Expand `go-testing`** (currently 12 lines): isolation/determinism, `t.Parallel()` decision guide + foot-guns, property-based (rapid), fuzzing | extend language-idiom skill | unit/integration writer, reviewer | go stack |
| C | **Isolation/determinism skill** — seams for time / randomness / uuid / IO; principles agnostic | new agnostic concept skill | SE (implements), test-writer (reports missing seam back), reviewer | concern-signal |
| D | **`distributed-patterns` skill** — tx boundaries, no IO inside tx, at-least/at-most/exactly-once, outbox, idempotency, retry/backoff | new agnostic concept skill | SE, both test writers, reviewer | concern-signal |
| E | **Anti-tautology checkpoint** — expand the one-line "no copied implementation logic" into a procedure with triggers | extend reviewer + checklist | reviewer | always |
| F | **Review-after-tests rationale + test-strategy adequacy checkpoint** — state explicitly that the test suite is a review precondition and an artefact; add a checkpoint that the *kinds* of tests match blast radius | `code_reviewer` body | reviewer | always |
| G | **Strengthen the test-writer's existing planning phase** (Step 4) with skill A + derived symbol-level delta from diff/LSP — instead of a new intermediate agent | `unit_tests_writer` body | test-writer | always |
| H | **Mutation testing (gremlins)** as a reviewer/CI gate for high-risk packages — *not* a writer task | reviewer / checklist | reviewer | high-risk |
| I | **Functional/behavioural mode** for `integration_tests_writer_go` | agent body | integration writer | concern-signal |

C and E are instances of principle 3 (cross-role contract = shared skill).
A / C / D / E are agnostic concepts; only their idioms live in `{lang}-*`.

### Detail notes

**A — test-strategy decision matrix (signal → test type).**
- pure functions over large input spaces; encode/decode or parse/serialise pairs;
  round-trip / idempotence / commutativity / monotonicity / ordering invariants
  → **property-based (rapid)**;
- parsing of untrusted/structured input, security surface → **fuzzing**;
- state machines / complex state transitions → **rapid state-machine tests**;
- crossing a process/IO boundary (DB / HTTP / queue) → **integration**;
- high blast radius / critical path / uncertainty about test-suite strength
  → **mutation as a gate**;
- simple CRUD glue → plain table-driven unit.

**B — isolation & `t.Parallel()`.**
- *Isolation*: inject `Clock`/`now()`; never raw `time.Now()`/`time.Sleep`/
  `time.After` in logic under test. Seed/inject randomness; `t.TempDir`,
  `t.Setenv`; no real network/FS/global state.
- *`t.Parallel()` foot-guns to spell out*: `t.Setenv` panics under
  `t.Parallel()`; loop-variable capture in subtests (needs `tt := tt` on Go
  < 1.22, fixed on ≥ 1.22 — version-dependent on `go.mod`); shared mutable
  fixtures race between parallel subtests (each needs an isolated resource — own
  DB schema / own temp dir); use `t.Cleanup` not `defer` for shared resources
  (the outer function returns before parallel children run); **conflict with
  testify suites** — suite methods share state and `SetupTest`/`TearDownTest`
  are not parallel-safe, so `s.T().Parallel()` inside suite methods is dangerous
  without isolation. When parallel pays: I/O-bound tests, integration with
  independent containers, large independent table cases. When it does not: tiny
  fast units (overhead > benefit), shared fixtures, order-dependent tests.

**C — testability contract (cross-role).**
SE owns providing seams for ambient non-determinism (time/rand/uuid/IO). The
test writer's existing `ut_output.json.issues_raised → addressed_to:
software-engineer` is the return path when a seam is missing. **Tight
limiter**: this is *not* "interface everything" — the codebase prefers concrete
types and minimal interfaces (`go-testing`: "concrete types with test setup >
test-local interface > adapter; mock interface only if slow/external"; reviewer
Checkpoints O/F penalise over-export and complexity). Seams go *only* where
non-determinism is otherwise unbeatable.

**D — distributed-patterns (cross-role, agnostic).**
Same problems exist in Python (SQLAlchemy) and any other language, so the *skill
carries concepts/invariants/checklist only* — no `pgx.Tx` snippets. The agent
maps concept → idiom from knowledge it already has (the `go-testing` stance:
"you already know the tools; this skill sets the system's expectations"). The
existing "Distributed Systems" fragment in `go-review-checklist` becomes a thin
pointer to this skill rather than a duplicate.

**F — review ordering.** Keep the order (reviewer after tests — it already is);
do **not** add a second full review pass before tests (Fast Review mode +
`build-resolver-go` + SE self-review already cover "fix fundamentals first").

**G — no intermediate agent yet.** The precise "which file, which function,
which invariant → which test" mapping can only be made *after* SE writes code
(the planner plans before code exists). But that reasoning already lives inside
`unit-test-writer` Step 3 (reads invariants) + Step 4 (test plan) + Step 5
(bug-hunting). Strengthen it there with skill A and a diff/LSP-derived symbol
delta. A standalone test-planner agent is a *later* graduation — justified only
when (a) several writers need the same plan computed once, or (b) the reviewer
verifies "was the plan executed?" — and both imply a new structured artefact,
i.e. an I/O change (parked).

## Research notes (mutation / property-based)

- **rapid vs fuzzing is not either/or.** rapid = fast feedback loop on invariants
  during development; great at complex structured data and state-machine tests.
  Fuzzing = slow, coverage-guided edge-case/security search. A rapid test can be
  reused as a fuzz target via `rapid.MakeFuzz`.
  ([rapid](https://github.com/flyingmutant/rapid),
  [Go Fuzzing](https://go.dev/doc/security/fuzz/))
- **Mutation testing in Go.** [`gremlins`](https://github.com/go-gremlins/gremlins)
  is the practical pick — good on smallish modules / microservices and as a CI
  quality gate, but a run can take hours on large code bases, so apply it
  point-wise to high-risk packages. Alternatives:
  [`ooze`](https://github.com/gtramontina/ooze),
  [`avito-tech/go-mutesting`](https://github.com/avito-tech/go-mutesting).
  Mutation testing is **not a kind of test** — it is a meta-tool that scores the
  strength of the existing suite, so it belongs to the reviewer / CI gate, not to
  a test writer.

## Parked — I/O workstream (separate, deliberately deferred)

- Richer SE output (symbol-level manifest, richer invariants) — derive the facts
  from diff instead; any structured manifest is an I/O change.
- Planner emitting an explicit "Test Strategy" section or a wider `Test Type`
  vocabulary into its output.
- Standalone **test-planner agent** + its structured "test plan" artefact — to be
  graduated when multiple writers share it or the reviewer verifies against it.
- New fields in `ut_output.json` / `cr_output.json` / `se_go_output.json`.

When the I/O workstream lands, the explicit Test Strategy simply layers on top as
Tier 1 of principle 5 (it does not replace the diff-only tier).

## Open decisions (owner: user)

- **Scope of the first implementation iteration** — which test types to add now
  (rapid / fuzz / functional / mutation).
- **Final home of the strategy "brain"** — skill + planner vs standalone agent vs
  inside the writer (current lean: skill + writer's planning phase; agent later).
- **Rollout mode** — apply edits directly vs produce per-file diffs for review
  first.

## When Picking This Up

1. Decide the open questions above.
2. Author the agnostic concept skills (A, C, D) — concepts/invariants/checklist
   only, no language idioms.
3. Expand `go-testing` (B) with the isolation + `t.Parallel()` + rapid + fuzzing
   sections.
4. Edit agent bodies (E, F, G, H, I) and add the new skills to the relevant
   `skills:` frontmatter lists.
5. Run `make validate-claude` (agent/skill cross-references) and
   `make validate-skills`.
6. Add `trigger_evals.json` for the new skills where conditional loading matters.
