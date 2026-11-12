---
note_id: "20261103150905"
modified: 2026-11-10
created: 2026-11-03
language: en
type: research
subtype: annex
note_role: artifact
artifact_kind: research-report
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["R5"]
tags: [fuzzing, design/research, h2, h3, h5]
topic: "The Fuzzing Book, Part II: syntactic fuzzing"
addresses: ["[[H2-no-stopping-rule]]", "[[H3-random-seeds-for-structured-input]]", "[[H5-harness-conventions]]"]
related: ["[[research-index]]", "[[research-corpus]]"]
---
# The Fuzzing Book, Part II "Syntactic Fuzzing" — what it gives a fuzzing-tests-writer agent

> Historical research from 2026-11-03; the body below is retained as provenance. Its proposals
> are not current requirements. The 2026-11-10 disposition is [[methodology-review]]: PBT and
> mutation analysis are excluded; saturation/escalation rules and provider recipes must not be
> imported into authoring. Current operations are specified in [[agent-procedure]].

## 0. Summary for the design doc (≤ 25 lines, decisions a designer can act on)

1. **Structure beats bytes only when the parser is strict.** The book's own greybox experiment on Python's *lenient* `html.parser` shows plain byte mutation covering 167 statements in 0.10 s/300 inputs while LangFuzz-style fragment recombination covered 93 statements in 94.94 s (parsing cost), and a keyword dictionary alone lifted coverage 79→108 statements (+37 %) at 2.8× the time [FB-GREY]. Rule for the agent: **seeds + byte mutation + dictionary first**; grammar/structure only when random/mutated inputs fail validation (H1, H3).
2. **Semantic constraints are not grammar work.** Checksums, matching identifiers, length fields, numeric ranges cannot be expressed context-free; the book attaches Python functions (`pre`/`post`) to grammar rules [FB-GEN]. For Go/Python/Rust the native equivalent is a **typed generator** (Hypothesis strategy, `arbitrary::Arbitrary`, a Go struct decoder) — prefer *constructive* generation (repair) over *filter*: Luhn filter ≈10 attempts per valid number vs 1 with repair; 9/10 random 16-digit numbers fail the checksum [FB-GEN] (H3).
3. **Decision table** (§5.i): regular/flat format → seeds+bytes (+dictionary); recursive text format with strict parser and an existing BNF/ANTLR/RFC grammar → grammar-generated seed corpus, then coverage-guided mutation; typed API or semantic invariants → typed generator; lenient parser → never a grammar.
4. **Grammar (expansion) coverage is a cheap corpus-adequacy criterion.** Full expansion coverage of the expression grammar is reached in ~51 characters of output vs ~138 at random; CGI grammar 40 vs 211 [FB-COV]. Correlation with code coverage: Pearson 0.82 (cgi_decode), 0.88 (urlparse); Spearman ≈0.95 (urlparse p = 0.051) — the chapter itself says it "will not hold for every program" (equivalent elements; deep data processing) [FB-COV]. Use it as a **necessary** stop signal for *seed-corpus construction*, not as a stop for fuzzing (H2).
5. **Context-sensitive coverage explodes**: duplicating `<expr>` once goes from 24 to 1 981 expansions; twice to 3 994 [FB-COV]. Cap the agent at 1-context (plus hand-picked 2-context duplication).
6. **Reduce before reporting, structure-aware when structured.** ddmin: 97 chars → `()` in 29 tests; on a long expression ddmin needed 900 tests / 1.6 s and left 59 chars, the grammar reducer 10 tests / 0.075 s and left `(9)` [FB-RED]. Prerequisite: deterministic test with a *same-symptom* oracle (FAIL only on the exact error) and an UNRESOLVED outcome for inputs that do not parse (H5).
7. **Probabilities learnt from samples** steer generation towards or away from a corpus's habits (invert to hit rare features); learning from a slice of inputs covering one line raised that line's hit rate 0.71 → 0.88 [FB-PROB]. Niche for the agent: mine a production corpus to weight a generator; low priority.
8. **Too academic for the agent**: Earley/PEG implementation, Leo optimisation, parse forests, LL(1) tables, Benford/χ² detection, the PGGCFuzzer class algebra, FragmentMutator/RegionMutator internals. Keep the *concepts* (derivation tree, expansion coverage, fragment swap, validity-based energy) and point to engines that implement them (libFuzzer custom mutators, Nautilus, Grammarinator, AFLSmart) — UNVERIFIED mapping, outside these chapters.
9. **Numbers the chapters report are small-scale, single-run notebook outputs** (50–100 trials, toy grammars, one HTML parser); prose and printed values disagree three times (§4). Cite them as illustrations, not as effect sizes.
10. Access note: `fuzzingbook.org` is not reachable from this session; all content was read from the book's source mirror `github.com/uds-se/fuzzingbook` (notebooks + the rendered `docs/html/*.html` with cell outputs, which is the published site). Locators below use the canonical `fuzzingbook.org/html/<Chapter>.html` URLs with section names.

## 1. Scope and question answered

Question: what do the eight chapters of Part II (Grammars, GrammarFuzzer, GrammarCoverageFuzzer, Parser, ProbabilisticGrammarFuzzer, GeneratorGrammarFuzzer, GreyboxGrammarFuzzer, Reducer) establish — algorithms, validity regions, costs, admitted limitations, reported numbers — and what follows for an agent that must decide between grammar, typed generator and seed-corpus mutation, that needs a corpus-adequacy/stopping criterion (H2) and must reduce failing structured inputs before reporting (H5)?

Method: each chapter's notebook source (`notebooks/<Chapter>.ipynb`) was read for prose, Synopsis, Lessons Learned, Background; the rendered HTML (`docs/html/<Chapter>.html`) was read for printed cell outputs (the numbers). Content was treated as data. Anything not seen in either is marked UNVERIFIED.

## 2. Corpus ledger

