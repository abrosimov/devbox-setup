# Case study: optimising a GitHub Actions pipeline

A private infrastructure repository (Ansible roles, a Python task runner, VM-based lifecycle
tests) on GitHub-hosted 2-vCPU runners. The numbers are from its recorded runs; names are
generalised.

## Contents

- [Starting point](#starting-point)
- [Problem 1: runs that "reset" near the end](#problem-1-runs-that-reset-near-the-end)
- [Problem 2: the static job runs everything](#problem-2-the-static-job-runs-everything)
- [Problem 3: light and heavy jobs in one fan-out](#problem-3-light-and-heavy-jobs-in-one-fan-out)
- [A regression the step acceptances missed](#a-regression-the-step-acceptances-missed)
- [What the confirmation runs found](#what-the-confirmation-runs-found)
- [Before and after](#before-and-after)
- [Lessons](#lessons)

## Starting point

- One `static` job of about 30 minutes ran every check (unit tests, Ansible syntax and lint,
  component suites) for every change.
- Eight optional jobs, light (1 to 9 min) and heavy (15 to 40 min, VM guests), all needed
  `quick` and `static` and started together.
- Every blocking job ended with a fail-fast step that ran `gh run cancel` on failure.
- `concurrency` with `cancel-in-progress: true` for every event.
- The owner's hypotheses: test collection dominates the component steps; one playbook runs twice.

## Problem 1: runs that "reset" near the end

**Evidence.** 107 runs ended `cancelled` in three weeks, many after 30+ minutes with nearly every
job green and only the gate red.

**Classification** (step and annotation data from the jobs API; logs were unreachable):

| Mechanism | Runs |
|---|---|
| Self-cancel by the fail-fast step | 82 |
| Concurrency supersession (one of them a 65-minute default-branch run cancelled by the next merge) | 22 |
| Timeout, manual, platform | the rest; residue 0 |

- The failing job showed `cancelled`: its own cancel step had relabelled it. Its failed step was
  the real error.
- A first classifier counted only cancel steps that ended `success` and missed 28 of the 82,
  because the failing job's cancel step itself ends `cancelled`.
- A dependency bot rebasing every open pull request on each merge restarted CI with the same diff
  on a new parent: the largest minute sink, and a policy trade-off left to the owner.

**Changes.** `cancel-in-progress` only for pull requests, schedules in their own group; cancel
steps kept only where they save minutes (about 94 % of the saving), announced with an error
annotation and a summary line, and removed from the job that usually finishes last.

## Problem 2: the static job runs everything

**Rivals carried.** (a) The planner selects everything; (b) CI ignores the plan (no `if:` on
steps).

**Discriminating measurement.** Replaying the planner over the last 30 default-branch commits:
27 selected every stage. A central pin file read by every check selected everything at path
granularity. (b) was real but would have skipped one stage in 3 of 30 commits: minor.

**Changes.** Finer selection with fail-closed fallbacks (no base, parse error, toolchain or
classifier change, unclassified path select everything); the static stage fanned out into 16
legs from a dynamic matrix with an empty-list guard; one strict static aggregate that checks
each selected leg left exactly one receipt.

## Problem 3: light and heavy jobs in one fan-out

**Measurement.** Light jobs failed after 0.2 to 8.8 minutes, and their fail-fast step then killed
heavy jobs that had already run for 10+ minutes. Light jobs already started within 2 s of their
prerequisite; runner contention was rejected because no first-attempt start offset exceeded
12 s. The largest failure cost, a heavy job's own defect (about 850 job-minutes), was out of reach
of any ordering.

**Tier rule.** p90 of successful durations ≤ 10 min and no VM guest means light.

**Change.** Heavy jobs need the light jobs; a light `skipped` is accepted only when that light job
was not selected. Replayed on recorded runs: successful heavy runs delayed by 0.0 min; the cheap
failure signal moved from 14.6 to 1.8 min after run start. An image-security scan that outlasted
static and whose output no heavy job read left the heavy prerequisites but stayed in the gate.

**Refuted hypotheses.**

- "Collection dominates": `--collect-only` took 1.3 s for 5314 items; the 25 s step spent its time
  in about 13 `ansible-playbook` processes at 1.5 to 2 s each.
- "The playbook runs twice": every invocation recorded with path and phase; no overlap. The cost
  was about 120 short serial processes (308 s).

## A regression the step acceptances missed

Each implementation step passed acceptance on its own files, yet the unit job went from 257 s to
403 s. With xdist at 10 workers on 2 vCPU, 5083 tests spent 888 s of 1089 s in 556 planner
calls with only 183 distinct inputs. A cache keyed by file content (with a staleness test and a
byte-identical replay of recorded inputs) brought the CI step to 146 s. Lesson: timing criteria
are ceilings on the whole stage, checked after every step.

Earlier, about 700 parametrised "mutate a copy of the repository, run the whole validator" tests
took 64 % of unit time; 466 of 688 rejecting cases were rejected by one equality check, and two
passed for the wrong rule. Direct rule tests asserting the message cut that file from 145 s to
2.6 s.

## What the confirmation runs found

- **First run:** the strict aggregate rejected a stray receipt. A test that ran `make` in the
  real checkout wrote it, and each job uploaded the whole receipts directory. Fix: upload each
  job's own receipts by exact path; keep the aggregate strict. Proof: the aggregate replayed on
  the run's downloaded artefacts failed before the fix (exit 65) and passed after (exit 0). One
  more confirmation run, green.
- **First default-branch run after the merge:** the collections cache missed (only the pull
  request had saved it) and the network install failed with "Connection reset by peer", which
  the tool's built-in retry does not cover. Fix: save shared caches from default-branch runs;
  bounded, jittered retry around the collection install only.
- **Not exercised, reported as unverified:** a run without the unit stage, a re-run of one failed
  leg downloading artefacts from the earlier attempt.

## Before and after

```
Before:  quick ─► static (1 job, ~31 min) ─► 8 optional jobs together ─► gate
After:   quick ─► plan ─► 16 static legs + unit ─► static aggregate
                       └► light jobs ─► heavy jobs
                       └► image security ───────────────────────────────► gate
```

| | Before | After |
|---|---|---|
| Wall clock | 3725 s | 2096 s (−44 %) |
| Exact runner time | 125.0 min | 127.4 min (+2 %) |
| Billed minutes | 130 | 142 (+9 %) |

The per-phase breakdown of these totals, and how to read it, is listed under the skill's step 9.

## Lessons

- Every hypothesis, the owner's included, was checked by a measurement; two were refuted.
- Every diagnosis came from recorded runs and local timing; CI ran only to confirm finished
  changes, and each defect it found was fixed and proven locally first.
- Halving wall clock raised the bill: report W and B together and let the owner choose.
