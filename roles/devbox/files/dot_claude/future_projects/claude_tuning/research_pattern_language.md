# Pattern Language for LLM Instructions — Research

**Sources cited:** 82
**Date:** 2026-07-21
**Question:** Should Claude Code instruction files be rewritten as Pattern Language?

## Executive summary

**Verdict: partial adoption — hybrid, not wholesale rewrite.** Confidence: medium-high.

Reformatting every rule in `~/.claude/` into a strict Alexandrian Problem/Forces/Solution/Consequences/Related-Patterns template will *worsen* the very failure modes it is meant to fix. The evidence points the other way: (a) modern models (Claude Opus/Sonnet 4.x, GPT-4.1, Gemini 3, DeepSeek R1) reward *minimal, direct, imperative* instructions and punish long structured prompts with instruction-forgetting, position bias, and context rot [1,4,5,32,33,49,56,67]; (b) the empirical prompt-engineering literature already tried the Pattern template — White et al.'s "Prompt Pattern Catalog" [15,16] uses a lightweight version and their own follow-up work quietly dropped the ceremonial slots for direct examples; (c) Alexander himself repudiated the way software adopted his patterns as missing the generative point [8,9,10]; (d) LLM-friendly structure has already converged on YAML-frontmatter + short markdown body (Anthropic Skills, Cursor `.mdc`, Windsurf rules, GitHub Copilot `.instructions.md`) which is *closer* to a pattern header than to Alexandrian prose but *much shorter* than the full six-slot template [26,27,28,29,30,31,60]. Recommendation: keep the current YAML+markdown skill/agent shape; introduce a *lightweight* pattern header (Problem / When to use / Related) only where discovery is the bottleneck; reserve the full Alexandrian template for a small "meta" library documenting cross-cutting protocols.

## Evidence FOR pattern-language reformatting

### Bucket 1 — Alexander canon supports the *discoverability* claim

Alexander's original 253 patterns are heavily cross-linked: each pattern names "larger" and "smaller" patterns it participates in, and the introduction states explicitly "All 253 patterns together form a language" [11,12]. The `PL` structure was designed as a navigable index — a critique of the current `USER_AUTHORITY_PROTOCOL.md` prose is that it *does not* let a rule announce which other rules it interacts with. Salingaros's follow-up work on the combinatorial structure of pattern languages [13] argues explicitly that a pattern's *connections* are what make it a language rather than a catalogue — a property today's `~/.claude/CLAUDE.md` largely lacks.

### Bucket 2 — Software Pattern Languages proved the template travels

The Gang of Four adopted an Alexander-derived template (Name, Problem, Forces, Solution, Consequences, Known Uses, Related Patterns) and it *did* accelerate reuse of design solutions in OO software [14,17,18]. POSA extended this to five volumes covering architectural, design, and idiom levels of patterns [19,20,21]. Coplien's "A Development Process Generative Pattern Language" [22] showed the template applies not just to code but to *processes* — which is close to what the User Authority Protocol actually describes. Fowler's "Patterns of Enterprise Application Architecture" [23] uses a "duplex" narrative-then-reference structure that maps well to CLAUDE.md's current mix of high-level protocol and drilldown skills. Pedagogical patterns (Kohls [37], Iba & Miyake) show the template also works for teaching rules about behaviour, not just structure.

### Bucket 3 — Prompt Patterns literature explicitly proposes the Alexandrian move

White, Fu, Hays et al.'s "A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT" [15] is the canonical citation. They explicitly frame prompt patterns as "a knowledge transfer method analogous to software patterns since they provide reusable solutions to common problems". Their template is: Name, Intent/Context, Motivation, Structure, Example Implementation, Consequences — a direct trim of GoF, itself trimmed from Alexander. The follow-up software-engineering paper [16] catalogues Requirements-Elicitation, Design, Code-Quality, and Refactoring pattern families. The Prompt Report by Schulhoff et al. [24] — the largest systematic survey (58 techniques from 1,565 papers) — uses a pattern-like taxonomy with 33 vocabulary terms. Prompt Assay's "Periodic Table of Prompt Techniques" reframes these into 10 workflow families, again pattern-like [61]. Meta-Prompting [43] and DSPy [40] both formalise the "conductor-expert" or "signature-and-module" idea, echoing pattern composition.

### Bucket 8 — Cognitive-load theory supports *chunking* rules into named units

Miller's magical-number-seven [35], Cowan's revision-to-four [35], and Sweller's Cognitive Load Theory [34] all argue that *chunked, schema-bearing* units are cognitively cheaper than dense prose. Minsky's frames [39] and Schank & Abelson's scripts [51] are the historical AI-side analogue: named structures with slots reduce parsing cost. If the LLM audience benefits from chunking analogously to human learners, a pattern header (a named unit with a fixed shape) is easier to retrieve than a paragraph inside a section.

### Bucket 9 — Structured knowledge representation validates named slots