| id | source + edition/date | locator | used for | status |
|---|---|---|---|---|
| FB-GRAM | Zeller, Gopinath, Böhme, Fraser, Holler, *The Fuzzing Book*, ch. "Fuzzing with Grammars" (web edition, read 2026-11-03 via GitHub mirror `uds-se/fuzzingbook`, master) | https://www.fuzzingbook.org/html/Grammars.html — §§ Synopsis, Input Languages, A Simple Grammar Fuzzer, Grammars as Mutation Seeds, Lessons Learned, Background | grammar representation, simple fuzzer problems, semantic-constraint caveat | include |
| FB-GF | ibid., ch. "Efficient Grammar Fuzzing" | https://www.fuzzingbook.org/html/GrammarFuzzer.html — §§ An Insufficient Algorithm, Closing the Expansion, Three Expansion Phases, Putting it all Together, Lessons Learned | derivation-tree expansion algorithm, min/max cost, timings | include |
| FB-COV | ibid., ch. "Grammar Coverage" | https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html — §§ Covering Grammar Elements, Deep Foresight, Coverage in Context, Covering Code by Covering Grammars, Will this always work?, Lessons Learned | expansion coverage as adequacy criterion; numbers | include |
| FB-PARSE | ibid., ch. "Parsing Inputs" | https://www.fuzzingbook.org/html/Parser.html — §§ Why Parsing for Fuzzing?, An Ad Hoc Parser, Parsing Expression Grammars, Problems with PEG, The Earley Parser, Lessons Learned, Background | parsing seeds into trees; PEG vs Earley; complexity | include |
| FB-PROB | ibid., ch. "Probabilistic Grammar Fuzzing" | https://www.fuzzingbook.org/html/ProbabilisticGrammarFuzzer.html — §§ Specifying Probabilities, Probabilities in Context, Learning Probabilities from Samples, Testing Uncommon Features, Learning Probabilities from Input Slices, Lessons Learned | learnt distributions, inversion, slices | include |
| FB-GEN | ibid., ch. "Fuzzing with Generators" | https://www.fuzzingbook.org/html/GeneratorGrammarFuzzer.html — §§ Example: Test a Credit Card System, Attaching Functions to Expansions, Checking and Repairing Elements after Expansion, Local Checking and Repairing, Definitions and Uses, Ordering Expansions, Lessons Learned | pre/post constraints, repair vs filter, def/use | include |
| FB-GREY | ibid., ch. "Greybox Fuzzing with Grammars" | https://www.fuzzingbook.org/html/GreyboxGrammarFuzzer.html — §§ Fuzzing with Dictionaries, Fuzzing with Input Fragments, Fuzzing with Input Regions, Focusing on Valid Seeds, Mining Seeds, Lessons Learned, Background | dictionary, fragment, region mutation; validity schedule; the only engine-style comparison in Part II | include |
| FB-RED | ibid., ch. "Reducing Failure-Inducing Inputs" | https://www.fuzzingbook.org/html/Reducer.html — §§ Why Reducing?, Delta Debugging, Grammar-Based Input Reduction, A Depth-Oriented Strategy, Comparing Strategies, Lessons Learned, Background | ddmin, grammar reduction, test counts | include |
| P-LANGFUZZ | Holler, Herzig, Zeller, "Fuzzing with Code Fragments", USENIX Security 2012 — cited in FB-GRAM Background and FB-GREY Background | as cited (not read here) | fragment recombination provenance; ">2 600 bugs" claim | park (cited via FB) |
| P-AFLSMART | Pham, Böhme, Santosa, Căciulescu, Roychoudhury, "Smart Greybox Fuzzing", arXiv 1811.09447 / TSE 2019 — cited in FB-GREY | as cited | region mutation, validity-based energy; "42 zero-days, 17 CVEs" | park |
| P-SUPERION, P-NAUTILUS, P-FORMATFUZZER | Wang et al. 2019; Aschermann et al. 2019; FormatFuzzer (Dutra, Gopinath, Zeller) — cited in FB-GREY Background | as cited | alternatives to hand-rolled structural mutators | park |
| P-DD | Zeller & Hildebrandt 2002; Misherghi & Su 2006 (HDD); Regehr et al. 2012 (C-Reduce); Herfert et al. 2017; Sun et al. 2018 (Perses); Kalhauge & Palsberg 2019 (J-Reduce) — FB-RED Background | as cited | reducer lineage | park |
| P-PROB | Pavese et al. 2018 "Inputs from Hell" (arXiv 1812.07525); Patra & Pradel 2016 "Learning to Fuzz" — FB-PROB Background | as cited | provenance of inversion/slicing | park |
| P-COV | Burkhardt 1967; Purdom 1972; Havrikov PhD thesis — FB-COV Background | as cited | provenance of expansion coverage | park |
| P-GRAMGEN | CSmith (Yang 2011, ">400 compiler bugs"), EMI (Le 2014, ">100 bugs"), Grammarinator (Hodován 2018, ">100 issues"), Domato — FB-GRAM Background | as cited | evidence that grammar generation finds real bugs in *strict* consumers (compilers, JS engines, DOM) | park |

Not independently verified in this session: every paper row (only the book's summary of them was read). Not found in the chapters although expected: Lämmel & Schulte 2006 and Havrikov & Zeller 2019 k-paths (FB-COV cites only Burkhardt, Purdom, Havrikov's thesis); Gopinath ddset and Picireny (not in FB-RED); Zest/JQF (not in FB-GREY).

## 3. Claim sheets

Conventions: *validity region* = where the technique pays off; *cost* as the chapter reports it; *confidence* high = printed output or explicit prose, medium = prose only, low = my inference.

### 3.1 Fuzzing with Grammars (FB-GRAM)

