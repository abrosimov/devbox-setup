---
name: response-templates
description: Reply templates for the end of a turn — T1 final report with "Decisions I made", T2 decision card (3–7 candidates with trade-offs), T3 "What I need from you" block with the ai/scripts home for agent-written scripts and Python/Go script templates, T4 discussion ledger for multi-turn lists. Use when writing a final report, presenting options or alternatives, handing a manual step, command, or script to the user, or tracking a numbered list across turns.
version: 1
triggers:
  - final report
  - what I need from you
  - decision card
  - options
  - candidates
  - trade-offs
  - ai/scripts
  - agent-written script
  - manual step
  - ledger
alwaysApply: false
problem: "End-of-turn replies bury the outcome, hide the user's actions mid-message, hand over long manual command sequences, and let discussed list items drift or vanish."
related: [diverge-synthesize-select, writing-for-the-reader, agent-communication]
---

# Response Templates

Four shapes for the replies the shared core (§2, §4, §5) asks for. Each exists because the user reads
many threads at once and returns to a reply cold: the shape tells them where the outcome, the choice,
and their own work live without reading everything.

## T1 — Final report

Order: outcome, supporting detail, answer to any question asked alongside the work, one-line status of
every open list ID (only while a list is under discussion), then "Decisions I made" — one line per
design choice or assumption you took, with its reason and how to reverse it — and finally "What I
need from you" (T3) as the last `##` section. Omit either section when it would be empty; T3 appears
only when work is genuinely blocked on the user.

Why: the first sentence is what the user reads on return, so it states what happened. Decisions are
listed rather than asked, so the user keeps authority through a cheap veto instead of an approval
round. Their actions come last and always in the same place, so they never scan for them.

```markdown
Staging now receives the nightly metrics dump; the first run at 02:00 wrote 1 412 rows.

- `jobs/metrics_dump.py:48` — target switched from `prod-ro` to `staging-rw`.
- Retry policy unchanged (3 attempts, 5 min apart).

You asked whether this touches the reporting dashboard: no — it reads from `prod-ro`, which is unchanged.

Open: G2 — rotate the staging token (waiting for you) · G3 — alert on empty dump (decided, next turn).

## Decisions I made

- Kept the 02:00 schedule rather than moving it after the ETL run: the dump reads raw tables, not ETL
  output. To change it, edit `jobs/schedule.yml:12`.

## What I need from you

1. **Rotate the staging write token**, because the old one is in the leaked CI log.
   Run: `uv run ai/scripts/rotate-staging-token/main.py`
   Verify: the script ends with `VERIFY OK`.
```

In a Russian conversation the sections are headed `## Решения, которые я принял` and
`## Что нужно от вас`.

## T2 — Decision card

Use it when the core's threshold holds: the user asked for options, or the candidates differ in what
the user gets and the conversation does not settle the choice. Otherwise pick in your own reasoning and
report the pick with its reason in a line.

Shape, one card per problem:

1. The problem, restated in one line, and the recommendation with its reason.
2. 3–7 candidates, including a boring baseline and at least one combination.
3. A table: candidate, mechanism, pros, cons, combines with.
4. Synergies — which candidates strengthen each other.
5. Trade-offs — what each direction gives up.

Unless the user asked for options or the choice passes the core's §1 stop list, take the
recommendation, continue the work, and close the card with one line saying how to switch.

Why: a first idea compared against nothing is rarely the best one; the baseline shows what doing
little costs, and the combination row catches the answer that is better than any single candidate.
Present candidates with trade-offs — the reader needs the comparison, not a narration of how you got
there. `diverge-synthesize-select` covers generating genuinely different candidates.

```markdown
**D1 — cache invalidation for product prices.** Prices change in the admin panel but the shop shows
stale values for up to an hour. Recommendation: A+C — stale reads disappear without a new service to
operate.

| Candidate | Mechanism | Pros | Cons | Combines with |
|---|---|---|---|---|
| A — shorter TTL (baseline) | TTL 60 min → 5 min | one-line change | 12× more DB reads | C |
| B — event purge | admin save publishes `price.changed`; cache deletes key | instant | new consumer to run | C |
| C — versioned keys | key includes `price_version` | no stale reads | old keys linger until TTL | A, B |
| A+C | versioned keys, 5 min TTL | stale-free, bounded memory | touches both read and write paths | — |

Synergies: C removes staleness; A bounds the memory C leaves behind.
Trade-offs: B is fastest but adds a running component; A+C adds none.
Implemented A+C; say "B" to switch to event purge instead.
```

