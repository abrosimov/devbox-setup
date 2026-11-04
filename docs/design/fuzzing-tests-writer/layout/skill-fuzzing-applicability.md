---
note_id: "20261103150402"
created: 2026-11-03
modified: 2026-11-04
language: en
type: design
subtype: skill
note_role: artifact
artifact_kind: skill
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["Skill: fuzzing-applicability", "fuzzing-applicability"]
tags: [fuzzing, design/component, design/skill, h1, h4, h7]
addresses: ["[[H1-no-applicability-gate]]", "[[H4-crash-only-oracle]]", "[[H7-no-objective-before-work]]"]
realises: ["[[applicability-gate]]", "[[fuzzing-vs-pbt-boundary]]", "[[fuzzing-charter]]", "[[oracle-ladder]]"]
tested_by: ["[[eval-family-A-gate]]", "[[eval-family-B-oracle]]", "[[eval-family-H-charter]]"]
decided_by: ["[[FTW-D-001-gate-is-first-step]]", "[[FTW-D-002-six-skills]]", "[[FTW-D-008-pbt-out-of-scope]]", "[[FTW-D-009-charter-before-work]]"]
target_path: "roles/devbox/files/dot_ai/skills/fuzzing-applicability/"
codex_shared: true
related: ["[[reference-documents]]", "[[pbt-agent-prompts]]"]
---
# Skill `fuzzing-applicability`

**Problem** (frontmatter `problem:`): agents fuzz everything they are pointed at, start harnesses
before stating what the campaign must establish, blur fuzzing with property-based testing, and
accept "does not crash" as the oracle in memory-safe code.

## Carries

1. **Gate tables** of [[applicability-gate]]: hard stops, fuzz-or-out-of-scope rows and the seven
   preconditions, each with its evidence, and the one-line outcome with its matching row quoted.
2. **Fuzzing-versus-PBT boundary**: the definitions table and the tool-by-tool table of
   [[fuzzing-vs-pbt-boundary]], with the conditions under which a hybrid bridge is allowed.
3. **Charter** template and rules of [[fuzzing-charter]].
4. **Oracle ladder** of [[oracle-ladder]] in fuzz-target form: contract-statement header; round-trip,
   differential and invariant checks inside the target; resource limits; the ecosystem facts that
   change what the bottom rungs see.
5. **Borrowed discipline** of [[pbt-agent-prompts]] in its fuzzing form.
6. **Anti-pattern list** with the evidence behind each entry (R1 §3.12), and pairwise option
   testing as the answer for flag spaces (R6 §5.4).

≤ 300 lines of decision tables; references `bug-class-evidence.md` and `fuzzingbook-map.md`
([[reference-documents]]).

## Evals shipped with the skill

`evals/trigger_evals.json` (~20 queries; positives: "should we fuzz this parser", "add a fuzz target
for the decoder", "is fuzzing worth it here", "define the goal of the fuzzing campaign"; near-miss
negatives: "add table-driven tests for the parser", "write a Hypothesis property for this
function", "fuzzy-match these strings", "speed up the CI test job") and `evals/evals.json` with
the gate and charter cases of [[eval-family-A-gate]] and [[eval-family-H-charter]].
