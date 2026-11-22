# GitLab CI facts with documentation anchors

Coverage in this version: measurement, reading pipelines, retries, cache scope and cost. Pipeline
structure (`rules:changes`, `needs`, stage ordering, gates, the project setting that makes
`interruptible` supersede pipelines) is **not covered**: no row below was grounded in a real
GitLab pipeline, and those pages were not read. For structure, read docs.gitlab.com directly and
say that the guidance does not come from this skill.

Each row names its page; all were read on 2026-11-22. **[U]** marks a fact the page does not
state.

## Contents

- [Jobs and pipelines API](#jobs-and-pipelines-api)
- [Step timing: log sections](#step-timing-log-sections)
- [Retries](#retries)
- [Interruptible](#interruptible)
- [Caching](#caching)
- [Compute minutes](#compute-minutes)
- [Unverified](#unverified)

## Jobs and pipelines API

Sources: [Pipelines API](https://docs.gitlab.com/api/pipelines/), [Jobs API](https://docs.gitlab.com/api/jobs/), [glab api](https://docs.gitlab.com/cli/api/).

| Fact | Consequence |
|---|---|
| `GET projects/:id/pipelines?ref=B&status=success` (also `order_by`, `updated_after`) lists pipelines | The history for a baseline |
| `GET projects/:id/pipelines/:pipeline_id` shows `started_at`, `finished_at`, `duration`, `queued_duration` in its example | The page does not define `duration` [U] |
| `GET projects/:id/pipelines/:pipeline_id/jobs?include_retried=true`; `include_retried` defaults to `false` | Without it, an earlier failed attempt of a retried job is invisible |
| Job timing fields `created_at`, `started_at`, `finished_at`, `duration`, `queued_duration` appear in response examples only | Their exact meaning is [U] |
| The Jobs API has no per-step or per-section endpoint | Step timing needs log sections, a job split, or local timing |
| `glab api` fills `:id`, `:fullpath`, `:branch` and other placeholders from the current directory's repository; `--hostname` defaults to its authenticated host | Recipes work unchanged on self-hosted instances |

## Step timing: log sections

Source: [Job logs, "Create custom collapsible sections"](https://docs.gitlab.com/ci/jobs/job_logs/).

GitLab records time per job, not per command. In order of preference:

1. Give the work that needs its own timing its own job, when the split pays anyway (skill step 5).
2. Emit custom sections around each phase of the script, and compute end minus start from the
   markers (whole seconds):

   ```yaml
   script:
     - echo -e "\e[0Ksection_start:$(date +%s):install[collapsed=true]\r\e[0KInstall dependencies"
     - make install
     - echo -e "\e[0Ksection_end:$(date +%s):install\r\e[0K"
   ```

   The timings script's `fetch --sections` downloads each job's log and parses these markers.
3. Time the phases locally on the bench.

Auto-generated script sections (`FF_SCRIPT_SECTIONS`) do not display durations, so the marker
timestamps, not the UI, are the data. The log endpoint path (`projects/:id/jobs/:job_id/trace`)
and the names of the runner's own built-in sections are [U].

## Retries

Sources: [CI/CD YAML, `retry`](https://docs.gitlab.com/ci/yaml/#retry); [Configure runners, "Job stages attempts"](https://docs.gitlab.com/ci/runners/configure_runners/#job-stages-attempts).

| Fact | Consequence |
|---|---|
| `retry:` re-runs the whole job; `max` is 0 (default), 1 or 2 | A job-level retry repeats the tests too |
| `retry:when` takes failure categories such as `runner_system_failure`, `runner_external_dependency_failure`, `runner_interrupted`, `api_failure`, `scheduler_failure`, `stuck_pending_with_matching_runners`, `unknown_failure`, `script_failure`, and `always` (the default); 22 values in all, `stuck_or_timeout_failure` and `job_execution_timeout` deprecated | A blanket `retry: 2` also re-runs real test failures |
| `retry:exit_codes` limits retries to listed exit codes | A fetch wrapper with a dedicated exit code can be retried alone |
| A network error inside the script is a `script_failure` | `when: script_failure` would re-run failing tests as well |
| Runner fetch attempts: `GET_SOURCES_ATTEMPTS`, `ARTIFACT_DOWNLOAD_ATTEMPTS`, `RESTORE_CACHE_ATTEMPTS`, `EXECUTOR_JOB_SECTION_ATTEMPTS` (Docker executor); default 1 | Retries for the runner's own clone, artefact and cache fetches, without touching the script |

```yaml
install:
  script:
    - ./ci/fetch_with_retry.sh ansible-galaxy collection install -r requirements.yml
  retry:
    max: 2
    when: [runner_system_failure, api_failure]
    exit_codes: [75]
```

The script-level loop is usually enough; add `exit_codes` only when a whole-job retry is wanted.
The page states no rule for combining `when` and `exit_codes`; its example ("retried up to 2
times if the exit code is `137` or if it had a runner system failure") reads as either-or [U].
So never list `script_failure` beside `exit_codes`: it would retry every failing script.

## Interruptible

Source: [CI/CD YAML, `interruptible`](https://docs.gitlab.com/ci/yaml/#interruptible).

| Fact | Consequence |
|---|---|
| "Defines if a job can be canceled when made redundant by a newer run"; default `false` | Opt in per job |
| A job that has not started is always treated as interruptible | Queued jobs of a superseded pipeline go regardless |
| The docs advise against it for deployment jobs | Keep deploys non-interruptible |

## Caching

Sources: [Caching in GitLab CI/CD](https://docs.gitlab.com/ci/caching/); [CI/CD YAML, `cache:unprotect`](https://docs.gitlab.com/ci/yaml/#cacheunprotect).

| Fact | Consequence |
|---|---|
| Keys get the `-protected` suffix in pipelines for a protected branch or tag, or started by a Maintainer or Owner; other pipelines get `-non_protected` | By default an unprotected branch and the protected default branch do not share a cache |
| `cache:unprotect: true` makes them share it | Weigh it: unprotected pipelines can then write what protected ones read |
| Restore order: `cache:key`, then up to five `fallback_keys`, then `CACHE_FALLBACK_KEY` | A fallback to the default branch's key is possible within the same protection class |
| Different projects cannot share a cache | |
| Whether a merge-request pipeline reads the default branch's cache | [U]; under the suffix rule it cannot when the two differ in protection |

## Compute minutes

Source: [Compute minutes, "Compute usage calculation"](https://docs.gitlab.com/ci/pipelines/compute_minutes/).

| Fact | Consequence |
|---|---|
| Usage is "Job duration / 60 * Cost factor"; job duration excludes time in `created` and `pending` | Queue time costs nothing; it still adds to wall clock |
| GitLab.com hosted Linux x86-64: cost factor 1 (small), 2 (medium), 3 (large) | A medium runner pays only if it more than halves the duration |
| Public projects in the GitLab for Open Source programme: 0.5; public forks of them: 0.008 | Say which class the project is in before optimising usage |
| Self-Managed: instance-runner usage is shown on a dashboard and quotas are optional; no cost factors listed | "Cheaper" there means runner capacity and wall clock |
| Per-job rounding | [U]: not stated; report usage unrounded |

## Unverified

Carry these as premises, not facts, until the page is read:

- per-job rounding of compute minutes;
- the meaning of `duration` and `queued_duration` in the API;
- the log endpoint path and the runner's built-in section names;
- the exit code of `glab auth status` (the timings script treats non-zero as unauthenticated and
  confirms zero with one `glab api user` call);
- whether a merge-request pipeline can read the default branch's cache;
- the project setting that makes `interruptible` supersede pipelines;
- `rules:changes`, `needs` and stage semantics (out of this version).
