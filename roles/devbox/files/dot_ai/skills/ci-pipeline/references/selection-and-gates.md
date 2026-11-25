# Selection and gates: design and predicate templates

GitHub Actions syntax throughout; GitLab structure is outside this version of the skill.

## Contents

- [Planner outputs](#planner-outputs)
- [Fail-closed rules](#fail-closed-rules)
- [Selection methods](#selection-methods)
- [Measuring a selection before wiring it](#measuring-a-selection-before-wiring-it)
- [Binding the plan to the run (recommended)](#binding-the-plan-to-the-run-recommended)
- [Gate predicates](#gate-predicates)

## Planner outputs

A planner job reads the change set and publishes two kinds of output:

- **Booleans per optional job or stage** (`light_selected`, `stage_ansible`), each exactly
  `'true'` or `'false'`. The planner rejects any other value, and a test checks that it does:
  GitHub compares strings case-insensitively, so a stray `'TRUE'` would still select the job.
- **A list of legs** for a dynamic matrix, as a JSON array string. The consuming job guards the
  empty list, because a matrix from `fromJSON('[]')` fails:

  ```yaml
  component:
    needs: plan
    if: ${{ needs.plan.outputs.component_legs != '[]' }}
    strategy:
      fail-fast: false
      matrix:
        leg: ${{ fromJSON(needs.plan.outputs.component_legs) }}
  ```

The planner module runs in every job that imports it. It uses only dependencies all of those jobs
install; a check runs it under the smallest dependency set (for example
`uv run --no-default-groups`).

## Fail-closed rules

Every rule that can drop work has a fallback that selects everything. Report the cost of the
fallback when it fires; never make it silent.

| Condition | Selection |
|---|---|
| No base commit (new branch, shallow clone, force push) | Everything |
| The diff cannot be computed or a changed file cannot be parsed | Everything |
| The toolchain changed (lockfile, task runner, CI workflow) | Everything |
| The classifier or planner itself changed | Everything |
| A changed path matches no rule | Everything |
| A scheduled or default-branch run | Everything (a periodic full run backs the selection up) |

## Selection methods

| Method | Selects | Risk |
|---|---|---|
| Workflow `paths:` filter | Whole workflow | A skipped required workflow stays pending and blocks the merge; avoid on required workflows |
| Static include closure (which files each check reads, by declared includes) | Jobs or stages | A hub file read by every check selects everything; granularity is the lever |
| Read-set tracing (record what each check actually opened on a full run) | Jobs, stages or legs | The trace goes stale; re-record on toolchain change and fall back to everything when the trace is missing |

## Measuring a selection before wiring it

Before crediting a selection change with a saving, replay the planner over recent real change
sets (for example the last 30 default-branch commits) and report, per stage, the fraction that
would be skipped. If most commits still select everything, name why (a hub input, path
granularity) and treat the wiring as a minor saving. Separate the selection-independent cost
(process start-up, dependency install) that no selection can remove.

## Binding the plan to the run (recommended)

Worth it only when a planner exists and the aggregate is strict.

1. The planner publishes the plan and its digest (for example SHA-256 of the canonical JSON).
2. The plan file is uploaded as an artefact by exact path.
3. Every selected subject writes exactly one receipt (a small JSON naming its task), uploaded by
   exact path.
4. The aggregate downloads plan and receipts, checks the digest, and checks that the set of
   receipts equals the set of selected subjects: none missing, none extra, none unknown.

## Gate predicates

The aggregate gate is the only required check:

```yaml
ci-gate:
  if: always()
  needs: [plan, static, light, heavy]
  runs-on: ubuntu-latest
  steps:
    - name: Judge every result against the selection
      env:
        NEEDS: ${{ toJSON(needs) }}
      run: python3 ci/gate.py
```

The gate script, for each needed job: selected means the result must be `success`; unselected
means it must be `skipped`; anything else (including `cancelled`, or `success` while unselected)
fails, naming the job and the expected result.

A dependent job's condition, accepting `skipped` only for an unselected need:

```yaml
heavy:
  needs: [plan, static, light]
  if: >-
    ${{ !cancelled() && needs.static.result == 'success' &&
        needs.plan.outputs.heavy_selected == 'true' &&
        (needs.light.result == 'success' ||
         (needs.light.result == 'skipped' && needs.plan.outputs.light_selected != 'true')) }}
```

Rejected forms:

| Predicate | Why it is wrong |
|---|---|
| `needs.light.result != 'failure'` | A cancelled or selected-but-skipped light job passes |
| `needs.light.result == 'success' \|\| needs.light.result == 'skipped'` | A light job skipped because its own need failed passes |
| No status function and a `skipped` clause | The implied `success()` skips the job before the clause is read |
| Gate with `!cancelled()` | The gate can be skipped, and a skipped job reports success to required checks |

When a heavy job is skipped because a selected light job failed, the gate sees a selected heavy
job with result `skipped` and fails: that is the intended verdict. A re-run of failed jobs keeps
earlier successes, so the gate judges the combined attempts.