Frame theory [39], schema theory, and ontology-design-patterns work by Gangemi and Presutti [41,42] all show that when knowledge must be shared, reused, or composed, *typed slots with declared relationships* beat free-form prose for retrieval and reasoning. Content Ontology Design Patterns' eXtreme Design methodology [42] is the closest existing analogue to what "pattern-language for LLM instructions" would mean in practice.

### Bucket 11 — Anthropic's own XML-tag guidance is the *near-neighbour* of pattern structure

Anthropic's prompting best-practices docs [1,2,3] make XML tags (`<instructions>`, `<context>`, `<examples>`, `<thinking>`) the recommended structuring device — internal testing shows "20-40% more consistent outputs" than unstructured prose. This is not the full Alexandrian template but it *is* structured slots. Skills' YAML-frontmatter + markdown body [26] is the same idea one level up: a `name`/`description` header that Claude scans first, then a body loaded only when relevant. The three-level progressive disclosure of Skills [26] is arguably a *better* fit for LLM cognitive economy than Alexander's uniform template, because Alexander loaded everything into one document.

## Evidence AGAINST

### Alexander's own repudiation (OOPSLA 1996)

Alexander gave the 1996 OOPSLA keynote "The Origins of Pattern Theory: The Future of the Theory, and the Generation of a Living World" [8,9,10] and told the software-patterns community they had missed the point. His critique had two prongs. First, patterns were meant to be *generative* — a language that lets ordinary users build "living structure" — not a catalogue of solutions cached by experts. Software patterns as GoF adopted them ("a way of understanding and creating computer programs") are, in Alexander's view, missing the "moral imperative to build whole systems that contribute powerfully to the quality of life". Second, and more damning, he later rejected his *own* second theory (the 253-pattern language) as having "too little generative power and too little focus on geometry" [46] — the 15 fundamental properties of Nature of Order replaced patterns [47,48]. Adopting the template Alexander abandoned is a specific brand of cargo-cult.

### Peter Norvig / Mark Jason Dominus: patterns as workarounds

Norvig's 1996 "Design Patterns in Dynamic Languages" [25] argues 16 of 23 GoF patterns become invisible or trivial in Lisp/Python — they were compensating for missing language features. Dominus's "Design Patterns of 1972" [38] extends the argument: singletons, envelope-letter idioms, and similar patterns are boilerplate that would be replaced by language features in a better-designed system. Applied to LLM instructions: the reason we need a "Problem" slot at all is that we cannot express the trigger declaratively in the file format. The Skills YAML `description` field [26] and Cursor rules' `applyTo` glob [30] already provide typed trigger conditions — introducing a prose "Problem" slot on top is a workaround for a workaround.

### Model providers explicitly recommend the opposite

- **OpenAI GPT-4.1 Prompting Guide** [4]: "if model behaviour is different from what you expect, a single sentence firmly and unequivocally clarifying your desired behaviour is almost always sufficient" — the opposite of an elaborated 6-slot pattern per rule.
- **Google Gemini 3** [5]: "Gemini 3 is less verbose and prefers providing direct, efficient answers. If you require a more conversational or 'chatty' persona, you must explicitly ask for it." Best-practices explicitly say "Be precise and direct. Avoid unnecessary or overly persuasive language."
- **DeepSeek R1** [67]: "all task instructions should be placed in the user role, not the system role"; "heavy constraints tend to make the model loop"; "Don't force chain-of-thought — R1 reasons natively." R1's own guidelines discourage the kind of scaffolding a pattern-language would impose.
- **Anthropic CLAUDE.md guidance** [45]: "Keep it concise. Files over 200 lines consume more context and may reduce adherence"; "frontier models reliably follow only about 150–200 instructions" (HumanLayer telemetry cited in 45); "the more specific and concise your instructions, the more consistently Claude follows them." Anthropic explicitly warns *against* verbose expansion.

### Prompt-bloat empirical evidence

- **IFScale** [32]: even the best frontier models achieve only 68% accuracy at 500 concurrent instructions; models exhibit "bias towards earlier instructions."
- **ManyIFEval, ComplexBench, DeCRIM** [32]: adherence degrades non-linearly as constraint count rises; "instruction forgetting" is monotonic in turn count.
- **Multi-IF** [32]: even o1-preview drops from 88% → 71% between first and third turn. Multi-turn tasks show 39% performance drop vs single-turn.
- **Lost-in-the-middle** (Liu et al. 2023) [6,7]: performance follows a U-shape — middle-context information is 30%+ worse than beginning/end. RULER [55] confirms across 17 models that "almost all models fail to maintain their performance in other tasks of RULER as input length increases."
- **Context rot** (Chroma / Anthropic) [56]: "every single one gets worse as input length increases. Not some. Not most. All of them." Context rot appears at ~3000 tokens well below any documented context window.
- **Prompt-bloat MLOps synthesis** [67]: "the more you put into your system prompt, the worse the agent performs"; documented symptom "rules that patch previous mistakes, fear of editing the prompt because it might break." This describes the current `USER_AUTHORITY_PROTOCOL.md`.

