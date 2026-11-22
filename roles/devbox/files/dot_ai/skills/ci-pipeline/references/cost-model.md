# Cost model: wall clock and billed minutes

## Contents

- [Definitions](#definitions)
- [Why parallel jobs raise billed minutes](#why-parallel-jobs-raise-billed-minutes)
- [The measured case, per phase](#the-measured-case-per-phase)
- [How to compute the breakdown](#how-to-compute-the-breakdown)
- [What "cheaper" means](#what-cheaper-means)
- [GitLab compute minutes](#gitlab-compute-minutes)
- [When a split pays](#when-a-split-pays)

## Definitions

| Symbol | Meaning |
|---|---|
| W, wall clock | Run start to the gate's end: what a developer waits for. Includes queue time |
| E, exact runner time | Sum of executed jobs' durations |
| B, billed minutes (GitHub) | Sum over executed jobs of `ceil(duration / 60 s)`. Skipped jobs bill nothing. Queue time is not billed |

GitHub's pricing reference: "GitHub rounds the minutes and partial minutes each job uses up to
the nearest whole minute". A 61 s job bills 2 min; a 20 s job bills 1 min. Each job therefore
carries on average about half a minute of rounding slack (B − E).

## Why parallel jobs raise billed minutes

Every job repeats a fixed cost that one job pays once: runner set-up, checkout, toolchain install,
cache restore before the work; cache save, artefact upload and post steps after it. Each split
also adds rounding slack. Parallelism shortens W only for pieces that run at the same time; B
pays for every piece. A change can therefore cut W sharply while B rises.

Another example of rounding: a 4.6-minute change spread over several short jobs billed 7 minutes.

## The measured case, per phase

One static job was split into 18 (16 legs, a unit job, a static aggregate); the run went from 11
to 28 jobs. Two recorded runs, before and after:

| Part | Before (11 jobs) | After (28 jobs) | Change |
|---|---|---|---|
| Wall clock W | 3725 s | 2096 s | −44 % |
| Static stage, exact | 30.9 min (1 job) | 27.1 min (18 jobs) | −3.8 min |
| — set-up before the work | 17 s | 131 s | +114 s |
| — the work steps | 1831 s | 1417 s | −414 s |
| — after the work | 6 s | 79 s | +73 s |
| Static stage, billed | 31 min | 36 min | +5 min |
| — rounding slack | 0.1 min | 8.9 min | +8.8 min |
| Other 10 jobs, exact | 94.1 min | 100.3 min | +6.2 min |
| Other 10 jobs, billed | 99 min | 106 min | +7 min |
| **All jobs, exact** | **125.0 min** | **127.4 min** | **+2 %** |
| **All jobs, billed** | **130 min** | **142 min** | **+9 %** |

Reading it:

- **The split's own cost** is duplicated set-up and teardown, +187 s exact (about 10 s per extra
  job with a warm cache), and rounding, +8.8 billed minutes.
- **The work fell by 414 s** because of a separate change in the same period (a cache that
  stopped unit tests recomputing a plan per test: 259 s → 146 s), not because of the split.
- **The other jobs' +6.2 exact minutes** come from jobs the change did not touch (+191 s, +145 s,
  +59 s for three of them). That is most likely run-to-run variance [U: one pair of runs; the
  spread over more runs was not computed].
- So "+2 % runner minutes" understates B (+9 %), and one pair of totals mixes three effects that
  only the per-phase breakdown separates.
- **Cold-cache counterfactual:** on a cache miss each of the 16 legs would pay 30 to 73 s of
  dependency downloads, about 8 to 19 extra minutes before rounding [U: estimated, not observed].

## How to compute the breakdown

From the jobs JSON of both runs (`scripts/ci_run_timings.py compare DIR BASE NEW` does this):

1. For each executed job, split its steps at the first work step: everything before it is
   set-up (including the runner's set-up step), the work steps are work, everything after the
   last work step is after-work.
2. Sum each phase per stage; sum `ceil(duration/60)` per job for B.
3. Report W, E and B per stage and in total, with the rounding slack, for both runs.
4. Mark differences in jobs the change did not touch as variance unless the spread from several
   recorded runs says otherwise.

## What "cheaper" means

Settle this before optimising B; the trade-off between W and B belongs to the owner, and the
report gives both.

| Repository | B costs | "Cheaper" means |
|---|---|---|
| Public, standard GitHub-hosted runners | Nothing: standard runners are free in public repositories | W, queue time under the concurrency cap, the shared runner pool |
| Private | Deducted from the plan's included usage (a monetary amount); billed beyond it | B, the share of the allowance it uses, and the rate (Linux 2-core $0.006/min on the pricing page as read; re-check) |
| Larger runners, any visibility | [U]: not read | Check the pricing page first |

A +9 % B can be free this month and paid next month; report the share of the allowance, not only
the delta.

## GitLab compute minutes

Usage is "Job duration / 60 * Cost factor", with job duration excluding `created` and `pending`
time. GitLab.com hosted Linux x86-64 runners: factor 1 (small), 2 (medium), 3 (large); GitLab for
Open Source public projects 0.5, their public forks 0.008. Self-Managed shows instance-runner
usage on a dashboard with optional quotas. Per-job rounding is not documented [U], so the
duplicated set-up argument holds without the rounding term. A runner with factor 2 pays only if
it more than halves the duration.

## When a split pays

- Split when pieces are independent and each takes much longer than the fixed per-job cost
  (case study: pieces over about 30 s against about 8 s fixed cost), and W matters more than B
  for this repository.
- A warm cache is a precondition: every split-out job pays the cold install otherwise.
- Budget against the concurrent-job cap: fan-out × simultaneous pull requests (the case study
  peaked at about 21 jobs). Use `max-parallel` or bundle small suites once a measured queue time
  shows the need.
- Re-ordering light before heavy jobs mostly buys billed heavy minutes and verdicts not lost to
  cancellation; estimate it by replaying recorded runs, not by trying it on CI.
