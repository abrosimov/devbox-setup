---
name: fpf-thinking
description: Use First Principles Framework (FPF) patterns to frame complex systems questions before solving them. Use for system boundaries, domain modelling, architecture, problem shaping, evidence and assurance, option comparison, causal or temporal claims, naming, and costly decisions. Do not use for routine local edits or for rendering an already-framed subject as a narrative; use narrative-thinking for that.
---

# FPF-guided systems thinking

Use FPF as a reasoning scaffold for complex systems work. Keep the response in plain language and
ground it in the user's actual situation. Framework vocabulary is useful only when it makes a
distinction more precise.

## References

Resolve these paths relative to this `SKILL.md`:

- `references/FPF-Spec.md` — FPF Core, owning `A.*` through `G.*` ids.
- `references/Narrativization-and-Narrative-Studies-Principles-Framework.md` — the companion NSTD
  framework. Use it through the sibling `narrative-thinking` skill.

Both documents are large. Never load either file in full. Search by stable section id, enumerate the
matching section's headings, then read only the relevant range. Titles, line numbers, slot numbers,
and document size may change between editions.

For example, locate a pattern and enumerate its slots with targeted searches equivalent to:

```text
rg -n '^#{1,6} A\.1(?:\s|:)' references/FPF-Spec.md
rg -n '^#{1,6} C\.11:' references/FPF-Spec.md
```

Use the `:End` heading as the pattern boundary. Search for a distinctive slot title such as
`Solution`, `Conformance`, `Rationale`, or `Relations` instead of assuming its slot number.

## Workflow

1. Decide whether the live question needs FPF. Skip it for straightforward implementation,
   factual lookup, or a decision whose frame and criteria are already explicit.
2. Identify the current situation and choose one Practical-Use Card from the index below. If two
   cards appear plausible, compare their promised first results before opening either pattern.
3. Open only the direct branch whose stated condition is current. Read its `Solution` and, when the
   answer will be relied on, its `Conformance Checklist`.
4. Combine the selected pattern with repository, source, or user evidence. FPF never substitutes
   for missing facts.
5. Return the smallest useful result for the current use. Do not walk stronger neighbours unless a
   new live claim requires them.
6. Close with the Result test.

Do not expose private chain-of-thought. Present conclusions, evidence, assumptions, alternatives,
and concise rationale sufficient for the user to inspect the result.

## Practical-Use Card index

| Card | Use when | Direct patterns |
|---|---|---|
| `ARCHITECTURE` | Pressure must become candidate, selected, expected, or actual structure | `C.32.P2S`, `C.30.AD` |
| `WORKING-DOCUMENTS` | A participant will use a document for meaning, enactment, reliance, or publication | `A.6`, `A.3.2`, `A.2.8`, `A.6.RSIR`, `A.15.2`, `C.24`, `A.10`, `E.17` |
| `OPTION-COMPARISON` | Options need a comparison frame, archive, live pool, published set, or choice | `A.19.ECS`, `C.18`, `C.19`, `G.5`, `C.11` |
| `PROBLEM-SHAPING` | Vague pressure has not yet become an honest problem or task | `A.16.1`, `B.4.1`, `B.5.2.0`, `C.22.2`, `C.22` |
| `IMPROVEMENT` | Evaluation purpose, scale, or proposed effect is unsettled | `E.22`, `C.25`, `A.19.ECS`, `E.23` |
| `COSTLY-ACTION` | An action is expensive, committing, safety-relevant, or hard to reverse | `A.10`, `B.3`, `A.20`, `A.21`, `C.28`, `C.11`, `A.15.5` |
| `TIME` | A rate, delay, trend, currentness, or validity-window claim supports action | `C.27`, `G.11` |
| `CAUSAL-USE` | A causal, intervention, effect, or counterfactual claim supports a decision | `C.28` |
| `DESCRIPTION-USE` | A model, view, dashboard, report, or publication is being created or relied on | `E.17.0`, `A.6.3.RT`, `C.33`, `E.17.ID.CR`, `C.30.AD` |
| `NAMING` | A governed value needs a stable name in a bounded context | `F.18`, then `F.17` and `E.24.PUB` only when publication is current |
| `WORDING` | Fluent prose hides what relation or project claim is actually being made | `E.10`, `A.6.5`, `A.6.P`, `A.6.RCD`, `A.6.P.WMR`, `F.19` |
| `MATHEMATICAL-MODELLING` | One cheap mathematical lens could change the next admissible action | `C.29` |
| `SOTA-PORTFOLIO` | The plural current field of methods, theories, technologies, or sources is needed | `G.2`, then conditionally `C.18`, `C.19`, `G.5` |
| `DPF-AUTHORING` | A reusable FPF-grounded domain or practice framework is being built | `E.4.DPF`, `E.4.PFAD`, `C.30.AD` |
| `SYSTEM-IN-CONTEXT` | A system is named but identity, composition, participation, work, or production is unclear | `A.1`, `B.1.2`, `C.30`, `A.15.2`, `A.15.1`, `A.15.PROD` |