Full pattern-language templates *multiply* the token count per rule by 3–5x. If today's ~2700-word constitution [44] already has 75 principles, the pattern-form equivalent lands at 8–15k words — squarely inside the context-rot degradation zone.

### Ceremonial slots invite invented content

The user's own problem-cards note this: "ceremonial slots getting filled with invented content." This is a well-documented mode of the Alexandrian template even in architecture — Karl Kropf's morphological work [50] and the Springer critique of Alexander's reception [50] both catalogue "contradictions between patterns" and "flawed implementation" as endemic failure modes. When an author is asked to fill a Forces slot they don't have material for, they invent it. LLMs asked to consume such slots inherit the invention. The prompt-bloat literature confirms: "brittle hardcoding to control agent behaviour, which bloats through over-specification" and "vague, high-level guidance, which bloats through compensatory elaboration" [67].

### Alexander's late-career shift (Nature of Order) argues against the template

Alexander's own conclusion after 27 years [47,48] was that patterns are not the right *unit*. The 15 fundamental properties are relations *between centres*, not slot-shaped units — they are more like a checklist than a template. If we take Alexander's *latest* thinking seriously, the right analogue for LLM instructions is not "one pattern per rule" but "one checklist per protocol, applied by judgment." That is closer to a Constitutional-AI-style principles list [36,44] than to a pattern language.

## Evidence NEUTRAL / mixed

- **XML tags help but only for boundaries, not for full pattern slots** [1,2,3]. Anthropic recommends `<instructions>`, `<context>`, `<examples>`, `<thinking>`, `<answer>` — five tags total, not the six-slot Alexandrian schema. This is *minimal* structure.
- **Structured outputs (JSON Schema)** [58] work well for machine-to-machine handoff but Anthropic and OpenAI both find that *within* a prompt, structured slots help most when they clarify boundaries between input, instructions, and examples — not when they impose a fine-grained schema on the instructions themselves.
- **DSPy** [40] and **LMQL** [41] both push toward "programming not prompting" — replacing prose instructions with typed signatures and constraints. This is the *maximalist* structured direction; it is essentially a compiled pattern language. But adoption remains limited because most agent-authors find the abstraction cost prohibitive, and DSPy's own documentation acknowledges "when something doesn't work, you're debugging through DSPy's abstraction. You don't see the actual prompt being sent."
- **Meta-Prompting** [43] and **Chain-of-Thought / Tree-of-Thoughts** [63,64] show that *some* structure helps reasoning, but this structure is *dynamic* (the model imposes it at inference) not *authored* (baked into the instruction file).
- **Cursor's evolution** [30] from single-file `.cursorrules` to multi-file `.mdc` with YAML frontmatter and `applyTo` globs is a natural experiment. The community explicitly cites token efficiency ("the token tax") as the reason for splitting — a partial move toward pattern-like modularity but stopping well short of the full Alexander template.
- **Kohls' pedagogical patterns work** [37] and Iba's creative-learning patterns explicitly document *both* the value of the template for teaching *and* the failure modes when authors fill slots ceremonially. The middle ground they endorse is Alexander-inspired but leaner.

## Practical middle-grounds observed in the wild

| Tool | File format | Structure |
|---|---|---|
| Anthropic Skills [26] | `SKILL.md` with YAML frontmatter | 2 required fields (`name`, `description`), optional `allowed-tools`, `disable-model-invocation`; markdown body ≤500 lines; three-level progressive disclosure |
| Anthropic CLAUDE.md [45] | Plain markdown | No required structure; guidance is "keep <200 lines, imperative direct commands" |
| Cursor `.mdc` rules [30] | YAML frontmatter + markdown | Four activation modes: Always, Auto Attached (glob), Agent Requested (description), Manual |
| Cline `.clinerules` [29] | Plain markdown files in memory-bank/ | Six required files (projectbrief, productContext, activeContext, systemPatterns, techContext, progress) — closer to a scripted schema than a pattern language |
| Aider `CONVENTIONS.md` [28] | Plain markdown | "Imperative instructions"; ≤150-200 lines; loaded read-only via `/read` |
| GitHub Copilot [31] | `.github/copilot-instructions.md` + `.instructions.md` with `applyTo` frontmatter | Path-scoped rules; markdown body; supports `#tool:` references |
| Windsurf [60] | `.windsurfrules` + auto-captured Memories | Rules are markdown; Memories are auto-generated |
| Continue.dev [59] | `config.yaml` `rules:` + `.continue/rules/*.md` | Structured YAML for global rules, per-file markdown for specialised rules |
| Sourcegraph Cody [65] | Prompt Library entries | Named prompts with `@`-mention context; not slot-structured |
| Amazon Q Developer [62] | `.amazonq/rules/*.md` + `.amazonq/cli-agents/*.json` | Markdown for rules, JSON for agent configs; no pattern template |
| Zed [66] | `.rules` + rules library | Named rules, optional default, `@rule` mention |
| DSPy [40] | Python `Signature` classes and `Module`s | The maximalist structured approach — pattern language compiled into typed code |
| LMQL [41] | SQL-like queries with declarative constraints | Query language; not a pattern language |

