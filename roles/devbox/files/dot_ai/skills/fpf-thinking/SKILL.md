---
name: fpf-thinking
description: Use First Principles Framework (FPF) Library patterns — FPF Core and its Domain Principle Frameworks (DPFs) — to frame complex questions before solving them. Use for system boundaries, domain modelling, architecture, problem shaping, evidence and assurance, option comparison, causal or temporal claims, naming, costly decisions, and domain methods such as systems engineering, agent procedures, knowledge-corpus access, notation design, decision design, and research method. Do not use for routine local edits or for rendering an already-framed subject as a narrative; use narrative-thinking for that.
---

# FPF-guided systems thinking

Use the FPF Library as a reasoning scaffold for complex work. Keep the response in plain language
and ground it in the user's actual situation. Framework vocabulary is useful only when it makes a
distinction more precise.

## References

Resolve these paths relative to this `SKILL.md`:

- `references/USING-FPF.md` — upstream's reading rules for people and agents. Follow them; this
  skill only adds the local routing below.
- `references/FPF-Spec.md` — FPF Core, owning `A.*` through `G.*` ids. Its `## Practical entries`
  section is the authoritative list of practical entries and Practical-Use Cards.
- `references/DPFs/README.md` — catalogue of the Domain Principle Frameworks: four Suites, each
  with its own README and Suite Reference, plus standalone frameworks.
- `references/DPFs/Narrativization-and-Narrative-Studies-Principles-Framework.md` — NSTD. Use it
  through the sibling `narrative-thinking` skill.
- `references/FPF-LIBRARY-REFERENCE.md` — boundaries and connections across Core and the DPFs.
- [Bundle index](references/bundle-index.md) — snapshot provenance and maintenance.

A DPF pattern id (`SYSE.47`, `PSDA.1`) belongs to its own file, not to FPF Core. These documents are
large. Never load a complete framework or the whole bundle. Search by heading id within the selected
document, enumerate the matching section's headings, then read only the relevant range. Titles,
line numbers, slot numbers and document size change between editions.

```text
rg -n '^#{3,5} [A-Z][A-Z-]+ [—-] ' references/FPF-Spec.md        # practical entries and cards
rg -n '^#{1,6} C\.11(?:\s|:)' references/FPF-Spec.md              # one Core pattern
rg -n '^## SYSE\.47\s*[-—]' 'references/DPFs/Engineering DPF Suite/SYSTEMS-ENGINEERING-PRINCIPLES-FRAMEWORK.md'
rg -l -i 'stale cache|invalidat' references/                       # difficulty words, all files
```

DPF headings use either a hyphen or an em dash after the id, so accept both. Use the `:End` heading
as the pattern boundary. Search for a distinctive slot title such as `Solution`, `Conformance`,
`Rationale` or `Relations` instead of assuming its slot number.

## Workflow

1. Decide whether the live question needs FPF. Skip it for straightforward implementation,
   factual lookup, or a decision whose frame and criteria are already explicit.
2. Start from the receiving work: name the decision, plan, method or publication that will use the
   result. `C.39` says when a contribution is sufficient for that use; `C.11.DUA` says when an
   advice or evidence demand is not worth its burden.
3. Find an entry, in this order:
   - **Core practical entry or card.** Enumerate the headings under `## Practical entries` in
     `FPF-Spec.md` and choose the one whose title matches the situation. If two cards look
     plausible, compare their promised first results before opening either. The entry names its
     direct patterns.
   - **Domain method.** When the question needs a field's methods, use the domain routing table
     below, or the Suite README for a Suite it does not list.
   - **Neither.** Search Core and every DPF together with words describing the difficulty. A
     missing hit does not prove the method is absent; record the remaining search gap.
4. Check the selected pattern's problem frame before applying it. Read its `Solution` and, when the
   answer will be relied on, its `Conformance Checklist`.
5. Combine the pattern with repository, source or user evidence. FPF never substitutes for missing
   facts. A citation names a source; it does not make the method applicable (`E.11.PUA`).
6. When the answer joins results from several patterns or frameworks, check each result is
   qualified, each fits its receiving use, and the combination meets its shared conditions. Use
   `A.15.9` when one practice uses a bounded result from another.
7. Return the smallest useful result. Do not walk stronger neighbours unless a new live claim
   requires them. Close with the Result test.

When the purpose is to extend what an agent, person or team can do over continuing work, use
`C.40.OD` with the relevant domain methods rather than a one-off pattern.

Do not expose private chain-of-thought. Present conclusions, evidence, assumptions, alternatives,
and concise rationale sufficient for the user to inspect the result.

## Domain framework routing

Core owns a question when one of its practical entries matches. Choosing among options the chooser
already has is `C.11`; an unsettled choice of how to obtain a result is `C.38`; mapping a plural
field of methods is `G.2`; one cheap mathematical lens is `C.29`. Open a DPF when the question
needs its field's methods. Paths are relative to `references/DPFs/`.