## T3 — "What I need from you"

Automate first. If you can do the step within your permissions, do it. Hand over only what blocks the
work and needs the user: their credentials, elevated privileges, a GUI action, or an answer that
passed the core's §1 stop list — every handed-over step is time and a chance of a typo. A decision
you can make is not an item; it belongs in "Decisions I made".

Each item carries:

- **what + why**, self-contained — readable without the rest of the thread;
- **the exact command or script invocation**;
- **how to verify** the result.

Size rule: one single-line command may sit inline in a fenced block. Anything longer becomes a script.

### Where agent-written scripts live

Every script an agent writes — a step handed to the user, a probe, a one-off check — lives in one
engine-neutral home, committed with the rest of the work, so it is reviewable, rerunnable and
versioned:

- `ai/scripts/<slug>/` at the repository root holds the script, its test when it has logic, and a
  short `README.md` saying what the script does and why it exists.
- `ai/scripts/README.md` is the index: one line per script, its slug and its purpose. Add the line
  in the same change that adds the script.
- Never `$TMPDIR`, an engine-specific directory or an unlisted path: the OS may purge `$TMPDIR`, and
  a script no one can find cannot be reviewed or rerun.

| Repository root has | Language | Files | Run | Test |
|---|---|---|---|---|
| `go.mod` | Go | `main.go`, `main_test.go`, `README.md` | `go run ./ai/scripts/<slug>` | `go test ./ai/scripts/<slug>` |
| no `go.mod` | Python | `main.py` (PEP 723 inline metadata), `test_main.py`, `README.md` | `uv run ai/scripts/<slug>/main.py` | `uv run --with pytest pytest ai/scripts/<slug>` |

Never shell scripts: quoting, error handling, and portability between macOS and Linux fail silently in
shell, and they cannot be unit-tested in the same way.

Script conventions:

- **Idempotent** — a second run plans nothing and changes nothing.
- **`--dry-run`** — prints the plan and exits without side effects.
- **Prints what it will do** before doing it.
- **Ends with a verification result** (`VERIFY OK` / `VERIFY FAILED`) and a non-zero exit on failure.
- **Tested when it has logic** — branches, parsing, loops, API calls. A pure sequence of commands may
  skip the test.

Start from the skeletons in `templates/python/` and `templates/go/`: a pure `plan` function (unit
tested), an `execute` step, a `verify` step, and the flags above. Show the user how to run the test.

```markdown
## What I need from you

1. **Grant the deploy bot read access to the `billing` schema**, because the nightly export now reads
   invoices and only a database owner can grant it.
   Preview: `uv run ai/scripts/grant-billing-read/main.py --dry-run`
   Apply: `uv run ai/scripts/grant-billing-read/main.py`
   Verify: the last line reads `VERIFY OK: deploy_bot can SELECT billing.invoices`.
   Test: `uv run --with pytest pytest ai/scripts/grant-billing-read`
2. **Click "Allow" on the macOS firewall prompt for `otelcol`**, because only a GUI click can grant
   incoming connections and the collector cannot receive telemetry without it.
   Verify: `curl -fsS localhost:13133` prints `{"status":"Server available"}`.
```

## T4 — Discussion ledger

For lists longer than about five items or threads that run over many turns, keep
`.hermetic/state/ledger-<topic>.md` in the current worktree and re-read it before every reply.
Memory of a long thread drifts; the file does not. Never use `$TMPDIR` for it: the OS may purge it
between sessions. `.hermetic/` is excluded by the global git ignore and is never committed.

A session that picks the ledger up later checks it against the current tree first: it records what
was true when it was written, not what is true now.

```markdown
# Ledger — checkout redesign

Branch: checkout_redesign · created 2026-11-02 · last touched 2026-11-16

| ID | Name | Status | Decision / notes |
|---|---|---|---|
| C1 | Guest checkout | decided | email only; account offered after payment |
| C2 | Saved cards | open | waiting for the payment provider's tokenisation answer |
| C3 | Address autocomplete | dropped: provider cost exceeds benefit | — |
| C4 | Order summary sidebar | open | two layouts under review |
```

Rules, so the user can trust that nothing moved or vanished:

- Every ID is paired with its name wherever it appears ("C2 — saved cards").
- Never renumber, reorder, or merge. A removed item stays, marked `dropped: <reason>`.
- A new item takes the next free ID, even if earlier ones were dropped.
- Update the file in the same turn a status changes, and close the reply with the one-line status of
  every open ID (T1).