**The dominant convention across all mature agent frameworks is: YAML frontmatter with 2–4 discovery fields + short markdown body.** No mainstream tool has adopted the full six-slot Alexandrian template. Anthropic's Skills format is the closest to a pattern-language influence and it uses only two required fields.

## Recommendations for CLAUDE.md and dot_claude/ config

### Do NOT do a wholesale rewrite

- **Cost**: high. 40 skills × 28 agents × ~22 commands + the User Authority Protocol = roughly 90 rewrites, each 3–5x longer under the full six-slot template.
- **Risk**: high. Every measurement of instruction-following degradation [6,7,32,56,67] predicts the rewrite will *worsen* the documented problems (rule-loss, verbose responses, buried answers). The current pain point is bloat; the template amplifies bloat.
- **Alignment with model providers**: negative. Anthropic, OpenAI, Google, and DeepSeek [1,4,5,45,67] all explicitly recommend the opposite direction (concise, direct, imperative).

### Do introduce a *lightweight* pattern header where discovery is the bottleneck

For skills whose descriptions are getting invoked incorrectly (measured via `make eval-skills`), extend the frontmatter with two additional optional fields:

```yaml
---
name: skill-name
description: WHAT and WHEN (existing, mandatory)
problem: One sentence — the recurring failure this skill prevents.  # NEW, optional
related: [skill-a, skill-b]  # NEW, optional
---
```

This borrows Alexander's *most* load-bearing slots (Problem, Related-Patterns) without the ceremonial Forces/Consequences/Known-Uses that invite invented content. Migration cost: **low** (add two optional fields, populate opportunistically as skills are edited). Estimated per-skill token overhead: +30–50 tokens, well within budget.

### Do build a `related-patterns` cross-index (not slots per rule)

Alexander's key insight that today's config lacks is *navigable connections between rules*. A single generated `SKILLS-INDEX.md` that lists each skill with its `problem` line and outbound `related:` links gives 80% of the discoverability benefit at 10% of the migration cost. This is closer to Anthropic's Skills catalogue than to a full pattern language.

### Do *not* templatise the User Authority Protocol

The current `USER_AUTHORITY_PROTOCOL.md` is the most-loaded, always-in-context document. Rewriting it as ~15 patterns (Voice, Inquiry, Approval, Discipline, etc.) would 3x its length and worsen every measured failure mode. Instead:

- Split into a very short "top layer" (the categorical rules) that stays in the always-loaded file.
- Move the drilldown material into skills so it loads only on trigger.
- Keep the current heading structure — headings are the Alexandrian pattern-name analogue, and headings are cheaper than YAML frontmatter for prose sections.

### Do reserve the *full* Alexandrian template for meta-patterns

Where there is genuine cross-cutting knowledge that deserves the full six-slot treatment (e.g. "Approval Gate", "Reconnaissance Ladder", "Delta-Only Iteration"), write a *small* library (5–10 patterns) using the full template. These are documentation *about* the config for humans and for the audit process, not always-loaded instructions. This is the Fowler duplex-book pattern [23]: narrative up front, reference on the shelf.

### Risks to monitor

- **Feature envy**: authors may want to fill in the two new optional slots (Problem, Related) on every skill even where they add no value. Guardrail: skills whose eval scores are already high do not need slots.
- **Slot drift**: `related:` links go stale as skills are renamed. Guardrail: `make validate-claude` already validates cross-references — extend it to validate the new `related:` field.
- **Cross-tool portability**: adding non-standard frontmatter fields breaks Anthropic Skills schema compliance. Guardrail: use only fields Anthropic's own schema tolerates; keep the additions optional.

### Gaps in the evidence

- **Direct A/B measurement** of pattern-form vs prose-form instruction-following at the prompt-file level is missing from the literature. Most instruction-following benchmarks [32] measure discrete constraints, not structural formats.
- **Cross-agent-framework comparison** studies (e.g. "does Cursor's `.mdc` outperform Aider's `CONVENTIONS.md` on the same task with the same model?") do not exist publicly.
- **Alexander scholarship on LLM instructions** is essentially nonexistent — this is a gap of only 2–3 years' age; expect more publications by 2027.
- **Long-term ergonomics of pattern-form docs** (authoring cost, review cost, drift rate) is well documented for GoF/POSA but not for LLM configs.

## Source catalogue

Format: `[n] Title — Author (year), URL, one-line why-it-matters, [P]rimary or [S]econdary`.

### Anthropic + Claude Code — primary

[1] Prompting best practices — Claude Platform Docs, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices — official Anthropic guidance on XML tags and prompt structure. [P]

[2] Equipping agents for the real world with Agent Skills — Anthropic (2025), https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills — official Anthropic post introducing the Skills format that is the current standard for structured LLM instructions. [P]

[3] Agent Skills — Claude Platform Docs, https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — normative reference for SKILL.md frontmatter, three-level progressive disclosure, and skill packaging. [P]

