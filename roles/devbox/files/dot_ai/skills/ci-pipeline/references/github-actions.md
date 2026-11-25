# GitHub Actions facts with documentation anchors

Each row names the page it comes from and the date it was read. GitHub moves pages; when a link
404s, search docs.github.com for the heading and update the row. **[U]** marks a fact not
confirmed on the page in this revision.

## Contents

- [Concurrency](#concurrency)
- [Expressions, status functions and needs](#expressions-status-functions-and-needs)
- [Matrix](#matrix)
- [Required checks](#required-checks)
- [Caching](#caching)
- [Artefacts and re-runs](#artefacts-and-re-runs)
- [Retries](#retries)
- [Runners and billing](#runners-and-billing)
- [REST endpoints for timing](#rest-endpoints-for-timing)

## Concurrency

Source: [Control workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), read 2026-11-22.

| Fact | Consequence |
|---|---|
| At most one running job or workflow per concurrency group | A second run waits as pending |
| An existing pending run in the group "is canceled and replaced" by a newer one | The newest commit is still tested even without `cancel-in-progress` |
| `cancel-in-progress` accepts an expression | `${{ github.event_name == 'pull_request' }}` cancels superseded PR runs only |

Give scheduled runs their own group (for example by putting `'schedule'` into the group key), so
a push does not cancel or queue behind them.

## Expressions, status functions and needs

Sources: [Expressions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions),
read 2026-11-22; [Using jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs), read 2026-11-22.

| Fact | Consequence |
|---|---|
| "GitHub ignores case when comparing strings" | `'TRUE' == 'true'` is true. A test helper that evaluates `if:` case-sensitively certifies wrong behaviour |
| `success()` is implied when an `if:` has no status function | `if: needs.x.result == 'skipped'` alone never runs after a failed need |
| `always()` returns true even when the workflow was cancelled; the page advises `!cancelled()` for steps that could fail critically or hang | Use `!cancelled()` for ordinary "run regardless" jobs; use `always()` for the aggregate gate (see Required checks) |
| `failure()` is true when any previous step fails, or any ancestor job in a chain of needs | |
| "If a job fails or is skipped, all jobs that need it are skipped unless the jobs use a conditional expression that causes the job to continue" | A job skipped because its need failed looks the same as one skipped because it was unselected. Tie `skipped` to the selection output |

## Matrix

Source: [Running variations of jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations), "Handling failures", read 2026-11-22.

| Fact | Consequence |
|---|---|
| `fail-fast` cancels in-progress and queued jobs of the same matrix only | Stopping jobs outside the matrix needs an explicit `gh run cancel` step |
| `fail-fast: false` keeps every leg running | Use it when legs are independent evidence |
| `max-parallel` caps simultaneous legs | Use it against the concurrent-job cap once queue time shows the need |
| A matrix from `fromJSON(needs.plan.outputs.legs)` with `'[]'` fails the job [observed in a recorded run] | Guard with `if: needs.plan.outputs.legs != '[]'` |

## Required checks

Source: [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks), read 2026-11-22.

| Fact | Consequence |
|---|---|
| "A job is skipped by a conditional": the job reports "Success" | A skippable gate can pass a run it never judged |
| A workflow skipped by path filtering, branch filtering or commit message: "Associated checks stay in a "Pending" state and block merging" | Do not put `paths:` on a required workflow; select at job level |
| "Use `always()` with `needs` for required checks that depend on other jobs" | The aggregate gate runs with `if: always()` |

## Caching

Source: [Dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching), "Restrictions for accessing a cache", read 2026-11-22 (as cited by the proposal this skill was built from).

| Fact | Consequence |
|---|---|
| A run can restore caches created on its own branch, the default branch, and for pull requests the base branch | Shared caches must be saved by a default-branch run |
| A cache saved by a pull-request run is scoped to `refs/pull/N/merge` | Only re-runs of that pull request can restore it; the next pull request starts cold |
| Entries not accessed for 7 days are evicted; the default limit is 10 GB per repository | A scheduled default-branch run keeps a rarely used entry alive |

Observed: the first default-branch run after a pull request introduced a cache missed it (only
the pull request had saved it) and fell back to a network install that then failed.

## Artefacts and re-runs

| Fact | Status |
|---|---|
| `if-no-files-found` takes `error`, `warn` or `ignore`; `overwrite: true` replaces an artefact of the same name | Used in practice; action README not re-opened [U] |
| A re-run of one failed matrix leg can download artefacts uploaded by legs that succeeded in the earlier attempt | [U]: no recorded run exercised it |
| Re-running failed jobs keeps the earlier attempt's successful jobs and their results | Observed in recorded runs |

## Retries

Source: [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), read 2026-11-22.

The workflow syntax has no retry key for steps or jobs. A retry is a loop in the step's script,
in the task runner's install function, or a third-party action pinned by commit SHA. The
pattern and its scope are in the skill's step 8.

## Runners and billing

Sources: [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing), read 2026-11-22;
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), "Included compute usage and storage", read 2026-11-22.

| Fact | Status |
|---|---|
| "GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute" | Documented |
| Linux 2-core standard runner: $0.006 per minute | Documented on the pricing page as read; rates change, re-check before quoting money |
| Standard GitHub-hosted runners are free in public repositories | Documented |
| Private repositories draw on the plan's included usage, stated as a monetary amount; usage beyond it is billed | Documented |
| Private standard Linux runners have 2 vCPU | [U]: runner reference not re-opened |
| Larger runners and their billing in public repositories | [U]: not read |

## REST endpoints for timing

Source: [Workflow jobs API](https://docs.github.com/en/rest/actions/workflow-jobs), read 2026-11-22.

| Endpoint | Gives |
|---|---|
| `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs?filter=all` (default `latest`) | Jobs with `started_at`, `completed_at`, `conclusion`, `run_attempt` and a `steps` array (`name`, `number`, `status`, `conclusion`, `started_at`, `completed_at`) |
| `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{n}/jobs` | Jobs of one attempt |
| `GET /repos/{owner}/{repo}/actions/runs?branch=B&status=completed` | Run history [U: page not re-opened] |
| `GET /repos/{owner}/{repo}/check-runs/{job_id}/annotations` | Cancel and error annotations [U: page not re-opened] |
