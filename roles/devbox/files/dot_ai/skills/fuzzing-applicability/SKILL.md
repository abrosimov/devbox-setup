---
name: fuzzing-applicability
description: Assess a target, input domain and oracle for a scoped fuzzing investigation.
---

# Fuzzing applicability

Return an evidenced target/method/oracle choice, a bounded check of a missing prerequisite, or a
reasoned non-fuzz disposition. Work within the requested area and permitted effects. This workflow
does not create PBT, mutation analysis, product fixes or another testing programme.

## Recover the assignment

Read the repository instructions, relevant contract, current tests, existing fuzz targets and useful
corpora. Recover earlier attempts and conclusions before proposing work. Bind the assessment to
the relevant commit plus dirty changes, experiment configuration and dataset selection/version.
An unchanged assessment can be reused; a new session alone is no reason to repeat it.

If no precise question exists, examine concrete material through a bounded reconnaissance pass:
name the input/code area, feasible inspection or replay operation, kind of possible knowledge gain
and effort limit. The pass may discover the question. Do not require a predicted bug or proof of
the usefulness of an unknown discovery. Return observations and their limits instead of indefinitely
enumerating targets.

## Establish a usable target

| Check | Inspect | Result needed |
|---|---|---|
| Behaviour and scope | Entry point, owned transformations and relevant product contract | A meaningful behaviour to exercise within the assignment |
| Input path | Bytes, text, primitives or an explicitly bounded decoder/operation sequence | Inputs that can reach the target through a supported engine interface |
| Observation | Target calls, expected rejection, relevant checks and instrumentation | A way to tell what was executed and what a failure would mean |
| Replay | Setup/reset, time/randomness, filesystem/network dependencies and corpus encoding | Reproducible calls with controlled effects or a named unavailable prerequisite |
| Useful contribution | Existing coverage of the question and available new material | An experiment or reconnaissance that can contribute at proportionate cost |

An upstream fuzz target does not establish the safety of local transformations. Conversely, a thin
wrapper or already exhaustively checked finite domain need not receive a redundant harness.
Explain the local judgement. Network or filesystem use calls for an appropriate isolation boundary;
it is not a universal reason to reject the target. Do not refactor production code to manufacture
a target or invent an adversary outside the task.

## Choose and qualify the oracle

Use a contract-backed failure predicate and the simplest method that supplies the intended
observation. Read [Oracle selection](references/oracles.md) when choosing a semantic, differential
or resource check, or when an assertion's meaning is uncertain.

Exercise known valid and intentionally invalid inputs and an existing known failing case where
available. Establish expected outcomes from the contract or independently specified examples,
not solely from the new harness. An assertion failure is initially a candidate: the oracle itself
may be wrong. Do not invent a product defect or modify product code to validate the oracle.

Missing semantics can leave a particular assertion unqualified while a narrower independently
justified check remains usable. State its limits. If meaningful execution cannot be established,
return the precise gap and whether a scoped next check is possible.

## Preserve the current contribution

Before constructing a harness, record the target, observation/oracle basis, scope and practical
limits in the repository's existing research note or artefact convention. Preserve the research
identity across sessions. Include:

- question and intended use, or reconnaissance material and learning aim;
- subject versions, relevant assumptions, prior evidence and useful corpus paths;
- selected operation, expected contribution, completion evidence and cost/resource limits;
- missing prerequisites and the next usable result or reason to stop.

The caller can pass that material to the relevant language harness operation or `fuzzing-campaign`
when available. Do not label unresolved evidence as `do-not-fuzz`: distinguish missing information,
unsupported technique and a justified negative assessment. A non-fuzz result completes this
assessment without commissioning an alternate suite.