| Use when | Framework | File | Entry patterns |
|---|---|---|---|
| Choosing how to obtain an engineering result (build, buy, reuse); deciding or reopening architecture | Systems Engineering | `Engineering DPF Suite/SYSTEMS-ENGINEERING-PRINCIPLES-FRAMEWORK.md` | SYSE.24, SYSE.6, SYSE.2 |
| Repeatable builds, fast trustworthy CI, deployment, restoring a failed platform task | Systems Engineering | same | SYSE.30, SYSE.31, SYSE.41, SYSE.38 |
| Constructing, testing or splitting an AI agent's procedure, memory or effort | Systems Engineering | same | SYSE.47, SYSE.46, SYSE.44, SYSE.43, SYSE.51 |
| Readers cannot find or trust the right passage in a changing document corpus | Knowledge-Corpus Access | `Engineering DPF Suite/KNOWLEDGE-CORPUS-ACCESS-ENGINEERING-PRINCIPLES-FRAMEWORK.md` | KCAE.USE, KCAE.SEARCH, KCAE.CHANGE, KCAE.MEMORY |
| Separately governed sources or engines disagree on meaning or identity | Semantic Integration | `Engineering DPF Suite/SEMANTIC-INTEGRATION-ENGINEERING-PRINCIPLES-FRAMEWORK.md` | SIE.1, SIE.4, SIE.11 |
| Representation or algorithm choice, interpreters and translations, composing computations | Computational Thinking | `Foundational Thinking DPF Suite/COMPUTATIONAL-THINKING-DPF.md` | CMP.10, CMP.12, CMP.14, CMP.15 |
| Designing a DSL, schema or notation; keeping several representations consistent | Notational Engineering | `Foundational Thinking DPF Suite/NOTATIONAL-ENGINEERING-DPF.md` | NOT.1, NOT.5, NOT.6, NOT.7 |
| A full model must be built, identified from data or validated | Mathematical Modeling | `Foundational Thinking DPF Suite/MATHEMATICAL-MODELING-PRACTICE-DPF.md` | MMP.8, MMP.15, MMP.16 |
| Framings are contested, alternatives are missing, or the comparison may flip | Decision Design (PSDA) | `DECISION-DESIGN-PRINCIPLES-FRAMEWORK.md` | PSDA.1, PSDA.5, PSDA.6, PSDA.8, PSDA.9, PSDA.14 |
| Whether a question needs research; criticising a claim; synthesising a source corpus | Research Method Practice | `RESEARCH-METHOD-PRACTICE-PRINCIPLES-FRAMEWORK.md` | RMP.1, RMP.2, RMP.5, RMP.7 |
| A recipient must understand something well enough to act; repairing an explanation | Explanation Design (EXD) | `EXPLANATION-DESIGN-PRINCIPLES-FRAMEWORK.md` | EXD.1, EXD.4, EXD.6 |
| Limiting work in progress; finding the current bottleneck in a flow of work | Operations Management | `Management DPF Suite/OPERATIONS-MANAGEMENT-PRINCIPLES-FRAMEWORK.md` | OPS.5, OPS.9 |
| Human, AI or provider arrangements for the same work result | Organization Change | `Management DPF Suite/ORGANIZATION-CHANGE-ENGINEERING-PRINCIPLES-FRAMEWORK.md` | OCE.8 |
| Whether a person needs a capability, a tool or support; deliberate practice | Human Capability Development | `Human Capability Engineering DPF Suite/HUMAN-CAPABILITY-DEVELOPMENT-PRINCIPLES-FRAMEWORK.md` | HCD.1, HCD.3, HCD.9 |

Every framework embeds an Architectural Reference with a section on its relation to FPF Core; read
it when unsure which side owns a question. Frameworks not listed here (other Management
frameworks, finance, economics, physics, movement, music and dance) are found through
`references/DPFs/README.md`.

## Result test

Close every FPF-guided result by establishing:

1. **Result kind** — what exact result the selected branch can honestly return.
2. **Receiving use** — the decision, method, plan, evaluation, transformation, gate, or publication
   occurrence that will use it.
3. **Binding** — what direct relation, application binding, or well-formed local claim makes this
   result valid for that use.

If a required governor or fact is missing, name it and stop. Do not weaken the claim merely to
produce an answer. A note, plan, dashboard, ticket, or generated document is a carrier, not proof
that its downstream effect occurred. A fluent answer is not proof of fact, capability, permission
or commitment.

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
- `comparison-frame` builds the scales a comparison is made on (`A.17`–`A.19`, `A.19.ECS`, `C.16`,
  `E.13`) before options are weighed; `diverge-synthesize-select` owns the user-facing decision card; Decision Design supplies its
  formulation, alternatives and robustness methods when those are the hard part.
- Use option-generation or sequential-reasoning aids only when they add something to the selected
  branch; they are not mandatory dependencies.
- Prefer a small portfolio with explicit trade-offs over an unsupported single-winner conclusion.
- Do not load all entries, all neighbours, or an entire reference to demonstrate thoroughness.
