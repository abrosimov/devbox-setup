---
name: diagnose-and-repair
description: >
  Inventory-first diagnosis and batch repair for broken builds, failing validation suites,
  unhealthy services, VMs, containers, CI-like local checks, and other non-trivial debugging
  where multiple failures or cascading symptoms may exist. Use when an agent needs to discover
  the full failure set, group root causes, fix every currently actionable item, re-run the same
  broad baseline, or escape repeated unsuccessful repair attempts. Do not use for a known,
  genuinely isolated one-line defect with a single closure check.
---

# Diagnose and Repair

Use an inventory -> plan -> repair batch -> rebaseline loop. A narrow check may guide a repair,
but it cannot prove that the overall task is complete.

## 1. Define the evaluation

- State the target outcome, scope, success criteria, and permitted validation.
- Find the broadest relevant repository- or system-owned non-destructive check. Prefer an existing
  aggregate target, smoke test, health check, or CI-equivalent command.
- If the aggregate check stops at its first failure, identify its independent gates and run each
  gate once. Do not treat the first emitted error as the complete inventory.
- Ask once for the whole validation batch only when it is destructive, externally stateful,
  unusually expensive, or requires authority not already granted.

## 2. Establish the baseline before editing

- Run the evaluation and collect all observable failures, exit statuses, relevant service states,
  and bounded logs before applying fixes, unless the run itself would be unsafe.
- Record one row per failure:

  `ID | failing check or symptom | evidence | likely layer/root cause | dependency | status | closure check`

- Mark duplicates, cascades, blocked rows, and out-of-scope rows explicitly. Do not count ten
  downstream errors caused by one unavailable dependency as ten independent root causes.
- Preserve the baseline command set so every later iteration evaluates the same contract.

## 3. Plan the repair batch

- Group rows by shared cause and order them by dependency: environment and infrastructure before
  services, services before integrations, integrations before downstream assertions.
- Select every unblocked, in-scope row for the current batch. Independent read-heavy investigation
  may run concurrently when the client and current instructions permit it; keep overlapping writes
  serial and retain one owner for the ledger.
- For each row, define the smallest plausible repair and the evidence that will close it.

## 4. Repair all actionable rows

- Work through the entire planned batch. Do not stop merely because the first failure is fixed or
  one narrow check turns green.
- After a risky change, run the narrow closure check for fast feedback and update the ledger.
- When evidence invalidates a suspected cause, reclassify the row before making another change.
- Do not rerun an unchanged command unless relevant state changed or the rerun collects new evidence.

## 5. Rebaseline and iterate

- Run the original broad evaluation again after the batch.
- Reconcile every row as closed, still failing, changed, regressed, newly exposed, blocked, or
  out of scope. Add new failures rather than silently replacing the old inventory.
- Build the next batch from all currently unblocked rows and repeat until the success criteria hold.

## Stagnation and context health

Switch strategy instead of blind retry when either condition holds:

- the same row survives two materially different evidence-based repair attempts; or
- a full repair/rebaseline iteration produces no net reduction in unresolved root causes.

At that point, challenge the assumed layer and reproduction, gather different evidence, or hand a
compact ledger and baseline to a fresh agent/session. Do not continue accumulating speculative
patches in a degraded long-running context.

## Stop conditions

Stop only when one of these is true:

- the original broad evaluation and all in-scope closure checks pass;
- a genuine blocker requires user authority, unavailable external state, or a material scope change;
- the remaining rows are explicitly out of scope and reported with evidence.

Never report completion while an observed in-scope failure remains unclassified or merely hidden by
a narrower validation command.