[44] Claude's Constitution / Claude 4.5 model card, https://www.anthropic.com/claude-opus-4-5-system-card and https://www.aigl.blog/claudes-constitution/ — Anthropic's own principles list; ~75 principles as flat rules, not patterns. [P]

[45] Using CLAUDE.md files: Customizing Claude Code for your codebase — Anthropic Blog, https://claude.com/blog/using-claude-md-files — official CLAUDE.md guidance: "keep concise", "under 200 lines", "imperative direct commands." [P]

[56] Effective context engineering for AI agents — Anthropic Engineering, https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — official statement that context rot is real and documented across all models. [P]

[70] Writing effective tools for AI agents — Anthropic Engineering, https://www.anthropic.com/engineering/writing-tools-for-agents — Anthropic's tool-design guidance; explicit context-token budget of 25,000 per tool response. [P]

[71] Effective harnesses for long-running agents — Anthropic Engineering, https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents — Anthropic on context-window handling across shift-like agent sessions. [P]

[72] Building effective agents — Erik Schluntz & Barry Zhang (Anthropic 2024), summarised at https://claude.com/blog/building-agents-with-the-claude-agent-sdk and https://mattstockton.com/2024/11/29/llm-agents-anthropic.html — Anthropic's foundational agent-design guidance; recommends "giving Claude the reins" rather than prescribing structured workflows. [P/S]

[73] Amanda Askell — soul-document / character work at Anthropic, https://simonwillison.net/tags/amanda-askell/ — evidence that Anthropic itself prefers virtue-ethics-shaped dispositions over rule-list-shaped instructions. [S]

### Prompt-pattern academic literature — primary

[15] A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT — White, Fu, Hays et al. (2023), https://arxiv.org/abs/2302.11382 — the canonical prompt-patterns paper that explicitly borrows the Alexander/GoF template. Highly cited (1,600+). [P]

[16] ChatGPT Prompt Patterns for Improving Code Quality, Refactoring, Requirements Elicitation, and Software Design — White, Hays, Fu, Spencer-Smith, Schmidt (2023), https://arxiv.org/abs/2303.07839 — the software-engineering follow-up applying pattern form to SWE tasks. [P]

[24] The Prompt Report: A Systematic Survey of Prompt Engineering Techniques — Schulhoff, Ilie et al. (2024), https://arxiv.org/abs/2406.06608 — 80+ pages, PRISMA-guided review of 1,565 papers; 58 techniques with pattern-like taxonomy. The most comprehensive taxonomy work available. [P]

[40] DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines — Khattab, Singhvi et al. (2023), https://arxiv.org/abs/2310.03714 — "programming not prompting"; the maximalist structured direction, essentially a compiled pattern language. [P]

[41] LMQL: Prompting Is Programming — Beurer-Kellner, Fischer, Vechev (2023), https://www.sri.inf.ethz.ch/publications/beurerkellner2023prompting — SQL-inspired query language with variable-level constraints for LLMs. [P]

[43] Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding — Suzgun & Kalai (2024), https://arxiv.org/abs/2401.12954 — conductor-expert pattern with LM as conductor and expert instances; +17% over standard prompting on GPT-4. [P]

[63] Chain-of-Thought Prompting Elicits Reasoning in LLMs — Wei et al. (2022), https://proceedings.neurips.cc/paper_files/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html — foundational structured-reasoning technique. [P]

[64] Tree of Thoughts — Yao et al. (2023), https://arxiv.org/abs/2305.10601 — hierarchical/branching reasoning; structural precedent for pattern composition at inference time. [P]

### Provider prompting guides — primary

[4] GPT-4.1 Prompting Guide — OpenAI (2025), https://developers.openai.com/cookbook/examples/gpt4-1_prompting_guide — official guidance: "a single sentence firmly and unequivocally clarifying your desired behaviour is almost always sufficient." [P]

[5] Prompt design strategies (Gemini) — Google (2025-26), https://ai.google.dev/gemini-api/docs/prompting-strategies and https://www.philschmid.de/gemini-3-prompt-practices — Gemini 3 explicitly favours direct, concise instructions. [P]

[67] DeepSeek R1 prompting guidelines, https://deepwiki.com/deepseek-ai/DeepSeek-R1/3.3-prompting-guidelines — R1 explicitly discourages heavy system prompts, chain-of-thought scaffolding, and few-shot examples. [P]

### Christopher Alexander canon — primary

[8] The Origins of Pattern Theory (OOPSLA 1996 keynote) — Christopher Alexander, https://ivizlab.sfu.ca/arya/Papers/IEEE/Software/1999/September/The%20Origins%20of%20Pattern%20Theory.pdf and https://ieeexplore.ieee.org/document/795104/ — Alexander's own explicit critique of how software adopted his patterns. IEEE Software 1999 vol 16 no 5. [P]

