---
name: comparison-frame
description: >
  Build the scales before comparing options: object kind and use, three contrast cases, one
  characteristic per coordinate on one declared scale, floors never traded, budgets,
  protected trade-offs, comparator and basis, stop condition. Use before any pros-and-cons
  table or decision card.
problem: "Options get compared on scores nobody declared, so the easiest number wins, correctness is traded for a proxy, and no one can say when the comparison is done."
related: [fpf-thinking, diverge-synthesize-select, response-templates, writing-for-the-reader]
---

# Comparison frame

A comparison is only as good as the scales it is made on. `diverge-synthesize-select` generates
candidates and presents the card; this skill builds what the card's evaluation step compares
them on, and it builds it first. The method is FPF's: `A.17` names what is measured, `A.18`
binds it to one scale, `A.19` declares the space, `A.19.ECS` says what counts as better for one
object kind and use, `C.16` makes a number interpretable, `E.13` keeps a proxy from becoming
the objective, `A.19.CPM` compares. Read the pattern's `Solution` through `fpf-thinking` when a
step below is in doubt.

## When to use it

- Before step 4 of `diverge-synthesize-select`, before any pros-and-cons table, and before a
  benchmark or a "this is faster" claim is relied on.
- When a comparison exists and any of these holds: a number has no declared scale or unit; a
  number depends on the machine it was taken on; ordinal scores were averaged; one score
  decides; a figure keeps improving past the point where the use needs it; correctness or
  completeness appears only as a footnote under a performance figure.
- Not when one measure on one declared scale already answers "what would make this claim
  false?" (`C.25`): state that characteristic and stop. Not for a choice below the
  decision threshold, where a one-line default is enough.

## Procedure

### 1. Name the object kind and the use

One sentence: *good as what kind of object, for which use, judged by whom, over which window.*
"A gate run of one directory by one release on one runner, for deciding where the tier runs in
CI, judged by the owner, until the pins or the runner change." If the object kind cannot be
named, stop here: no coordinate is meaningful yet.

### 2. Write three contrast cases

Before any coordinate: one object that must pass, one of the same kind that must fail the
floor, one that is outside the kind and must be refused rather than scored (a run on other
pins, a benchmark on other hardware, a candidate that solves a different problem). A frame that
cannot tell these three apart is not ready.

### 3. Find the characteristics from failure modes, not from available numbers

List what would make the object bad for the use: what breaks, who is harmed, what the user
loses. Each becomes a candidate characteristic. Then:

- split a compound one (`quality`, `performance`, `maintainability`) into the characteristics
  that would each be repaired by a different action;
- drop one that does not change what you would do, duplicates another without a different
  repair, or belongs to a different object kind;
- keep every characteristic that the failure modes demand even when it has no convenient
  number yet — an unmeasured characteristic is written down with its missingness rule, not
  omitted.

### 4. Bind each characteristic to one scale

For each coordinate state: the scale kind (nominal, ordinal, interval, ratio) and its values;
what each value means; whether the value is a measurement or a judgement; what a missing
value means. For a measured number add `C.16`'s account: the measurand, the method, the
conditions it depends on (hardware, versions, seeds, data), the uncertainty and how it is
handled (repeat runs, which value is taken), and the window in which the value stays valid.
A number that depends on conditions is comparable only within them; name the basis and
say so.

| Scale | Admissible operations | Not admissible |
|-------|------------------------|----------------|
| nominal (equal, differs, not run) | equality, counts per value | any order or arithmetic |
| ordinal (weak, adequate, strong; bounded < inductive < proved) | order, median | averaging, differences |
| interval | differences | ratios |
| ratio (seconds, states, bytes) | all arithmetic, within one basis | comparison across bases |

### 5. Classify each coordinate by its role

Three roles, decided before any value is read:

- **Floor.** Must be met; never traded for another coordinate. Correctness, completeness,
  soundness, safety belong here by default. A candidate below a floor is out, however it
  scores elsewhere.
