---
name: ci-pipeline
description: >
  Builds, diagnoses and optimises GitHub Actions and GitLab CI pipelines: timings from recorded
  runs and local step timing (never trial pushes), cancelled runs, concurrency, fail-fast, job
  selection and ordering, the aggregate gate and skipped needs, artefacts, caches and billed
  minutes. Use when writing a workflow file (.github/workflows/*.yml, .gitlab-ci.yml) or when CI
  is slow, costly, cancelled or flaky. Also use when the user mentions gh run, glab ci,
  cancel-in-progress, interruptible, needs, matrix, required checks or actions/cache, even for a
  one-line workflow edit. Not the agent-pipeline `workflow` skill, nor for a failing test inside
  a job (diagnose-and-repair).
alwaysApply: false
problem: "CI changes are found by pushing variants and watching live runs, or judged from guesses about where time goes, instead of being measured on a local bench and on recorded runs and then confirmed by one run."
related: [diagnose-and-repair, sandbox-toolchain, project-toolchain, python-testing, go-testing, docker-validation, code-comments]
triggers:
  - GitHub Actions
  - GitLab CI
  - CI pipeline
  - .github/workflows
  - .gitlab-ci.yml
  - gh run
  - glab ci
  - cancel-in-progress
  - interruptible
  - concurrency group
  - fail-fast
  - required status check
  - actions/cache
  - upload-artifact
  - runner minutes
  - compute minutes
---

# CI Pipeline

Treat a CI pipeline as a measured system, and keep the measuring off live CI. Find where time goes
from runs that already happened and from timing steps locally; choose a change on that bench; let
one CI run confirm it.

This is a main-session skill: it loads from its description, and no agent lists it in `skills:`
by design.

Platform facts with their documentation anchors live in `references/`. A fact marked **[U]** was
not confirmed in primary documentation or a recorded run: treat it as a premise to check, and say
so when a conclusion rests on it.

## Contents

- [When this applies](#when-this-applies)
- [0. The bench rule](#0-the-bench-rule-live-ci-is-not-a-test-bench) and the [checklist](#ci-change-checklist)
- [1. Measure before changing](#1-measure-before-changing)
- [2. Read the run correctly](#2-read-the-run-correctly)
- [3. Concurrency and fail-fast](#3-concurrency-and-fail-fast)
- [4. Selection: run what the change needs, fail closed](#4-selection-run-what-the-change-needs-fail-closed)
- [5. Job graph and ordering](#5-job-graph-and-ordering)
- [6. Gates and skipped needs](#6-gates-and-skipped-needs-hard-rules)
- [7. Artefacts and receipts](#7-artefacts-and-receipts)
- [8. Caching and network-dependent setup](#8-caching-and-network-dependent-setup)
- [9. Cost: wall clock and billed minutes](#9-cost-wall-clock-and-billed-minutes)
- [10. Confirm the finished change with one run](#10-confirm-the-finished-change-with-one-run)
- [Local and CI differ](#local-and-ci-differ)
- [Common mistakes](#common-mistakes)
- [References](#references)

## When this applies

- **In scope:** the pipeline's structure and behaviour: which jobs run, in what order, when they
  are cancelled, what they cost, and how their result is judged. Platforms: GitHub Actions in
  full; GitLab CI for measurement, reading runs, retries, cache scope and cost.
- **GitLab pipeline structure** (`rules:changes`, `needs`, stages, supersession settings) is not
  covered yet beyond the facts in `references/gitlab-ci.md`. Read the GitLab documentation for it
  and say that the guidance is not from this skill.
- **Out of scope:** making a red test green. That is `diagnose-and-repair`, or the language testing
  skill when the cost sits inside the tests. Steps 0 and 1 still help to find which test is slow.

## 0. The bench rule: live CI is not a test bench

This is the leading rule; every later step obeys it.

- **Optimise on a local bench or on recorded runs, never on live CI.**
  - *Recorded runs:* job and step (GitLab: section) timings of runs that already happened, read
    through the CI API. They give the baseline, its spread, and the quantities that exist only on
    CI.
  - *Local bench:* time each step or stage the change touches by running the same entry point the
    CI step calls (the task-runner target, not a hand-written approximation). Match the runner
    where the result depends on it: CPU count (private GitHub standard runners have 2 vCPU; use a
    container CPU limit or `taskset`), and cold against warm cache, timed separately.
- **A CI run confirms a finished change once; it is never the search.** Forbidden: pushing a series
  of commits to see which variant is faster; temporary experiment jobs or `workflow_dispatch`
  matrices of variants; A/B jobs running two strategies side by side; re-running a run to "see if
  it is faster now". Each costs billed minutes and concurrency slots other pull requests need,
  adds noise to the history the next diagnosis reads, and one run's difference usually sits
  inside run-to-run variance.
- **A quantity that exists only on CI** (cancellation mechanics, cache scope across refs,
  artefacts across attempts, queue time under the concurrency cap, billing) is read from recorded
  runs or the documentation, or named as unverified. Do not provoke it by experiment. If no
  recorded run shows it, design the single confirmation run to exercise it when that costs
  nothing extra.
- **Judge a CI-side difference against the spread of recorded runs, not one baseline run.** One
  run cannot show a change smaller than the spread of the jobs it touches. In the case study,
  three jobs the change did not touch moved by +191 s, +145 s and +59 s between two runs: more
  than the whole run's runner-time difference.
- **Write acceptance criteria as local, checkable commitments.** State a timing criterion as a
  ceiling on the whole file, stage or job, not on the new code alone, because per-step
  acceptance cannot see a stage-level regression. A count or duration estimate is a labelled
  forecast that the coverage criteria override; the CI number is a forecast the confirmation run
  checks.

### CI change checklist

Run through it before the push that will start the confirmation run.

1. Baseline read from several recorded runs, with the spread per touched job.
2. Every candidate timed on the local bench through the CI entry point, runner CPU count matched.
3. The change is finished and meets its local criteria; nothing is left to try on CI.
4. Each verification item is observable before merge, given the triggers, the push policy and
   artefact retention (step 10); the rest is deferred with a named condition.
5. The comparison to make after the run is written down (step 10), with the paths the run will
   not exercise listed in advance.
6. One push. A defect it shows is reproduced and fixed locally, then confirmed by one more run.

## 1. Measure before changing

- **Read the CI's own records first, for the baseline.** GitHub: the run's jobs endpoint gives each
  job's queue, start and end times and its step durations; check-run annotations give cancel and
  error text. GitLab: the pipeline's jobs endpoint, with `include_retried=true`; it has no
  per-step timing, so use log sections or a job split (`references/gitlab-ci.md`). Take a sample
  of runs, not one. Then time locally the steps the change will touch.
- **Use the timings script** rather than writing a fetcher again (usage in
  `references/measuring-runs.md`). It reads recorded runs through an authenticated `gh` or `glab`,
  chosen from the repository remote, and never triggers, re-runs or cancels a run:

  ```
  scripts/ci_run_timings.py history [--provider P] [--repo R] [--host H] [--branch B] [--limit N] [--out DIR]
  scripts/ci_run_timings.py fetch   [--provider P] [--repo R] [--host H] [--sections] --out DIR RUN_ID...
  scripts/ci_run_timings.py report  DIR RUN_ID [--min-step-seconds S] [--cost-factor F]
  scripts/ci_run_timings.py compare DIR BASE_RUN_ID NEW_RUN_ID [--min-step-seconds S]
  ```

  Exit 2: tool missing or the host is neither GitHub nor GitLab (pass `--provider`); exit 3: not
  authenticated (the message gives the `auth login` command); exit 4: an API call failed.
- **When job logs are unreachable** (they are served from a separate blob host that a sandbox may
  block), take step timestamps from the API host instead, say what the missing logs leave
  unknown, and measure that locally. Do not work around the network block (`sandbox-toolchain`).
- **Split each job's time into fixed per-job cost and work.** Fixed cost is runner set-up,
  checkout, toolchain sync, dependency install and cache restore. Its size decides whether
  splitting a job pays (step 5).
- **Test a causal hypothesis against a measurement before acting on it**, the user's included.
  "Collection overhead" was refuted by timing `--collect-only` alone (1.3 s for 5314 items) and
  the subprocesses inside the tests (one `ansible-playbook` per case). "The playbook runs twice"
  was refuted by recording every invocation with its path and phase and finding no overlap. Trace
  what runs; do not infer it from the step structure.
- **Locate cost per test, not per suite.** Use JUnit durations from CI or one fixed local method.
  Record repeated work and its distinct inputs (calls against distinct arguments) before choosing
  a remedy. More xdist workers on a 2-vCPU runner made one unit job slower (403 s against 257 s
  serial) because every test recomputed the same plan; a content-keyed cache brought it to
  146 s. The fix technique belongs to the testing skill (`python-testing`, `go-testing`).

## 2. Read the run correctly

- **A cancelled job is not evidence that it did not fail.** A cross-job fail-fast step that calls
  `gh run cancel` from inside the failing job rewrites that job's conclusion to `cancelled`; only
  the aggregate gate stays red. Find the failing job from step conclusions and annotations, not
  job conclusions. The cancel step itself may end `cancelled`: count it either way.
- **Classify every cancelled run into one mechanism and leave no residue:** self-cancel,
  concurrency supersession, timeout, manual, platform loss. The separating observations are the
  annotation text ("canceled by @github-actions[bot]", "higher priority waiting request",
  "exceeded the maximum execution time") and whether a cancel step started. Do not propose a fix
  before the attribution is complete.
- **Count restarts that come from outside the workflow.** A dependency bot that rebases every open
  pull request on each merge restarts CI with the same diff on a new parent; in the case study it
  was the largest minute sink. Changing the bot's rebase policy is a trade-off for the owner.
- **GitLab:** read jobs with `include_retried=true`, so a later attempt does not hide an earlier
  failed one; a job cancelled through the API or superseded under `interruptible` reads like the
  GitHub case.
- **Describe what a gate or cancel step does from its source,** per job. Map each cancel step to
  the jobs that have it before generalising, and quote a gate's message from the code that prints
  it: a gate that stops at its first mismatch names that job, not the one the reader expects.
- **Documenting a pipeline:** name the policy and the constant that holds it instead of copying a
  count from older prose; any number kept is counted from the code and cited (`code-comments`,
  Staleness Test).

## 3. Concurrency and fail-fast

- **Cancel superseded runs only where a newer run makes the old result worthless.** That holds for
  pull requests, not for the default branch, where every merged commit should reach a verdict.
  GitHub keeps one running and one pending run per group and replaces the pending one, so the
  newest commit is still tested.

  ```yaml
  concurrency:
    group: ci-${{ github.workflow }}-${{ github.event_name == 'schedule' && 'schedule' || github.ref }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```

  GitLab's counterpart is `interruptible` (default `false`); keep it off deployment jobs.
- **Matrix `fail-fast` acts only inside one matrix.** Stopping other jobs needs an explicit cancel.
  Use one only where it saves minutes, and announce it first: an error annotation and a
  step-summary line naming the failing job. Leave it out of the job that usually finishes last
  (it saves little and hides the failure) and of jobs nothing runs beside.
- **A matrix whose legs are independent evidence sets `fail-fast: false`.**

## 4. Selection: run what the change needs, fail closed

- **When a job runs everything, check both rival causes:** (a) the planner selects everything
  through a catch-all rule or a hub input every check reads; (b) CI ignores the plan (steps
  without `if:`). Either can hide the other. Measure the size of each by replaying the planner
  over recent real change sets and reporting the fraction that would skip each stage, before
  crediting either with the job time.
- **Prefer selection computed from the change at job level over workflow-level path filters.** A
  required workflow skipped by `paths:` leaves its check pending and blocks the merge; a job
  skipped by `if:` reports success.
- **Every selection rule has a fail-closed fallback.** No base commit, a parse error, a change to
  the toolchain or to the classifier itself, or an unclassified path selects everything. That is
  safe and costly; report the cost, do not hide it.
- **Fan out from the plan with a dynamic matrix and guard the empty list:** a matrix built from
  `fromJSON('[]')` fails the job, so the job carries `if: … != '[]'`.
- **A module imported by several jobs uses only dependencies every importing job installs.** List
  the jobs that import it and the dependency groups each installs (`--no-default-groups` jobs
  install fewer), and add a check that runs it under the smallest set.
- **Recommended, not required: bind the plan to the run.** Publish a digest of the plan and have
  the aggregate check that the retained plan matches it and every selected subject left exactly
  one receipt. It pays only when a planner exists. Design: `references/selection-and-gates.md`.

## 5. Job graph and ordering

- **Order by cost and failure risk: cheap failure-prone jobs first, independent heavy jobs in
  parallel.** Use an explicit, measurable tier rule taken from recorded runs, for example "p90 of
  successful durations ≤ 10 min and no VM guest means light". A heavy job waits only for what
  guards it or what it reads.
- **Work out what re-ordering can buy before promising it,** by replaying recorded runs. In the
  case study light jobs already started within 2 s of their prerequisite, so the gain was billed
  heavy minutes and lost verdicts, not earlier signal, and the largest failure cost (a heavy
  job's own defect) was out of reach of any ordering.
- **Do not make a job wait for something slow it does not read.** A scan that outlasts the static
  stage and whose output no heavy job reads leaves the heavy prerequisites but stays in the gate.
- **Split a job when its pieces are independent and each takes much longer than the fixed per-job
  cost** (in the case study: pieces over about 30 s against about 8 s fixed cost). Keep pieces as
  steps when they share state that cannot be cached. The billed side of a split is step 9.
- **A machine-checked shape contract** (a copy of the workflow topology in a test) catches drift
  but must be edited in every restructuring. Keep it only if that is cheap, and change both in the
  same change.

## 6. Gates and skipped needs (hard rules)

- **One aggregate job is the only required check.** It runs with `if: always()` and judges every
  needed result against the selection: selected means `success`, unselected means `skipped`, and
  a job that ran while unselected fails the gate too. Use `always()` here, not `!cancelled()`:
  a skipped job reports success to required checks, so a gate that can be skipped can pass a run
  it never judged.
- **Accept `skipped` from a needed job only when the run did not select that job.** A job is also
  skipped when one of its own needs failed or was cancelled. Tie the predicate to the selection
  output; never write `result != 'failure'` (a cancelled or selected-but-skipped job passes) or a
  bare `result == 'skipped'`.

  ```yaml
  if: >-
    ${{ !cancelled() && needs.static.result == 'success' &&
        (needs.light.result == 'success' ||
         (needs.light.result == 'skipped' && needs.plan.outputs.light_selected != 'true')) }}
  ```

- **With `!cancelled()` a job whose need was skipped is still evaluated,** so test each need's
  result explicitly, and check that the gate's exact rule still holds for a heavy job skipped
  because a light job failed. Re-running failed jobs carries earlier successes over.
- **Test evaluators match the platform's semantics.** GitHub ignores case when comparing strings
  with `==`, so a stand-in that compares case-sensitively certifies behaviour GitHub does not
  have. Keep rejection of non-canonical outputs (`TRUE`) as a separate fail-closed check.
- Gate predicate templates: `references/selection-and-gates.md`.

## 7. Artefacts and receipts

- **Upload artefacts by exact path, never a whole directory, when a strict consumer reads them.**
  Tests and commands can leave extra files there; a test that ran `make` in the real checkout once
  wrote a stray receipt that a strict aggregate rightly rejected. Keep the consumer strict; narrow
  the upload.
- **Replay the aggregate against a real run's downloaded artefacts before calling a fix done:**
  "before" reproduces the CI failure, "after" shows it gone. This is how a defect found by a
  confirmation run is fixed without searching on CI.
- **Upload evidence with `if: always()`.** `if-no-files-found: error` where the file is required,
  `warn` where a missing file must not turn a passing job red; `overwrite: true` so a re-run can
  upload under the same name. Check how a multi-line `path:` behaves when one entry finds nothing.

## 8. Caching and network-dependent setup

- **Key the cache on the exact inputs** (the lockfile or requirements hash plus OS and
  architecture). Restore and save as separate steps; save only on a miss.
- **Know the scope.** GitHub: a cache saved by a pull-request run belongs to that pull request's
  merge ref; other pull requests and the base branch cannot restore it. Runs restore from their own
  branch, the default branch and, for pull requests, the base branch. Unused entries are evicted
  after 7 days. GitLab: keys get a `-protected` or `-non_protected` suffix, so by default an
  unprotected branch and the protected default branch do not share a cache (`cache:unprotect`
  changes that). Details: `references/github-actions.md`, `references/gitlab-ci.md`.
- **Save every shared cache from default-branch runs,** and treat the first default-branch run
  after a new or re-keyed cache as cold: it pays the network install in every fanned-out job.
  Confirm the hit with one recorded default-branch run; do not trigger runs to warm it.
- **A cache is a precondition for fanning out, not an add-on:** every split-out job pays the cold
  install unless the cache hits.
- **Wrap network fetches in setup in bounded retries with backoff, and nothing else.**
  - Scope: the step that downloads packages, collections, images or toolchains. Never retry
    tests, linters, checks or the gate: a retried check hides a flaky test or a real defect and
    makes the verdict depend on luck.
  - Shape: a fixed attempt count (3 is enough), exponential backoff with jitter, an overall cap
    well inside the job timeout, each failed attempt logged as a warning so recorded runs show
    it, and a final non-zero exit with the tool's own error.
  - Put the fetch in its own step that runs only on a cache miss, so the steps after it run
    offline and are never inside the retry.
  - Check the tool's built-in retry before adding one: ansible-galaxy retries HTTP 429, 502, 520
    and timeouts, but not "Connection reset by peer".
  - GitHub has no retry key for steps or jobs: the retry is a loop in the step's script or the
    task runner's install function. GitLab's `retry:` re-runs the whole job and defaults to
    `when: always`; limit it with `retry:exit_codes` and a dedicated exit code from the fetch
    wrapper, or retry inside the script. Pattern: `references/measuring-runs.md`, "Retry pattern".

## 9. Cost: wall clock and billed minutes

The arithmetic, the per-phase table and the platform pages are in `references/cost-model.md`.

- **Report wall clock W and billed minutes B separately, and know why they move apart.** W is run
  start to gate end, queue included. B on GitHub is the sum over executed jobs of each job's
  duration rounded up to a whole minute. Every extra job repeats set-up and teardown and adds
  about half a minute of rounding slack; parallelism shortens W only for pieces that run at the
  same time, while B pays for every piece.
- **Measured case:** splitting one static job into 18 cut W by 44 % while exact runner time rose
  2 % and billed minutes 9 % (rounding slack 0.1 → 8.9 min). Report the per-phase breakdown
  (set-up, work, after-work, rounding), not one pair of totals.
- **Say what "cheaper" means for this repository before optimising B.** Public repository on
  standard GitHub-hosted runners: B costs no money, so "cheaper" means W, queue time and the
  shared pool. Private repository: B is deducted from the plan's included usage and costs money
  beyond it; report B, the share of the allowance and the rate. The W-for-B trade-off belongs to
  the owner.
- **GitLab bills compute minutes:** job duration (without `created` and `pending` time) ÷ 60 ×
  the runner's cost factor. Per-job rounding is not documented [U]; report usage unrounded.
- **Budget against the concurrent-job cap** (fan-out times simultaneous bot pull requests), with
  `max-parallel` or bundling, once a measured queue time shows the need. **Runner size limits
  parallelism inside a job.**

## 10. Confirm the finished change with one run

- **A CI change is done when one confirmation run shows the intended behaviour.** Compare it with
  the recorded baseline and its spread (`scripts/ci_run_timings.py compare`) on: wall clock;
  per-job and per-step (or section) time; exact and billed minutes broken down as in step 9;
  what each run ran against what the change needed; the job graph and what a failure looks like
  to a reader. A defect it shows is reproduced and fixed locally (step 7 replay), then confirmed
  by one more run.
- **Name what the run did not exercise and leave it unverified:** an empty-plan branch, a re-run
  of one failed leg, a selection that keeps a stage off, a cold cache on the default branch. List
  them with the recorded runs searched; do not stage extra runs to cover them.
- **Check each verification item against what can be observed before merge.** A scheduled run
  happens only on the default branch; a multi-week shadow window outlives artefact retention and
  the pull request; a CI measurement between steps conflicts with pushing once. Replace each with
  an in-PR substitute or defer it with a named condition.

## Local and CI differ

- **Local red, CI green:** repository scanners (lint, secret checks) may read untracked scratch
  the CI checkout never has. Prove it with `git ls-files` and `git check-ignore -v`, judge the
  change on tracked files, and leave the scanner alone (`project-toolchain`).
- **Local green, CI red:** CI differs in CPU count, cache state, checkout contents, installed
  dependency groups and network. Reproduce the CI condition locally before changing CI.

## Common mistakes

| Assumption | Reality | Step |
|---|---|---|
| "Push it and see whether CI is faster" | The search runs on the bench; CI confirms once | 0 |
| "One run against one run shows the effect" | Untouched jobs move by minutes between runs | 0 |
| "Cancelled means not failed" | A self-cancel relabels the failing job | 2 |
| "More xdist workers always help" | 2 vCPU and repeated per-test work can make it slower | 1 |
| "Collection is the cost" | Measure `--collect-only` and the subprocesses first | 1 |
| "Path filters are cheaper" | A skipped required workflow blocks the merge | 4 |
| "A PR's cache warms the next PR" | PR caches are scoped to that PR's merge ref | 8 |
| "The first default-branch run after the merge is warm" | It is cold unless the default branch saved | 8 |
| "Retry the job when CI is flaky" | Retry network fetches in setup only | 8 |
| "Skipped is a pass" | Only when the job was not selected | 6 |
| "+2 % runner minutes means a +2 % bill" | Per-job rounding made it +9 % | 9 |
| "Local green means CI green" | Reproduce the CI condition locally | Local and CI |

## References

| File | Read when |
|---|---|
| `references/measuring-runs.md` | Steps 0 to 2: the local bench, the timings script, `gh`/`glab` recipes, classifying cancellations, the retry pattern |
| `references/github-actions.md` | Writing or reviewing a GitHub workflow: concurrency, status functions, matrix, required checks, cache scope, artefacts, limits, billing |
| `references/gitlab-ci.md` | Writing a GitLab pipeline or reading its runs: jobs API, log sections, `retry`, job-stage attempts, `interruptible`, cache, compute minutes |
| `references/selection-and-gates.md` | Steps 4 and 6: planner outputs, fail-closed rules, plan digest, gate predicates |
| `references/cost-model.md` | Step 9: W and B arithmetic, the per-phase table, public and private repositories |
| `references/case-study.md` | A worked example with real numbers: three diagnoses, rivals refuted, before and after |