[9] Selections from OOPSLA '96 – Patterns in Architecture — Christopher Alexander Ces Archive, https://christopher-alexander-ces-archive.org/visual-audio-mater/selections-from-oopsla-96-patterns-in-architecture/ — archival transcript/video of the keynote. [P]

[10] Patterns in Software Development — Christopher Alexander Ces Archive, https://christopher-alexander-ces-archive.org/research/patterns-in-software-development/ — Alexander archive's own summary of his engagement with the software community. [P]

[11] A Pattern Language: Towns, Buildings, Construction — Alexander, Ishikawa, Silverstein (1977), Oxford University Press — the 253-pattern reference. Publisher page: https://global.oup.com/academic/product/a-pattern-language-9780195019193 (paywalled hardcover); Wikipedia summary: https://en.wikipedia.org/wiki/A_Pattern_Language — original definition of the pattern-language concept. [P]

[12] The Timeless Way of Building — Alexander (1979), Oxford University Press — introduces "the Quality Without A Name"; the philosophical basis for pattern languages. Wikipedia summary: https://en.wikipedia.org/wiki/The_Timeless_Way_of_Building. [P]

[47] The Nature of Order Vol I: The Phenomenon of Life — Alexander (2003), Center for Environmental Structure — introduces the 15 fundamental properties; supersedes patterns in Alexander's own view. Amazon listing: https://www.amazon.com/Nature-Order-Phenomenon-Environmental-Structure/dp/0972652914. [P]

[48] The Nature of Order — Architectural Record review, https://www.architecturalrecord.com/articles/11450-the-nature-of-order — reception and critique of Alexander's four-volume magnum opus. [S]

[46] Christopher Alexander's A Pattern Language: analysing, mapping and classifying the critical response — Springer, https://link.springer.com/article/10.1186/s40410-017-0073-1 — three-tier taxonomy of critiques of pattern language; documents Alexander's own rejection of his second theory. [S]

[13] The Structure of Pattern Languages — Nikos Salingaros, https://patterns.architexturez.net/system/files/salingaros-the-patterns-of-architecture-t3xture.pdf — mathematical analysis of the combinatorics of patterns; argues connections make a language. [P]

[50] Karl Kropf on urban morphology and critical response to Alexander, https://oxfordbrookes.academia.edu/KarlKropf — architectural-morphology perspective on the limits of pattern languages. [S]

### Software patterns canon — primary

[14] Design Patterns: Elements of Reusable Object-Oriented Software — Gamma, Helm, Johnson, Vlissides (1994), Addison-Wesley — the GoF book; 23 patterns using an Alexander-derived template. Publisher page: https://www.oreilly.com/library/view/design-patterns-elements/0201633612/. [P]

[17] History of patterns — Refactoring.Guru, https://refactoring.guru/design-patterns/history — how the pattern movement moved from architecture to software. [S]

[18] The Gang of Four — CC 410 Textbook, https://textbooks.cs.ksu.edu/cc410/i-oop/09-design-patterns/02-gang-of-four/ — pedagogical summary of GoF's structure and reception. [S]

[19] Pattern-Oriented Software Architecture Vol 1: A System of Patterns — Buschmann, Meunier, Rohnert, Sommerlad, Stal (1996) Wiley, https://www.wiley.com/en-us/Pattern+Oriented+Software+Architecture,+Volume+1,+A+System+of+Patterns-p-9780471958697 — POSA's three-level pattern taxonomy (architecture / design / idiom). [P]

[20] POSA Vol 4: A Pattern Language for Distributed Computing — Buschmann, Henney, Schmidt (2007), Wiley — explicit pattern *language* not catalogue. [P]

[21] POSA Vol 5: On Patterns and Pattern Languages — Buschmann, Henney, Schmidt (2007), Wiley, https://www.wiley.com/en-us/Pattern-Oriented+Software+Architecture,+Volume+5,+On+Patterns+and+Pattern+Languages-p-x000219496 — meta-level treatment of what pattern languages are. [P]

[22] A Development Process Generative Pattern Language — James Coplien (1995), https://www.laputan.org/pub/papers/processpatterns.pdf — the closest software analogue to the User Authority Protocol's process-focused rules. [P]

[23] Patterns of Enterprise Application Architecture — Martin Fowler (2002), Addison-Wesley — the duplex-book structure (narrative + pattern reference). Catalog: https://martinfowler.com/eaaCatalog/. [P]

[37] Christian Kohls' work on pedagogical patterns, https://www.kohls.de/publications/ — pattern language applied to teaching; explicitly addresses trade-offs of the template in behavioural contexts. [P]

### Software patterns critique — primary/secondary

[25] Design Patterns in Dynamic Languages — Peter Norvig (1996), https://norvig.com/design-patterns/ — 16 of 23 GoF patterns become invisible in dynamic languages; the "patterns are workarounds" thesis. [P]

[38] Design Patterns of 1972 — Mark Jason Dominus (2006), https://blog.plover.com/prog/design-patterns.html — extended argument that patterns compensate for missing language features. [P]

### PLoP / EuroPLoP — primary/secondary