The rows are routing choices, not a checklist. A branch promises what a later use could return; it
does not prove that the result already exists.

## Semantic fallback

Use this only when no Practical-Use Card clearly matches:

| Question | Starting patterns |
|---|---|
| What is this system or project? | `A.1`, `A.1.1`, `A.2` |
| How confident are we in this claim? | `B.3`, `A.10`, `B.3.4` |
| What does success mean and how is it measured? | `A.17`, `A.18`, `A.19.CN`, `G.0`, `G.11` |
| What does this term mean across contexts? | `F.0.1`, `F.3`, `F.9`, `F.17`, `F.18` |
| How should this evolve? | `B.4`, `A.4`, `E.9`, `E.18.1` |
| How do several transformation flows connect? | `E.18`, `E.18.NET`, `E.18.3`, `A.15.6` |
| Who does what and why? | `A.2`, `A.15`, `A.2.1`, `A.13` |
| What are the boundary contracts? | `A.6`, `A.6.B`, `A.6.C`, `A.2.3` |
| How should tool use be planned? | `C.24`, `A.15`, `A.13` |
| Is X actually causing Y? | `C.28` |
| What ethical trade-offs are live? | `D.1`, `D.2`, `D.3`, `D.4`, `D.5` |
| How should an architecture be designed or criticised? | `C.30`, `C.31`, `C.32`, `C.33`, `C.34`, `C.35`, `A.22.CGUS` |

## Result test

Close every FPF-guided result by establishing:

1. **Result kind** — what exact result the selected branch can honestly return.
2. **Receiving use** — the decision, method, plan, evaluation, transformation, gate, or publication
   occurrence that will use it.
3. **Binding** — what direct relation, application binding, or well-formed local claim makes this
   result valid for that use.

If a required governor or fact is missing, name it and stop. Do not weaken the claim merely to
produce an answer. A note, plan, dashboard, ticket, or generated document is a carrier, not proof
that its downstream effect occurred.

## Useful renderings

Use these only when they match the selected pattern's result:

- **System characterisation:** name, boundary, parts, roles, context rules, bridges.
- **Trust assessment:** claim, scope, formality, evidence chain, reliability, verdict.
- **Comparison frame:** characteristics, indicators, comparability rules, aggregation policy,
  protected trade-offs.
- **Name card:** governed value, context and sense, candidate labels, rejections, bridges, reopen
  condition.
- **Design rationale:** context, choice, alternatives, evidence, consequences, review trigger.
- **Evolution roadmap:** evidenced current state, measurable target, steps, feedback, evidence
  refresh.
- **State-of-the-art pack:** scope, rival traditions, method families, comparison frame, viable
  portfolio, evidence gaps.

Default to an inline conversational result. Persist an artefact only when the user asks for one or
when the requested task explicitly requires a file. Follow the repository's existing location and
naming conventions rather than inventing a global FPF path scheme.

## Boundaries

- Use FPF for systems thinking, not as a replacement for language-specific engineering skills.
- Use `narrative-thinking` when the problem is already framed and the task is to explain, teach, or
  narrate it without outrunning the source.
- Use option-generation or sequential-reasoning aids only when they add something to the selected
  FPF branch; they are not mandatory dependencies.
- Prefer a small portfolio with explicit trade-offs over an unsupported single-winner conclusion.
- Do not load all cards, all neighbours, or an entire reference to demonstrate thoroughness.