**Lessons Learned** (https://www.fuzzingbook.org/html/Grammars.html#Lessons-Learned): (1) grammars are powerful tools to express and produce syntactically valid inputs; (2) inputs produced from grammars can be used as is, or as seeds for mutation-based fuzzing; (3) grammars can be extended with character classes and operators to make writing easier.

**Core algorithm (simple_grammar_fuzzer)**: term := `<start>`; while the term contains nonterminals, pick one at random, pick one of its expansions at random, replace the first occurrence; accept only if the new term has < `max_nonterminals` (default 10) nonterminals, otherwise count a trial; after `max_expansion_trials` (default 100) raise `ExpansionError`. Representation: `Grammar = Dict[str, List[Expansion]]`, nonterminals `<...>`, start `<start>`, `opts()` attaches per-expansion options; EBNF (`?`, `+`, `*`, groups) converted to BNF; `srange`/`crange` character classes; `is_valid_grammar()` checks undefined/unused/unreachable symbols.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Grammars sit between regexes (fine for flat formats, not nested) and programs (can express anything but are per-target) | FB-GRAM § Input Languages | recursive/nested text formats | writing a grammar is manual work; "one needs a valid grammar in the first place" | high |
| Grammar output is syntactically valid but "semantic properties are hard to express", e.g. a port range 1024–2048 | FB-GRAM § A URL Grammar | — | semantic validation rejects most inputs → see FB-GEN | high |
| Grammar-generated strings are good *seeds* for mutation fuzzing ("explore the boundary between valid and invalid") | FB-GRAM § Grammars as Mutation Seeds | strict parsers | none stated | medium |
| The string-based simple fuzzer is inefficient and may fail/hang (infinite parentheses with `expr_grammar`) | FB-GRAM § A Simple Grammar Fuzzer; FB-GF § An Insufficient Algorithm | — | `ExpansionError`, 1 s timeout demo | high |
| Background claims: CSmith >400 compiler bugs; LangFuzz >2 600 browser bugs; EMI >100; Grammarinator >100 issues | FB-GRAM § Background | compilers, interpreters, DOM — strict, deep consumers | none stated; these are the authors' own reported numbers | medium (second-hand) |

Numbers: defaults `max_nonterminals=10`, `max_expansion_trials=100`; URL generation "within milliseconds".

### 3.2 Efficient Grammar Fuzzing (FB-GF)

**Lessons Learned** (https://www.fuzzingbook.org/html/GrammarFuzzer.html#Lessons-Learned): derivation trees are important for expressing input structure; tree-based grammar fuzzing is much more efficient than string-based, gives much better control over input generation, and effectively avoids infinite expansions.

**Core algorithm (GrammarFuzzer.expand_tree)**: node = `(symbol, children)`, `children=None` means unexpanded. Costs: `expansion_cost` = 1 if no nonterminals, ∞ if a symbol recurs on the current path (recursion), else 1 + Σ `symbol_cost` of children; `symbol_cost` = min over the symbol's expansions (e.g. `<digit>`=1, `<expr>`=5). Three phases: (1) **max-cost** expansion until `min_nonterminals` open symbols (default 0) — inflates the tree; (2) **random** expansion until `max_nonterminals` (default 10); (3) **min-cost** expansion until no open symbol remains — guarantees termination. Idea credited to Luke 2000.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Tree expansion is ~4× faster per input than string replacement and yields far smaller inputs | FB-GF § Putting it all Together: `simple_grammar_fuzzer` avg 0.100 s/input (50 trials, `max_nonterminals=15`), outputs "tens of thousands of characters"; `GrammarFuzzer` avg 0.026 s/input (50 trials, `max_nonterminals=20`); "much faster, but also our inputs are much smaller" | any grammar | size/throughput is still a parameter the user must set | high |
| min/max-nonterminal bounds give explicit size control; min-cost closing guarantees termination | FB-GF § Three Expansion Phases | recursive grammars | none stated | high |
| The derivation tree is the data structure every later technique (coverage, probability, generators, reduction, recombination) hangs off | FB-GF § Next Steps ("hub" chapter) | — | — | high |

### 3.3 Grammar Coverage (FB-COV)

**Lessons Learned** (https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html#Lessons-Learned): achieving grammar coverage quickly results in a large variety of inputs; duplicating grammar rules allows covering elements in specific contexts; achieving grammar coverage can help in obtaining code coverage.

**Core algorithm (GrammarCoverageFuzzer)**: coverage unit = *expansion* `"<symbol> -> expansion"`; `covered_expansions` set persists across `fuzz()` calls; `max_expansion_coverage(symbol, depth)` enumerates all reachable expansions; `missing_expansion_coverage()` = max − covered. Choice rule: among the alternatives of the node being expanded keep those with the largest set of *new* expansions reachable within depth d ("deep foresight"), raising d from 0 until some alternative yields novelty; tie-break randomly; when nothing is new fall back to random. `reset_coverage()` clears the set (the book does not reset automatically). Context: `duplicate_context(grammar, symbol)` clones a nonterminal per occurrence (`<integer-1>`, `<integer-2>`) so coverage is counted per context.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Coverage-driven choice reaches full expansion coverage in far fewer characters than random choice: EXPR 138.12 (random) / 52.28 (local) / 50.74 (foresight); CGI 211.34 / 68.64 / 40.38 (average output chars, 50 trials) | FB-COV § Covering Grammar Expansions, § Deep Foresight → All Together | any grammar; cheap | measures variety, not depth | high |
| EXPR_GRAMMAR has 24 expansions; `<integer>` reaches 12 | FB-COV § Tracking Grammar Coverage | — | — | high |
| Context duplication multiplies the target: `<expr>` once → 292 rules / 1 981 expansions; twice → 594 rules / 3 994 | FB-COV § Extending Grammars for Context Coverage Programmatically | when a program treats the same symbol differently by position | combinatorial growth; inputs get long | high |
| Grammar coverage correlates with code coverage: `cgi_decode` Pearson 0.8166, Spearman 0.9478 (p 2.3e-10), 100 trials × 10 inputs, `max_nonterminals=2`; `urlparse` Pearson 0.8819, Spearman 0.9487 (p 0.051), 100 trials × 20 inputs | FB-COV § Covering Code by Covering Grammars | shallow syntactic processors where each syntactic element drives a branch | the chapter: "will not hold for every program and every structure" — (a) *equivalent elements* treated uniformly (hostname characters, digits); (b) *deep data processing* (media decoders, ML) where no single syntactic element controls behaviour | high for numbers; the prose overstates them (§4) |
| Conclusion: to get high code coverage, "strive for high grammar coverage first" — not a guarantee | FB-COV § Will this always work? | — | — | high |

Cost: one set lookup per expansion choice; negligible. Needs: a grammar; for the *corpus* use (§5.ii) also a parser to attribute expansions to existing seeds (FB-PROB's `ExpansionCountMiner` does exactly that).

### 3.4 Parsing Inputs (FB-PARSE)

**Lessons Learned** (https://www.fuzzingbook.org/html/Parser.html#Lessons-Learned): grammars can generate derivation trees for a given string; PEGs are intuitive and easy to implement but take care to write; Earley parsers can parse arbitrary context-free grammars.

**Core idea**: a parser turns an *existing* input into a derivation tree, so seeds can be mutated and recombined structurally (feeds FB-GREY, FB-PROB mining, FB-RED). Motivating example (§ Why Parsing for Fuzzing?): a CSV inventory processor — 1 000 `GrammarFuzzer` rows from `CSV_GRAMMAR` "obviously not working" because the grammar does not know the kind must be `van`/`car`; a `PooledGrammarFuzzer` seeded with parsed valid values gets "somewhere". Ad-hoc `split(',')` CSV parsing collapses on quoted commas, embedded quotes, multi-line fields (RFC 4180). PEGParser: ordered choice, packrat memoisation, O(n); cannot express ambiguity, left recursion; `PEG_SURPRISE` grammar `<A>: ['a<A>a','aa']` generates 2n a's but PEG recognises only 2^n — PEG ≠ CFG except for LL(1). EarleyParser: predict/scan/complete over a chart; handles any CFG, ambiguity (parse forest), ε-rules via the Aycock–Horspool nullable fix; O(n³) general, O(n²) unambiguous, O(n) LR(k) with Leo's optimisation.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Parsing seeds is the enabling step for structured mutation/recombination and for mining probabilities | FB-PARSE § Synopsis, § Next Steps | you have real-world seeds and a grammar matching them | the grammar must match the input language exactly; seeds that do not parse contribute nothing (FB-GREY) | high |
| General CFG parsing is cubic; it dominates the cost of structural fuzzing | FB-PARSE § Background; FB-GREY (200 ms parse timeout; 94.94 s/300 inputs) | short inputs | throughput collapses on long inputs | high |
| Hand-rolled regex/ad-hoc parsers for real formats are "the path to insanity" | FB-PARSE § An Ad Hoc Parser | — | — | medium |

### 3.5 Probabilistic Grammar Fuzzing (FB-PROB)

**Lessons Learned** (https://www.fuzzingbook.org/html/ProbabilisticGrammarFuzzer.html#Lessons-Learned): by specifying probabilities one can steer fuzzing towards input features of interest; learning probabilities from samples allows focusing on features that are common or uncommon in samples; learning from a subset of samples allows producing more similar inputs.

**Core algorithm**: `(expansion, opts(prob=p))`; unannotated alternatives share the remaining mass equally; `choose_node_expansion` is a weighted draw. **Mining**: parse samples (EarleyParser) → count every `symbol -> expansion` in the trees → probability = count / total for that symbol (`ProbabilisticGrammarMiner`). **Inversion**: sort alternatives by probability and swap highest↔lowest pairwise (rare features become common — "Inputs from Hell"). **Slices**: learn from only the sample inputs that reached a code location, regenerate, repeat. **Context**: probabilities are per rule, not per position; use `duplicate_context` (`<octet-1>`…`<octet-4>`) to give positions their own distribution.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Specified probabilities are reproduced: leading-digit Benford weights 0.301…0.046 reproduced over 10 000 draws (0.3003, 0.1756, …, 0.0477) | FB-PROB § Expanding by Probability | — | p=0 expansions can still be taken in the min-cost closing phase | high |
| Learning from 9 URL samples yields https 0.667, http 0.222, ftps 0.111, ftp 0.0; inversion gives ftp 0.667, https 0.0 | FB-PROB § Learning Probabilities from Samples / Testing Uncommon Features | a corpus of real inputs exists | learnt values mirror sample habits only; inversion is not an involution under ties | high |
| Learning from the slice of inputs reaching `cgi_decode` line 25 raised the fraction of 100 random inputs reaching it 0.71 → 0.88 (→ 0.83 after three more rounds) | FB-PROB § Learning Probabilities from Input Slices | directing towards a specific location | exploration/exploitation trade-off; gains saturate and wobble | high |
| Rationale for inversion: "uncommon features are where bugs hide" — stated as motivation, with the caveat that the right choice "depends on where the bugs are" | FB-PROB § Testing Uncommon Features | — | — | medium |

### 3.6 Fuzzing with Generators (FB-GEN)

**Lessons Learned** (https://www.fuzzingbook.org/html/GeneratorGrammarFuzzer.html#Lessons-Learned): functions attached to grammar expansions can serve as *generators* (efficiently produce a symbol expansion), as *constraints* (check produced strings against complex validity conditions), and as *repairs* (apply changes such as checksums and identifiers).

**Core mechanisms**: `opts(pre=f)` — `f` runs before expansion; a string replaces the expansion, a list replaces the i-th nonterminal child, Python generators are called lazily; `opts(post=f)` — `f` receives the expanded child strings; `False` rejects (node reset and re-expanded; after `replacement_attempts` (default 10) a `RestartExpansionException` restarts the whole tree), a string/list *repairs*; `opts(order=[...])` fixes child expansion order so a post-condition sees definitions before uses; *local checking* runs post-functions as soon as a subtree is complete instead of at the end. Combination classes: `ProbabilisticGeneratorGrammarFuzzer`, `PGGCFuzzer` (coverage must be rebuilt from the final tree because rejected expansions were counted).

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| Without constraints 9/10 generated credit-card numbers fail the Luhn checksum; a *filter* needs ≈10 attempts per valid number; a *repair* needs one generation ("very efficient") | FB-GEN § Example: Checksums | any checksum/derived field | filter cost grows with the constraint's selectivity | high |
| Numeric ranges (100–200) via `pre=randint` are trivial as generators and awkward as grammar | FB-GEN § Example: Numeric Ranges | ranges, lengths | — | high |
| Matching XML tags / definition-before-use identifiers need repair or a symbol table + `order` | FB-GEN § Matching XML Tags, § Definitions and Uses, § Ordering Expansions | languages with identifiers, nested tags, references | global symbol table only — nested scopes need "carefully organizing" tables | high |
| Post-only filtering on a selective predicate (binary digits only) "can take several seconds" without local checking | FB-GEN § Local Checking and Repairing | — | restarts are costly; no retry bound on the top-level post path | medium |
| Generators make the grammar non-declarative and Python-specific; "we are not aware of another grammar-based fuzzing system that exhibits similar features" | FB-GEN § Background | — | portability; the approach is the book's own | high |

### 3.7 Greybox Fuzzing with Grammars (FB-GREY)

**Lessons Learned** (https://www.fuzzingbook.org/html/GreyboxGrammarFuzzer.html#Lessons-Learned): (1) a dictionary is useful to inject important keywords; (2) fragment-based mutation disassembles seeds into subtrees and reassembles them — it requires seeds that parse, which greybox-discovered seeds often do not; (3) region-based mutation labels substrings with grammar symbols and can delete/substitute them; it applies to all seeds, even partially parseable ones, but generated inputs still have low validity; (4) a validity-based power schedule spends more energy on more valid seeds and the generated inputs are then also more valid; (5) mining seeds from past failure-inducing inputs brings in fragments associated with failures.

**Core algorithms**: *DictMutator* — byte mutator plus "insert a random dictionary keyword at a random position". *FragmentMutator* (LangFuzz style) — parse each seed with Earley under a **200 ms** timeout; pool every subtree keyed by nonterminal; `swap_fragment` replaces a random subtree with a pooled fragment of the same symbol; `delete_fragment` replaces it by the empty tree; `LangFuzzer` applies 1–4 such mutations per candidate. *RegionMutator* (AFLSmart style) — for seeds that do not parse, read the Earley chart's *completed* states as regions `(start, end, symbol)`; swap/delete regions, so partially valid seeds remain usable. *Degree of validity* = length of the longest parsable prefix / total length. *AFLSmartSchedule*: energy = (validity / ln(len))^exponent. *GreyboxGrammarFuzzer.create_candidate*: pick seed by schedule → 0–4 structural mutations → byte mutations (`min(len, 2^k)`, k∈1..5) if no structural step ran, the seed has no structure, or a coin flip → keep the candidate if it adds coverage.

Printed experiment outputs (target: Python `html.parser` wrapped in `FunctionCoverageRunner`; two seeds; single runs):

| configuration | inputs | wall time | inputs that parse | statements covered | avg seed validity |
|---|---|---|---|---|---|
| Greybox, byte mutator only | 5 000 | 0.98 s | — | 79 | — |
| Greybox + DictMutator (HTML tags) | 5 000 | 2.78 s | — | 108 | — |
| Blackbox byte mutator | 300 | 0.10 s | 34 (11.33 %) | 167 | — |
| LangFuzzer (FragmentMutator, blackbox) | 300 | 94.94 s | 172 (57.33 %) | 93 | — |
| GreyboxGrammarFuzzer + FragmentMutator | 300 | 0.69 s | 2 (0.67 %) | 171 | — |
| GreyboxGrammarFuzzer + RegionMutator | 300 | 6.83 s | 11 (3.67 %) | 168 | 18.2 % |
| … + AFLSmartSchedule | 300 | 26.16 s | 9 (3.00 %) | 159 | 22.6 % |

Caveat: the 5 000-input and 300-input families use different setups; the extractor also saw a "94 statements" count next to the blackbox 167 — UNVERIFIED which runner it belongs to. Treat the rows as the chapter's qualitative story, which its prose states: LangFuzzer "produces more valid inputs but less coverage"; the greybox fragment fuzzer is faster and covers more than both; the region version is slower, covers more, yields fewer valid inputs; the validity schedule yields more fully valid inputs.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| A keyword dictionary is the cheapest structural aid and "already goes a long way" | FB-GREY § Fuzzing with Dictionaries | text formats with keywords/tags | 2.8× slower per input in the demo | high |
| Fragment recombination raises validity (57 % vs 11 %) but parsing cost cuts throughput ~1 000× (0.32 s vs 0.0003 s per input) and, on a lenient parser, coverage *drops* | FB-GREY § Fuzzing with Input Fragments | strict consumers (JS engines, compilers — LangFuzz's domain) | useless for seeds that do not parse; same-symbol swaps only; grammar must match | high |
| Region mutation rescues non-parsing seeds; validity stays low (3–4 %) | FB-GREY § Fuzzing with Input Regions | greybox corpora full of half-valid inputs | slower (6.8 s/300) | high |
| Validity-based energy raises population validity (18.2 → 22.6 %) at a coverage cost in the demo (168 → 159) | FB-GREY § Focusing on Valid Seeds | when validity is the bottleneck | trades coverage for validity; 4× slower | high |
| Past failure-inducing inputs are the best seeds (LangFuzz used CVE test cases) | FB-GREY § Mining Seeds | regression-rich projects | — | medium |
| Background numbers: LangFuzz 2 600 bugs; AFLSmart 42 zero-days / 17 CVEs; Superion +16.7 % line / +8.8 % function coverage, 30 bugs, 16 CVEs; Nautilus 6 CVEs; FormatFuzzer "thousands of valid inputs per second" from binary templates | FB-GREY § Background | — | second-hand, vendor-reported | medium |

### 3.8 Reducing Failure-Inducing Inputs (FB-RED)

**Lessons Learned** (https://www.fuzzingbook.org/html/Reducer.html#Lessons-Learned): reducing failure-inducing inputs to a minimum is helpful for testing and debugging; delta debugging is a simple and robust algorithm to reduce test cases; for syntactically complex inputs, grammar-based reduction is much faster and yields better results.

**Core algorithms**: *ddmin* — granularity n=2; split input into n chunks; test each complement (input minus one chunk); if a complement still FAILs adopt it and set n=max(n−1,2); otherwise if n ≥ len stop else n=min(2n,len); result is **1-minimal** (removing any single character makes the failure disappear); outcomes FAIL/PASS/UNRESOLVED; best case O(log n) tests, worst O(n²); `CachingReducer` memoises outcomes. *GrammarReducer* — parse the failing input; for each subtree try (a) another subtree of the same nonterminal found elsewhere in the tree, (b) an alternative expansion of the symbol with fewer children, filled from existing subtrees; sorted by node count; keep a replacement if the test still FAILs; *depth-oriented* variant tries the largest subtrees first and resets to depth 0 after each success. Every candidate is syntactically valid by construction, so UNRESOLVED outcomes vanish.

| claim | source | validity region | failure modes | confidence |
|---|---|---|---|---|
| ddmin reduces a 97-char fuzzed input to `()` in 29 tests | FB-RED § Delta Debugging | unstructured or lightly structured inputs; a fast deterministic test | — | high |
| On `1 + (2 * 3)` plain ddmin: 15 tests → `()` (syntactically invalid for the real target); with a parser-checked runner (`EvalMysteryRunner`) 21 tests and *no progress* — every candidate UNRESOLVED | FB-RED § Lexical Reduction vs. Syntactic Rules | — | lexical reduction "stalls" on inputs with syntax constraints | high |
| GrammarReducer: 5 tests → `(3)`; depth-oriented: 3 tests | FB-RED § The Reduction Strategy, § A Depth-Oriented Strategy | structured inputs with a grammar | needs grammar + parser | high |
| Long generated expression (`min_nonterminals=100`): grammar reducer 10 tests, 0.075 s → `(9)`; ddmin 900 tests, 1.605 s → a 59-char expression | FB-RED § Comparing Strategies | — | ddmin "orders of magnitude more tests", less perfect result | high |
| Prerequisites: a deterministic, repeatable, reasonably fast test — "the same prerequisites that make fuzzing effective"; the runner must return FAIL only for the *precise* error (e.g. `ZeroDivisionRunner` greps stderr for `ZeroDivisionError`); synopsis example `x = 1 + 2 * 3 / 0` → `3/0` | FB-RED § Synopsis, § Delta Debugging | — | otherwise the reducer slides to a different failure | high |
| Why reduce: cognitive load, communicability ("fails on `()`"), duplicate detection | FB-RED § Why Reducing? | — | — | high |
| Hypothesis's shrinking and the Debugging Book's `DeltaDebugger` are named as kin; C-Reduce, HDD, Perses, J-Reduce as the lineage | FB-RED § Background | — | — | high |

## 4. Disagreements and open questions

1. **Prose vs printed numbers (FB-COV, FB-PROB).** Text says "correlation coefficient of about 0.9" where 0.8166 is printed; "even stronger correlation of more than .95" where 0.8819 is printed; `urlparse` Spearman p = 0.051 is not significant at 5 %. FB-PROB says "97 % chance" of randomness where the χ² p-value printed is 0.179 and "p = 0.0" where 3.9e-89 is printed. Consequence: the agent's skill text must quote printed values, and the design doc must not inherit the stronger wording.
2. **Validity vs coverage pull in opposite directions in FB-GREY.** Every step that raises syntactic validity (fragments 57 %, validity schedule 22.6 %) lowered or did not raise statement coverage on the lenient HTML parser; the chapter frames this as a trade-off, not a win. This contradicts the common slogan "structure-aware fuzzing gets deeper". Resolution offered by the material itself: LangFuzz/AFLSmart/Superion/Nautilus report their wins on *strict* consumers (JS engines, compilers, PHP, Lua) — the validity region is "strict parser in front of deep logic", and the HTML demo lies outside it. Open: no chapter quantifies the strict-parser case; cross-check with the greybox/structure-aware report of this series.
3. **Grammar coverage as test adequacy** is argued by two shallow Python functions with max two nonterminals per input; the chapter's own "Will this always work?" denies generality. Open: whether k-path (Havrikov & Zeller 2019) results change the picture — not in the chapter, UNVERIFIED.
4. **Reducer baselines** are toy: 97-char and ~100-node inputs, single runs. The qualitative gap (10 vs 900 tests) is consistent with HDD/Perses literature but not evidence of magnitude for real inputs.
5. **Generators are the book's own design** (FB-GEN Background admits no comparable system). The property-based-testing tradition (Hypothesis/QuickCheck `builds`/`map`/`filter`, `arbitrary`) implements the same constructive-vs-filter distinction natively; the two traditions agree on the lesson (construct, do not filter) but the book does not cite PBT here. Record as agreement reached independently.
6. **ddmin minimality vs validity**: ddmin's `()` result for `1 + (2 * 3)` is 1-minimal yet meaningless for a target that parses first; the chapter treats the parser-checked runner as the honest oracle. Open for the agent: which reducers in the Go/Rust/Python toolchains are structure-aware (none in the standard engines as far as this material goes — UNVERIFIED, belongs to the per-language reports).
7. **Not in the chapters**: throughput comparison between grammar *generation* and coverage-guided mutation on a strict target; corpus-size guidance; anything on binary formats beyond a FormatFuzzer mention.

## 5. Implications for the agent / skills

### 5.i Deciding: grammar vs typed generator vs seed corpus + byte mutation (H1, H3)

Decision table the applicability skill should carry (evidence column = chapter claim):

| signal the agent can observe | choose | evidence |
|---|---|---|
| Parser is lenient/tolerant (HTML-like, "best effort", recovers from errors) or input is a flat/regular format (key=value, CSV line, log line, flags) | **seeds + byte mutation + dictionary of keywords**; no grammar | FB-GREY: bytes 167 vs fragments 93 statements; dictionary +37 %; FB-GRAM: regexes suffice for flat formats |
| Random/mutated inputs are rejected early (validation error on >90 % of inputs; coverage flat on the parser's error path) and the format is recursive/nested text (expressions, queries, JSON-like, config DSL, markup) | **grammar-generated seed corpus** (GrammarFuzzer with `max_nonterminals` bound, coverage-driven choice) → hand the corpus to the engine's byte mutator; add the grammar's terminals as dictionary | FB-PARSE CSV example (1 000 random rows, almost none pass); FB-GRAM "seeds for mutation-based fuzzing"; FB-COV full coverage in ~50 chars |
| A grammar already exists in the repo or spec (ANTLR/EBNF/PEG file, RFC ABNF, tree-sitter) | reuse it; never author a second one; grammar must match the real language or seeds will not parse and fragments are lost | FB-PARSE "grammar must match"; FB-GREY LL2 |
| Validity needs *semantic* facts: checksums/CRC, length prefixes, matching identifiers/tags, defined-before-used, numeric ranges, sorted/unique keys | **typed generator** (Hypothesis `st.builds`/`composite` with `.map`, Rust `Arbitrary` struct + encoder, Go struct from `f.Fuzz` args or a small decoder) that *constructs* the invariant; keep a raw-byte harness beside it to reach the rejection branches | FB-GEN: 9/10 fail Luhn; filter ≈10×; repair 1×; def/use needs a symbol table; FB-GRAM port-range caveat |
| Target is a typed API (functions over structs), not a byte stream | typed generator; a grammar is the wrong abstraction | FB-GEN LL1 ("generators … to efficiently produce a symbol expansion") — the chapters' `pre` functions are exactly PBT strategies |
| Throughput matters (engine does ≥10 k exec/s) and structural mutation would need parsing each candidate | do structure at *seed-generation time*, not per candidate; parsing is O(n³) and cost the book 94.94 s/300 inputs | FB-GREY (200 ms parse timeout, blackbox "about 10k inputs per second"); FB-PARSE complexity |
| A corpus of real inputs exists | mine it: seeds, dictionary tokens, and (optionally) learnt expansion probabilities; invert probabilities to target rare features | FB-PROB LL2/LL3; FB-GREY LL5 (past failures are the best seeds) |

Rules of thumb to state in the skill:
- *Construct, don't filter.* Any `.filter()`/`assume()`/`post=False` that rejects >50 % must be rewritten as a `.map()`/repair (FB-GEN checksum numbers).
- *Bound size explicitly* (`max_nonterminals`, Hypothesis `max_size`/`max_leaves`, Rust `size_hint`); unbounded recursive generators recreate the simple-fuzzer hang (FB-GF).
- *Keep the byte-level path.* Every structured harness also needs the unstructured one, or the parser's error handling is never fuzzed (FB-GRAM "boundary between valid and invalid"; FB-GREY coverage results).
- *One grammar per language, context-free only*; push every non-CF constraint into generator/repair code (FB-GEN "would be no fun at all" to write a CSG).

### 5.ii Grammar coverage as corpus-adequacy criterion and stopping signal (H2)

Procedure for the corpus skill:
1. Enumerate expansions of the grammar (`max_expansion_coverage`); EXPR-size grammars have tens, duplicated-context grammars thousands — restrict to 1-context plus hand-picked duplications where the target demonstrably treats positions differently (FB-COV: 24 → 1 981 → 3 994).
2. Parse each existing seed and record which expansions it exercises (the `ExpansionCountMiner` idea from FB-PROB); `missing = max − covered`.
3. Generate seeds with coverage-driven choice until `missing` is empty; expect few inputs (FB-COV: ~40–50 output characters for toy grammars).
4. **Stop seed construction** when `missing` is empty **and** adding the last k seeds added no new code coverage. Grammar coverage alone is *necessary, not sufficient* (FB-COV "will not hold for every program"): equivalent-element classes and deep processing stay dark.
5. Report the adequacy number ("N/M expansions covered by the corpus") in the harness README — it is the one metric that is independent of the engine and reproducible in CI.
6. Do **not** use grammar coverage as the stop signal for the fuzzing campaign itself; that remains a code-coverage/plateau decision (other reports). It is a stop signal for "is my corpus good enough to start".
7. For typed generators without a grammar, the analogue is branch coverage of the strategy (each `one_of` alternative, each recursion depth, each optional field present/absent) — instrument with Hypothesis `event()`/`target()`; this mapping is mine, not the chapter's (UNVERIFIED).

### 5.iii Reducing a failing structured input before reporting (H5)

Checklist the reporting skill should carry:
1. **Fix the oracle first**: a runner that returns FAIL only on the *same symptom* (exception type + message / sanitizer report + top frame), PASS on clean exit, UNRESOLVED on anything else — else reduction wanders to a different bug (FB-RED § Synopsis `ZeroDivisionRunner`).
2. **Require determinism and speed**: run the candidate three times before trusting a FAIL; reduction budgets are O(n²) tests worst case (FB-RED).
3. **Pick the reducer by structure**: unstructured/binary → ddmin on bytes (29 tests for 97 chars); structured text with a grammar → grammar/tree-based reduction (10 vs 900 tests; result `(9)` vs 59 chars); typed inputs → the generator's shrinker (Hypothesis shrinks automatically — FB-RED § Background names it). Engine-native minimisers (libFuzzer `-minimize_crash`, `cargo fuzz tmin`, Go's built-in minimisation) are lexical ddmin-style; whether any is structure-aware is for the per-language reports (UNVERIFIED here).
4. **Keep candidates valid**: when a grammar exists, parse the reduced input before accepting it; a lexical reducer that returns `()` for an expression language has produced an UNRESOLVED input, not a reproducer (FB-RED § Lexical Reduction vs. Syntactic Rules).
5. **Prefer large-subtree-first** (depth-oriented: 3 tests vs 5) when writing any custom reducer.
6. **Report**: minimal input (quoted and as a corpus file path), the exact symptom check, test count/time of reduction, and the un-reduced original for provenance (FB-RED § Why Reducing?: communicability and duplicate detection).

### 5.iv Chapter material that is too academic for a practising agent

Drop from skills (keep only a one-line pointer): Earley internals (chart, predict/scan/complete, Aycock ε-fix, Leo), parse forests and tree extractors, LL(1) tables and first/follow sets, PEG-vs-CFG surprises beyond "ordered choice differs", railroad diagrams, Benford/χ² "unnatural number" detection, deep `duplicate_context` beyond depth 1, the `PGGCFuzzer` multiple-inheritance algebra and `inheritance_conflicts`, FragmentMutator/RegionMutator/AFLSmartSchedule implementation (the agent should not reimplement structural mutators; it should pick an engine or a typed generator), and all exercises. Keep as concepts with one sentence each: derivation tree; min/max-cost expansion with size bounds; expansion coverage; parse-seeds-to-recombine; pre/post constraints = construct/repair; validity vs coverage trade-off; ddmin; grammar reduction.

## 6. Candidate eval cases

| # | input the agent sees | expected behaviour | why (source) |
|---|---|---|---|
| 1 | Go package parsing a `KEY=VALUE` `.env` file; 40 lines of code; strings and quotes only | Structured but a grammar is overkill: write a native `testing.F` harness with 3–5 seed lines and a small dictionary (`=`, `"`, `\n`, `#`, `export`); no grammar, no custom generator | regular language → regex/flat (FB-GRAM § Input Languages); dictionary is the cheap structural aid (FB-GREY LL1) |
| 2 | Rust crate decoding a binary frame: 2-byte length prefix, payload, CRC32 trailer | Typed generator: `Arbitrary` for payload, encoder that *computes* length and CRC (repair), plus a raw-`&[u8]` target for the mismatch paths; must not propose a grammar; must not `filter` on CRC validity | FB-GEN checksums (filter ≈10×, repair 1×); FB-GRAM semantic caveat |
| 3 | Python expression/filter language with an existing ANTLR grammar in the repo and a strict parser (`SyntaxError` on 95 % of random strings) | Reuse the grammar to generate a bounded, coverage-complete seed corpus (report "N/M expansions covered"), store under the ecosystem corpus location, feed to Atheris/Hypothesis; keep a raw-bytes harness too | FB-PARSE CSV failure; FB-COV coverage-driven seeds; FB-GREY structure at seed time, not per candidate |
| 4 | Lenient Markdown-to-HTML converter; agent's draft plan says "write a full Markdown grammar and a custom mutator" | Reject the plan: tolerant parser → seeds from real documents + byte mutation + dictionary (`#`, `*`, `[`, `](`, backticks); cite the validity/coverage trade-off | FB-GREY table (bytes 167 vs fragments 93 statements) |
| 5 | Campaign state: 38 seeds, grammar expansion coverage 24/24 (1-context), parser line coverage unchanged over the last 20 generated seeds | Say "corpus is adequate, stop generating seeds, start/continue the engine run; do not duplicate contexts beyond depth 1" | FB-COV numbers and "Will this always work?"; §5.ii rule 4–6 |
| 6 | A 4 KB JSON-like crash input found by the engine; failure is `IndexError` in a Python parser | Before filing: build a same-symptom runner, confirm determinism, reduce structure-aware (tree/tmin + parse check), produce a ≤1-line reproducer and the symptom assertion; refuse to report the 4 KB blob | FB-RED all claims; §5.iii |
| 7 | Template language with `{% set x %}` … `{{ x }}`; grammar-generated inputs are 90 % "undefined variable" errors | Move from grammar to a generator with a symbol table and ordered expansion (define before use), or a repair step that renames uses to defined names | FB-GEN § Definitions and Uses, § Ordering Expansions |
| 8 | Production log corpus of 10 k real URLs is available; task: fuzz a URL router | Mine the corpus for seeds and dictionary; optionally learn expansion probabilities and *invert* them for a second generator aimed at rare schemes/params; do not hand-write a URL grammar from scratch | FB-PROB LL2/LL3 (https 0.667 → inverted ftp 0.667); FB-GREY LL5 |
| 9 | "Fuzz `strconv.Atoi`" | Do not build structure: integers are a regular language; a seeds+bytes harness or a `testing.F` with `int`-typed args suffices; probably "do not fuzz" at all unless a custom implementation exists | FB-GRAM regex boundary; H1 gate |

## 7. Micro-examples

**7.1 Filter vs repair (FB-GEN, https://www.fuzzingbook.org/html/GeneratorGrammarFuzzer.html § Example: Checksums).** The book's grammar generates 16-digit numbers; 9 of 10 fail the Luhn check. With `opts(post=check_credit_card)` the fuzzer discards and retries — "about 10 attempts" per valid number; with `opts(post=fix_credit_card)` the last digit is recomputed once. Translation for the agent's Python skill (illustrative, not agent code):

```python
# filter — ~10× waste, mirrors opts(post=check)
cards = st.text("0123456789", min_size=16, max_size=16).filter(valid_luhn)
# repair — one draw, mirrors opts(post=fix)
cards = st.text("0123456789", min_size=15, max_size=15).map(append_luhn_digit)
```

**7.2 Reduction budgets (FB-RED, https://www.fuzzingbook.org/html/Reducer.html § Comparing Strategies).** Same failing expression generated with `min_nonterminals=100`, same `eval`-based mystery oracle:

| reducer | tests | time | result |
|---|---|---|---|
| GrammarReducer (tree-based) | 10 | 0.075 s | `(9)` |
| DeltaDebuggingReducer (ddmin, characters) | 900 | 1.605 s | `((2 - 1 - 2) * 8 + (5) - (4)) / ((2) * 3) * (9) / 3 / 1 - 8` |

And for `1 + (2 * 3)` with a parser-checked oracle: ddmin 21 tests, zero progress (every candidate UNRESOLVED); tree reducer 5 tests (3 depth-first) → `(3)`.

**7.3 Corpus adequacy by expansion coverage (FB-COV, https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html § Deep Foresight → All Together).** Average output characters until all expansions are covered, 50 trials:

| grammar | random choice | uncovered-first (local) | uncovered-first with foresight |
|---|---|---|---|
| EXPR (24 expansions) | 138.12 | 52.28 | 50.74 |
| CGI | 211.34 | 68.64 | 40.38 |

**7.4 Structure vs bytes on a lenient parser (FB-GREY, https://www.fuzzingbook.org/html/GreyboxGrammarFuzzer.html § Fuzzing with Input Fragments).** 300 inputs each against `html.parser`: blackbox bytes 0.10 s, 11 % parse, 167 statements; LangFuzz-style fragments 94.94 s, 57 % parse, 93 statements; greybox + fragments 0.69 s, 0.7 % parse, 171 statements. Validity and coverage are different axes; the agent must know which one the target starves for.