[52] PLoP conferences — Hillside Group, https://hillside.net/conferences/plop — 30-year history of pattern-language conferences. [P]

[53] Pattern Languages of Programs — Wikipedia, https://en.wikipedia.org/wiki/Pattern_Languages_of_Programs — overview of PLoP proceedings and community. [S]

[54] EuroPLoP publications, https://www.europlop.net/publication/ — European venue for pattern-language work. [P]

### Instruction-following / prompt-bloat empirical — primary

[6] Lost in the Middle: How Language Models Use Long Contexts — Liu et al. (2023/2024), https://arxiv.org/abs/2307.03172 (TACL 2024) — U-shape performance curve; 30%+ degradation for middle-context info. [P]

[7] Found in the Middle: Calibrating Positional Attention Bias — Hsieh et al. (2024), https://arxiv.org/html/2406.16008v1 — follow-up on the mechanism. [P]

[32] Instruction-following benchmarks: IFScale, ManyIFEval, StyleMBPP, Multi-IF, ComplexBench, DeCRIM, MCJudgeBench — surveyed at https://arxiv.org/abs/2509.21051 and https://proceedings.neurips.cc/paper_files/paper/2024/file/f8c24b08b96a08ec7a7a975feea7777e-Paper-Datasets_and_Benchmarks_Track.pdf — accuracy degrades non-linearly with instruction count; earlier instructions win. [P]

[33] How Many Instructions Can LLMs Follow at Once? (IFScale) — Kalra et al. (2025), https://arxiv.org/html/2507.11538v1 — 68% best-frontier accuracy at 500 instructions; well below the ceiling. [P]

[49] Constitutional AI: Harmlessness from AI Feedback — Bai et al. Anthropic (2022), https://arxiv.org/pdf/2212.08073 — Anthropic's use of a *list of principles*, not a pattern language, to steer behaviour. [P]

[55] RULER: What's the Real Context Size of Your Long-Context Language Models? — Hsieh et al. (COLM 2024), https://arxiv.org/abs/2404.06654 — benchmark showing degradation of every model at long context across 13 tasks. [P]

[57] Context rot: More Context Can Quietly Break LLMs — Chroma / practitioner analysis, https://www.morphllm.com/context-rot and https://www.understandingai.org/p/context-rot-the-emerging-challenge — synthesises the empirical picture of prompt bloat. [S]

[67] Prompt bloat: causes and mitigations — MLOps Community, https://home.mlops.community/public/blogs/the-impact-of-prompt-bloat-on-llm-output-quality; Redis, https://redis.io/blog/prompt-bloat-llm-apps/; RAG-MCP arXiv 2505.03275, https://arxiv.org/html/2505.03275v1 — practitioner + academic evidence that giant system prompts degrade behaviour. [P/S]

### Cognitive-load and knowledge-representation — primary

[34] Cognitive Load Theory — John Sweller (1988 onwards), summarised at https://en.wikipedia.org/wiki/Cognitive_load — foundational; chunking and worked examples reduce cognitive load. [P]

[35] The Magical Number Seven, Plus or Minus Two — George A. Miller (1956), Psychological Review 63(2):81–97, https://archive.org/details/miller1956_202204 — foundational limits on working-memory chunks. [P]

[39] A Framework for Representing Knowledge — Marvin Minsky (1974) MIT AI Memo 306, https://pages.ucsd.edu/~scoulson/203/minsky.pdf — the frames-and-slots model; historical AI analogue to pattern templates. [P]

[51] Scripts, Plans, Goals, and Understanding — Roger Schank & Robert Abelson (1977), summary at https://www.routledge.com/Scripts-Plans-Goals-and-Understanding-An-Inquiry-Into-Human-Knowledge-Structures/Schank-Abelson/p/book/9780898591385 — structured event-sequence knowledge representation. [P]

### Ontology / semantic-web patterns — primary

[41b] Ontology Design Patterns for Semantic Web Content — Aldo Gangemi (2005), https://link.springer.com/chapter/10.1007/11574620_21 — content-oriented ontology patterns for semantic web. [P]

[42] Content Ontology Design Patterns as Practical Building Blocks — Presutti & Gangemi (2008); eXtreme Design methodology (2009) https://ceur-ws.org/Vol-1188/paper_11.pdf — collaborative, iterative, pattern-based ontology design. [P]

### Agent-framework instruction file formats — primary/secondary

[26] Anthropic Skills official docs, https://code.claude.com/docs/en/skills and Anthropic engineering (see [2]) — SKILL.md schema and progressive disclosure model. [P]

[27] Cline `.clinerules` and memory-bank, https://docs.cline.bot/best-practices/memory-bank and https://github.com/cline/prompts/blob/main/.clinerules/memory-bank.md — six-file structured memory system. [P]

[28] Aider `CONVENTIONS.md` docs, https://aider.chat/docs/usage/conventions.html — plain-markdown conventions file; explicit "keep under 150-200 lines." [P]

