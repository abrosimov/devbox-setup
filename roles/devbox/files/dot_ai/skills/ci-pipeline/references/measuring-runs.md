# Measuring runs: the local bench, recorded runs, and the retry pattern

## Contents

- [The local bench](#the-local-bench)
- [The timings script](#the-timings-script)
- [Raw recipes with gh and glab](#raw-recipes-with-gh-and-glab)
- [Classifying cancelled runs](#classifying-cancelled-runs)
- [Pitfalls](#pitfalls)
- [Retry pattern](#retry-pattern)

**[U]** marks a fact not confirmed in primary documentation or a recorded run.

## The local bench

The bench is where candidates are developed and chosen. Recorded runs give the baseline; the
bench gives the comparison between candidates.

- **Run the CI entry point, not an approximation.** Read the step's `run:` (or the job's
  `script:`) and call the same task-runner target with the project's command prefix
  (`project-toolchain`). A hand-written pytest command times a different thing.
- **Match the runner where the result depends on it.**
  - CPU count: private GitHub standard Linux runners have 2 vCPU [U: runner reference not
    re-opened]. Limit the bench with `taskset -c 0,1 <cmd>` on Linux or
    `docker run --cpus=2 …`. Parallelism results (xdist workers, `make -j`) are meaningless
    without this.
  - Cache state: time cold (fresh cache directories) and warm separately, and report both. A
    fan-out decision needs the cold number.
- **Repeat and report the spread.** Run each candidate at least three times; report median and
  range. Pin the inputs (same commit, same lockfile).
- **Record repeated work, not only totals.** A call recorder (a wrapper that logs each call's
  arguments and duration) shows "556 calls, 183 distinct inputs" where a profiler shows only "the
  planner is slow". Collection alone: `pytest --collect-only -q <same args>`.
- **Write the criterion as a ceiling on the whole stage**, and the bench number as the evidence
  for it. The CI number is a forecast until the confirmation run.

## The timings script

`scripts/ci_run_timings.py` is one standard-library Python file that shells out to `gh` or
`glab`. It only reads: it never triggers, re-runs or cancels a run, and its `api` calls are GET
only.

```
ci_run_timings.py history [--provider P] [--repo R] [--host H] [--branch B] [--limit N] [--out DIR]
ci_run_timings.py fetch   [--provider P] [--repo R] [--host H] [--sections] --out DIR RUN_ID...
ci_run_timings.py report  DIR RUN_ID [--min-step-seconds S] [--cost-factor F]
ci_run_timings.py compare DIR BASE_RUN_ID NEW_RUN_ID [--min-step-seconds S]
```

| Subcommand | Does |
|---|---|
| `history` | Lists completed runs (GitHub) or pipelines (GitLab) of one branch with wall clock and status, so the baseline and its spread come from many runs |
| `fetch` | Stores the raw API JSON per run under `DIR` (`run-<id>.json`, `jobs-<id>.json`). `--sections` also downloads GitLab job logs and parses their section markers |
| `report` | Offline. Per-job timeline (start offset, end offset, duration, conclusion), exact runner time, billed estimate, slow steps or sections |
| `compare` | Offline. Both reports and the per-job and per-phase difference: set-up before the work, the work, after the work, rounding slack |

**Provider detection (`--provider auto`, the default).** The script reads the `origin` remote
(`--remote NAME` for another), takes the host and project path, and picks `gh` for `github.com`
or a host `gh auth status` lists, `glab` for `gitlab.com` or a host `glab auth status --hostname H`
accepts. It never guesses from repository files, because a repository can carry both
`.github/` and `.gitlab-ci.yml`. `--repo` (`OWNER/REPO` or a GitLab project path) and `--host`
override the remote.

**Exit codes.** 0 only when every requested run was read; 2 the tool is missing or the host is
neither platform (pass `--provider`); 3 the tool is not authenticated for the host (the message
gives `gh auth login --hostname H` or `glab auth login --hostname H`); 4 an API call failed (the
CLI's stderr is printed).

**Normalised output.** One TSV row per job and one per step or section:
`provider, run_id, attempt, job_id, job_name, stage, status, conclusion, queued_s,
start_offset_s, duration_s, billed_min_estimate, step_number, step_name, step_duration_s`.

- `stage` is empty on GitHub; `attempt` on GitLab is the retry index within the pipeline.
- `billed_min_estimate`: `ceil(duration_s / 60)` per job on GitHub; on GitLab
  `duration_s / 60 × --cost-factor` (default 1), unrounded because per-job rounding is not
  documented [U].
- Skipped jobs and jobs without `started_at` are reported and left out of runner time.

## Raw recipes with gh and glab

Use these when the script is not available or a question needs a field it does not print.

```bash
gh api "repos/{owner}/{repo}/actions/runs/$RUN_ID/jobs?filter=all&per_page=100" --paginate \
  --jq '.jobs[] | [.name, .run_attempt, .conclusion, .started_at, .completed_at] | @tsv'
gh api "repos/{owner}/{repo}/actions/runs/$RUN_ID/jobs?per_page=100" --paginate \
  --jq '.jobs[] | .name as $j | .steps[] | [$j, .number, .name, .conclusion, .started_at, .completed_at] | @tsv'
gh api "repos/{owner}/{repo}/check-runs/$JOB_ID/annotations"
gh api "repos/{owner}/{repo}/actions/runs?branch=$BRANCH&status=completed&per_page=100"
```

- `filter=latest` (the default) returns the latest attempt of each job; `filter=all` includes
  earlier attempts; `.../runs/$RUN_ID/attempts/$N/jobs` reads one attempt.
- The annotations endpoint, the runs-list endpoint and `gh api` filling `{owner}`/`{repo}` from
  the current repository were used in practice but their pages were not re-opened [U].

```bash
glab api "projects/:id/pipelines?ref=$BRANCH&status=success&per_page=100"
glab api "projects/:id/pipelines/$PIPELINE_ID/jobs?include_retried=true&per_page=100" --paginate
glab api "projects/:id/jobs/$JOB_ID/trace"    # log; path [U]
```

- `glab api` fills `:id`, `:fullpath`, `:branch` and other placeholders from the repository of
  the current directory, and `--hostname` defaults to that directory's authenticated host.
- `include_retried` defaults to `false`: without it a retried job's earlier attempt is invisible.

## Classifying cancelled runs

For every run with conclusion `cancelled`, read its jobs with steps and its annotations, then
assign exactly one mechanism. The residue must be zero; an unclassified run means a missing
mechanism, not noise.

| Mechanism | Separating observation |
|---|---|
| Self-cancel (fail-fast step) | A cancel step **started** in some job (its own conclusion may be `success` or `cancelled`), after a failed step in that job; annotation "canceled by @github-actions[bot]" |
| Concurrency supersession | Annotation "Canceling since a higher priority waiting request … exists"; a newer run in the same group |
| Timeout | Annotation "exceeded the maximum execution time" on a job |
| Manual | Cancelled by a named user; no cancel step started |
| Platform loss | Runner lost or shut down; none of the above |

Traps:

- The failing job's own cancel step usually ends `cancelled`, because the cancel it issued
  reached its own job. A classifier that counts only cancel steps ending `success` misses those
  runs (in the case study, 28 of 82).
- The job that really failed shows `cancelled`. Its failed step, not its conclusion, is the
  evidence.
- Count restarts from outside the workflow separately: the same diff re-tested on a new parent
  (a bot rebase) is not a cancellation mechanism but is often the largest minute sink.

## Pitfalls

- **Job logs** on GitHub are served from a separate blob host; a sandbox may block it while the
  API host works. Step timestamps and annotations come from the API (`sandbox-toolchain`).
- **In-progress runs** have no `completed_at`; leave them out of a baseline.
- **Re-run attempts** inflate apparent queue time: offsets measured from the run's creation
  include the time before the re-run. Measure an attempt from its own first job start.
- **Retried GitLab jobs** are hidden without `include_retried=true`.
- **One run is not a baseline.** Use `history`, take several runs, report the spread per job.

## Retry pattern

Wrap only the network fetch in setup. Run it in its own step that runs only on a cache miss, so
the steps after it run offline.

```bash
fetch_with_retry() {
  local attempt=1 max=3 delay
  until "$@"; do
    if (( attempt >= max )); then
      echo "$1 failed after $max attempts" >&2
      return 75
    fi
    delay=$(( 2 ** attempt + RANDOM % 5 ))
    echo "::warning::$1 failed (attempt $attempt of $max); retrying in ${delay}s" >&2
    sleep "$delay"
    attempt=$(( attempt + 1 ))
  done
}
fetch_with_retry ansible-galaxy collection install -r requirements.yml
```

- Put the overall cap on the step (`timeout-minutes:` on GitHub, `timeout:` on GitLab), well
  inside the job's limit. `::warning::` is a GitHub workflow command; on GitLab a plain line is
  enough.
- The dedicated exit code (75) lets GitLab's `retry:exit_codes: [75]` re-run the job for this
  failure only, if a job-level retry is wanted at all.
- Put the loop in the project's own install function when a task runner owns the install, so
  local and CI runs share it. A third-party retry action is the alternative; pin it by commit SHA
  like other actions.
- Check the tool's own retry first. ansible-core's Galaxy API client retries HTTP 429, 502 and
  520 and wrapped timeouts or incomplete reads, with jittered backoff; "Connection reset by peer"
  is not in that list, and the retry codes are not configurable. Whether collection downloads
  get the same retry in a given release is [U]; check the pinned version's source.
