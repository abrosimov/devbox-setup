---
note_id: "20261104100004"
created: 2026-11-04
modified: 2026-11-04
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: reference
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["PBT agent prompts", "Hypothesis command and agentic-pbt"]
tags: [fuzzing, design/framing]
grounded_in: ["[[08-lang-python|R8]]"]
related: ["[[fuzzing-vs-pbt-boundary]]", "[[oracle-ladder]]", "[[reporting-and-claim-hygiene]]"]
opens: ["[[FTW-OQ-011-agentic-pbt-validity]]"]
---
# The two existing PBT agent prompts — what they are and what this agent borrows

Both are **property-based-testing** prompts (R8 §3.5), recorded here as the only published,
evaluated agent procedures in the neighbourhood of this agent ([[fuzzing-vs-pbt-boundary]]).

## 1. Hypothesis' own `.claude/commands/hypothesis.md` (HypothesisWorks/hypothesis, master)

- Goal: "a small number of high-value tests"; propose only properties the agent "strongly believes
  are true", with evidence from docstrings, comments, usage and type hints.
- Exploration order: public API → documented core → other core → private helpers.
- Property catalogue: round-trip, inverse, equivalent implementations, idempotence, commutativity,
  invariants, confluence, metamorphic, single entry point, stateful.
- Properties a unit test covers equally well "are not particularly valuable".
- Strategies "sound and ~90 % complete"; "only place constraints on Hypothesis strategies if
  required by the code"; stateful model "as simple as possible, usually a plain list or dict".
- After confirming a bug, add the minimal input as `@example`; "if nothing valuable turns up, say
  so and stop".

## 2. Anthropic's `agentic-pbt` `hypo.md` (mmaaz-git/agentic-pbt; arXiv 2510.09907, Maaz, DeVoe,
Hatfield-Dodds, Carlini, 2025-10)

- Pipeline: analyse → understand (introspection, follow private import chains) → propose → write →
  run → triage (reproducibility, legitimacy, impact) → report.
- "Prefer sound but incomplete properties"; "do not constrain strategies unnecessarily";
  `math.isclose` / `pytest.approx` for floats.
- Outcomes are one of: bugs / no bugs / inconclusive; "one real bug discovery > 100 passing tests".
- Evaluation: 100 packages (15 PyPI, 15 stdlib, 70 random); an LLM graded reports with a rubric.
- Reported validity of agent-found bugs: 56 % valid, 32 % worth reporting on a 50-report sample —
  **UNVERIFIED** (search snippets only; the paper host was unreachable;
  [[FTW-OQ-011-agentic-pbt-validity]]).

## What this fuzzing agent borrows (and rewrites in fuzzing terms)

| Borrowed discipline | Fuzzing form in this design |
|---|---|
| Evidence before proposing | the charter's *objective* must name plausible bug classes from the code's input kind and history ([[fuzzing-charter]]) |
| Triage rubric: reproducible → legitimate → impactful | the triage step of [[agent-procedure]] and [[reporting-and-claim-hygiene]]: reproduce three times, check the contract (`Must*`, documented preconditions), bucket, then file |
| "Say so and stop" when nothing valuable exists | the gate's `do-not-fuzz` / `out-of-scope` outcomes and the `STOP_SATURATED_AT_BUDGET` decision with its coverage evidence |
| Outcome taxonomy bugs / no bugs / inconclusive | decision tokens plus bucket list; "inconclusive" = `BLOCKED_HARNESS` or discoverability failure |
| Few high-value targets over many | one format or API family per target; attention allocation across targets by discovery rate |

Not borrowed, because it belongs to the PBT agent: strategy design, the property catalogue as a
deliverable, `@example` pinning, stateful models, Ghostwriter, the "sound and ~90 % complete"
strategy rule, and the evaluation design over PyPI packages. That agent, when it is built, starts
from these two prompts.