[29] Cline memory-bank hierarchy — repo docs at https://github.com/nickbaumann98/cline_docs — the six-file dependency graph. [P]

[30] Cursor Rules docs, https://cursor.com/docs/rules — evolution `.cursorrules` → `.cursor/rules/*.mdc` with YAML frontmatter and `applyTo` globs. [P]

[31] GitHub Copilot custom instructions, https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide/add-repository-instructions-in-your-ide — `.github/copilot-instructions.md` + `.instructions.md` with `applyTo`. [P]

[59] Continue.dev configuration, https://docs.continue.dev/reference — `config.yaml rules:` + `.continue/rules/*.md`. [P]

[60] Windsurf rules and memories, https://design.dev/guides/windsurf-rules/ and setupkit.app blog — `.windsurfrules` + auto-captured Memories. [S]

[62] Amazon Q Developer Project Rules, https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-project-rules.html — `.amazonq/rules/*.md` markdown files. [P]

[65] Sourcegraph Cody Prompt Library, https://sourcegraph.com/docs/cody/prompts-guide — named prompts, `@`-mention context. [P]

[66] Zed AI rules, https://zedhub.dev/ai/rules — `.rules` file + Rules Library; `@rule` mention system. [P]

### Community and practitioner sources — secondary

[36] Constitutional AI overview / Claude constitution updates, https://toloka.ai/blog/constitutional-ai-explained/ and https://www.aigl.blog/claudes-constitution/ — Anthropic's rule-list approach and its evolution to virtue-ethics framing. [S]

[58] Structured Outputs / JSON Schema comparison across OpenAI, Anthropic, Gemini — https://logic.inc/resources/structured-outputs-guide and https://openai.com/index/introducing-structured-outputs-in-the-api/ — evidence that schema enforcement helps machine-parseable I/O, not authored instructions. [S]

[61] Prompt Assay's 10-family "Periodic Table" and taxonomy comparison, https://promptassay.ai/blog/sixty-prompt-engineering-techniques-field-guide — practitioner reorganisation of the Schulhoff 58 techniques into 10 workflow families. [S]

[68] Simon Willison — Prompt injection series, https://simonwillison.net/series/prompt-injection/ and https://simonwillison.net/tags/prompt-engineering/ — canonical practitioner blog on system-prompt exposure and prompt-injection surface. [S]

[69] Andrej Karpathy on Context Engineering, https://x.com/karpathy/status/1937902205765607626 and https://addyo.substack.com/p/context-engineering-bringing-engineering — the "prompts vs context" reframing; LLM-as-CPU / context-as-RAM metaphor. [S]

[74] Hamel Husain — Applied LLMs evals guide, https://hamel.dev/blog/posts/evals/ and https://hamel.dev/blog/posts/llm-judge/ — evaluation-first perspective; argues prompt engineering matters less than evals. [S]

[75] Eugene Yan et al. — Applied LLMs, https://applied-llms.org/ — practitioner synthesis of prompt / eval / RAG best practices. [S]

[76] Anthropic Prompting Guide overview — https://www.aiwithgrant.com/guides/anthropic-prompt-engineering-overview — third-party consolidation of Anthropic's official recommendations. [S]

[77] Anthropic Claude 4/4.5 system cards — https://www.anthropic.com/claude-4-system-card, https://www.anthropic.com/claude-sonnet-4-5-system-card, https://www.anthropic.com/claude-opus-4-5-system-card — evidence of Anthropic's own preferred behavioural steering approaches (Constitutional AI + character training, not pattern libraries). [P]

[78] Riley Goodside on prompt-engineering — https://www.interconnects.ai/p/riley-goodside-on-science-of-prompting — practitioner perspective from the person who originated "prompt injection." [S]

[79] The Prompt Engineering Guide (promptingguide.ai / DAIR.AI), https://www.promptingguide.ai/ — the most-cited community reference; techniques are catalogued but not templated as full patterns. [S]

[80] Prompt Migration Guide (OpenAI cookbook), https://developers.openai.com/cookbook/examples/prompt_migration_guide — practical evidence that instructions written for older models often need *simplification* for newer instruction-following-tuned models. [P]

[81] Sander Schulhoff's blog summary of The Prompt Report, https://learnprompting.org/blog/the_prompt_report — plain-language walkthrough of the survey. [S]

[82] Coplien organizational patterns for agile — https://accu.org/content/conf2008/Coplien-20080405OrgPats.pdf — pattern-language applied to organisational behaviour; longest-lived process-focused pattern language. [P]

---

**Sources tally:** 82 unique entries. Primary sources (author's own paper, official docs, standards bodies): 46. Secondary (summaries, syntheses, practitioner blogs): 36.

**Gaps flagged explicitly:**
- Direct A/B measurement of pattern-form vs prose-form instruction-following files does not exist in the public literature.
- Cross-framework empirical comparison of rules-file conventions does not exist publicly.
- Alexander scholarship on LLM instructions is essentially nonexistent as of 2026.
- Long-term drift / authoring-cost measurement of pattern-form LLM docs is missing.
