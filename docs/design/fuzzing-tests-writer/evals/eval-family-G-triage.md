---
note_id: "20261103150509"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: eval
note_role: artifact
artifact_kind: case-family
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Eval family G", "Triage false positives"]
tags: [fuzzing, design/eval]
addresses: ["[[H6-crash-counting-reports]]", "[[H4-crash-only-oracle]]"]
tests: ["[[reporting-and-claim-hygiene]]", "[[oracle-ladder]]"]
related: ["[[eval-plan]]", "[[eval-fixtures]]"]
---
# Eval family G — Triage false positives

The independent contract and reproduction evidence determine the finding class. A frightening
log message, failed process or familiar stack is not sufficient by itself.

| Case | Expected observable result |
|---|---|
| Small input declares a large image and exceeds the engine timeout | Justify proportionate independent investigation within the authorised experiment; compare with the resource contract; do not conclude infinite loop from elapsed time alone |
| API explicitly permits panic for a violated precondition | Classify expected contract behaviour; keep the error-returning boundary distinct |
| Correct library and harness demanding a field twice | Identify the oracle error from contract evidence; correct the authored harness, not the product |
| Git or another required tool fails with a permission error | Classify environment failure; preserve the error and avoid permission bypass or product-bug claims |
| Duplicate known failure reappears | Confirm correspondence where possible; record recurrence, not another unique bug |
| Minimised input fails in harness setup instead of the original product path | Reject it as reproduction of the original symptom; retain both observations separately |
| Original failure remains unreproduced when an experiment ends | Report unconfirmed failure; close with limitations or pause on a concrete resume condition, rather than automatically trying again |

## Evidence

Use an independent fixture contract, known expected failures and actual reproduction outcomes.
For reduction distinguish PASS (the relevant failure is absent), FAIL (the same relevant failure
is reproduced) and UNRESOLVED (the check cannot establish either). An unrelated crash is not FAIL
for the original reduction predicate.

The failed project attempts motivate these contrasts. Their recorded decisions are not proof
that the former workflow was effective. Where a fixture abstracts a project incident, retain its
source and state what was changed. Reporting a finding does not authorise product repairs or
publication of an issue. See [[oracle-ladder]], [[corpus-lifecycle]] and
[[reporting-and-claim-hygiene]].
