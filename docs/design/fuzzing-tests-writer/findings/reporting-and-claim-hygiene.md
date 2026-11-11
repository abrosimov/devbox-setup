---
note_id: "20261103150206"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: finding
note_role: artifact
artifact_kind: finding
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Reporting and claim hygiene"]
tags: [fuzzing, design/finding, h6, h2]
addresses: ["[[H6-crash-counting-reports]]", "[[H2-no-stopping-rule]]"]
grounded_in: ["[[06-fuzzingbook-parts3-5|R6]]", "[[02-stopping-and-corpus-lifecycle|R2]]", "[[01-methods-and-applicability|R1]]"]
realised_by: ["[[skill-fuzzing-campaign]]"]
tested_by: ["[[eval-family-F-reporting]]", "[[eval-family-G-triage]]"]
related: ["[[stopping-algorithm]]", "[[corpus-lifecycle]]", "[[fuzzing-charter]]"]
---
# Reporting and claim hygiene

A report states what this research episode did, what its evidence supports and what persists for
the next session. It does not turn a process exit, local resource limit, quiet counter or saved
inputs into a claim that the research is answered or that the target is correct.
This applies C.16.IR: ask what distinction an observation resolves, retaining compatible
explanations until the available evidence separates them.

## Required report content

1. **Charter and subject:** objective, scope, repository revision and dirty-state context, target,
   oracle and assumptions; toolchain/engine versions, platform and instrumentation.
2. **Research disposition:** stable research identity, subject snapshot, ACTIVE/PAUSED/CLOSED
   state and reason; sufficient answer or remaining useful distinction. A pause names its resume
   condition; reopening names changed evidence and the affected conclusion.
3. **Accounting:** experiment/attempt identities, actual effort and applicable limits, interruptions
   and prior accumulated effort; local execution results remain separate from research state.
4. **Execution evidence:** commands, independently observed exits, raw logs, seed/corpus paths,
   engine-input and product-coverage observations with their measurement conditions. Mark missing
   measurements unavailable rather than inventing zeroes.
5. **Findings:** classification, symptom, preserved input, reproduction result and command,
   reduction status, evidence and remaining uncertainty.
6. **Replay handover:** useful inputs retained and where, their replay checks and any incomplete
   preservation; distinguish local saved files from authorised Git publication.
7. **Charter check:** each deliverable met or unmet, with evidence. State no finding within the
   actual tested scope when appropriate; residual risk is not quantified.
8. **User action only if blocked:** the concrete action and missing authority or information.
   Do not add an empty request section or ask for approval of routine design choices.

## Findings are separate from research state and experiment status

| Classification | Evidence required |
|---|---|
| Confirmed product failure | Reproduced violation of the product contract, with oracle and environment checked |
| Harness/oracle error | The check, input adaptation or harness behaviour contradicts its intended experiment |
| Environment failure | Toolchain, sandbox, filesystem, dependency or process failure explains the observation |
| Unconfirmed failure | A preserved candidate lacks enough evidence for the classifications above |
| No finding | No qualifying failure observed in the actual finite experiment |

Cluster related diagnostics to make triage manageable, but call these **candidate buckets**.
Matching stacks do not prove a common root cause; different stacks do not prove different bugs.
Do not force all timeouts or OOMs into one product bug, and do not count artefacts as confirmed
bugs. Report severity only with a grounded impact argument.

## Observation, supported conclusion and unresolved alternatives

| Observation | Supported conclusion | What it does not establish |
|---|---|---|
| No new reported features in a window | That engine reported no new features under those conditions | Saturation, absence of bugs, a broken harness or a mandatory strategy change |
| Zero execution-rate interval | The progress counter did not advance in that interval | A product hang; minimisation, startup or blocked infrastructure may explain it |
| Corpus gained inputs | Inputs were retained by the stated criterion | Source coverage, independent bug count or product safety |
| Valid-input ratio increased | More measured inputs passed that validation check | Deeper semantics were exercised or bugs became more likely |
| Grammar alternatives covered | Those grammar expansions occurred | Corresponding program paths were covered |
| A configured timeout was exceeded | That execution exceeded its bound | Exploitability, infinite execution or even product responsibility without attribution |
| Reproduction attempt interrupted or inconclusive | That attempt did not confirm the candidate | The original event was impossible or a false positive |
| Different discovery rates from different initial corpora | The recorded experiments differ | Improvement or decay attributable to the method alone |

A useful next observation needs an attainable contribution to the charter and proportionate effort
within authority. Record the reasoning to continue, pause or close under [[stopping-algorithm]];
remaining uncertainty alone does not create another experiment. Preserve the checkpoint and
applicable replay context across sessions. Engine exit code,
coverage report and reproduction result must come from the runner/tool evidence; a file written
by the evaluated agent asserting success is not independent verification.

The `go-kdl2`/`proj` histories are negative evidence for scope drift and misinterpretation, not
validation of their exploration policies. The
[phase-3 minimisation trace](https://github.com/abrosimov/go-kdl2/blob/f345e460f4cbe71020775802f5c90c9a5082f0f7/docs/roadmaps/kdl2-go-full-implementation/research/performance-and-fuzz-phase-3-evidence.md#L431-L485)
specifically supports separating engine work from target execution. [[eval-family-F-reporting]] and
[[eval-family-G-triage]] assess these distinctions without creating new product work.