- **Budget.** Must stay within a limit set by the use (a job timeout, a memory ceiling, a
  cost). Past the limit nothing is gained; "better" stops at the line. Type its proxy use as
  `E.13` does: a budget is a gate, not a target.
- **Optimised or orientation.** Lower or higher is preferred, and the frame says which;
  or the coordinate is read for understanding and never for ranking (per-check time,
  per-file counts).

Then name the protected trade-offs: for each optimised coordinate, which floor or other
coordinate could silently worsen while it improves, and how that will be seen.

### 6. Declare the comparator and the basis

State how two candidates are compared: on which coordinates, in which order of roles (floors,
then budgets, then optimised), with what tie rule, and whether a composite index is used. If
one is, publish its weights, keep the primitive coordinates visible, and never average ordinal
values. The outcome is set-valued: a candidate dominates, is dominated, or is incomparable;
incomparable is a result, not a failure of the frame. Comparisons are made within one basis;
a change of versions, hardware, seeds or corpus is a new basis, and results across bases need
a change account naming what moved.

### 7. State floor, stop and reopen

When is the comparison done: every floor met, every budget within its limit, and the optimised
coordinates compared under the comparator. When does it reopen: the object kind, use, basis,
or a contrast case changes, or a protected trade-off was found to have moved. No "exceptional"
tier unless the use defines one; a floor question stays a floor question.

### 8. Fix the result row

Every value is recorded as: coordinate, value, basis, evidence locus, one-line rationale.
A table of values without rationale and basis is an impression, not a comparison.

### 9. Hand the frame to the comparison

Give `diverge-synthesize-select` the frame instead of its default criteria table: its
`strong / adequate / weak` becomes an ordinal coordinate with declared meanings, its
"dropped" becomes "below a floor" with the floor named, and its synergy search runs over the
coordinates where candidates are incomparable.

## Worked slice

Object: a run of a model-checking gate by one tool release on one runner, for deciding whether
the gate may run per pull request. Contrast cases: a run with every outcome equal to the
reference inside the timeout; a run two minutes faster with one outcome different; a run on
other pins. Floors: outcome agreement per check (nominal), violated property named (nominal),
kept evidence equal (nominal). Budget: wall time on the named runner against the job timeout,
the larger of two runs, valid until the basis changes. Orientation: time per check.
Machine-independent cost for ranking, if ever needed: distinct states, tool invocations, JVM
starts, SMT problem count. Protected trade-off: a change that saves time by adding a second
code path is accepted only with that cost named. Stop: floors met and budget held on two runs.
Nothing in the frame rewards being faster than the budget.

## Pitfalls

| Pitfall | What prevents it |
|---------|------------------|
| The easiest number becomes the criterion | Characteristics from failure modes (step 3) before any value exists |
| Performance outranks correctness | Roles (step 5): correctness is a floor, time is a budget |
| "It improved" with no threshold or basis | A budget has a limit from the use; an optimised coordinate has a comparator and a basis |
| Hardware-dependent number compared across machines | `C.16` conditions and basis in step 4; cross-basis comparison needs a change account |
| Ordinal scores averaged into one figure | Admissible operations table; set-valued outcome |
| A proxy gated, then targeted | `E.13` proxy-use typing in step 5 |
| Coordinates that change nothing | Drop rule in step 3 |
| Frame rebuilt for every small choice | Threshold in "When to use it"; below it, a default and a reason |

## Follow-ups

| The user says | You do |
|---------------|--------|
| "Add a criterion" | Run steps 3–5 for it: characteristic, scale, role, protected trade-off; values of other candidates stay |
| "Why is X out?" | Name the floor it failed and the evidence row |
| "Just give me a score" | Give the set-valued outcome and, if an index is insisted on, its weights beside the primitive coordinates |
| "The numbers moved" | Check the basis first; a basis change is a new comparison, not a trend |
