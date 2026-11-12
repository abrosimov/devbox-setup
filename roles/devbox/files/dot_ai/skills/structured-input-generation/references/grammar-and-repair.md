# Grammar, repair and structured reduction

Use these operations only when they supply the current observation. Reuse an adequate existing
grammar, decoder or seed set; do not create a grammar framework merely because inputs are structured.

## Generate bounded syntax

A grammar expansion can build a derivation tree and then serialise its terminal leaves. For
recursive productions, establish a terminating alternative and bound tree depth, output size and
expansion work. Near the bound choose a terminating construction rather than allowing uncontrolled
recursive growth. Check the serialised result with independently expected accepted/rejected cases.

Track alternatives exercised when that distinction matters to the investigation. Unvisited
productions can guide a bounded next sample, but different productions can reach the same product
behaviour. Report grammar observations separately from instrumented product-path observations.

The [efficient grammar generation chapter](https://www.fuzzingbook.org/html/GrammarFuzzer.html)
describes derivation trees and controlled expansion; the
[grammar coverage chapter](https://www.fuzzingbook.org/html/GrammarCoverageFuzzer.html) distinguishes
grammar variety from its sometimes limited effect on code coverage. These mechanisms guide input
construction; their examples do not establish local performance or campaign completeness.

## Repair dependent fields

For length, count or checksum dependencies, compute fields from the generated payload where the
format permits it. Keep the transformation deterministic and bounded. Store the raw engine input
and the decoder/repair version so replay reconstructs the tested bytes. Inspect the actual target
call: repairs that make the input syntactically acceptable may still stop before the intended path.

For example, a repaired frame can exercise an optional-field decoder while an unmodified malformed
frame exercises rejection. Keep both routes when both behaviours are in scope. A repair that always
corrects the checksum cannot simultaneously claim to test bad-checksum handling.

## Develop a new direction from inputs

Compare a small set of unfamiliar nested or optional constructs with existing seeds. Preserve any
useful behavioural distinction and the material needed to repeat it. A result may suggest a new
question before its eventual value is known. If the sample reaches no useful difference, retain
that limited observation without declaring all other structures uninteresting or automatically
expanding the investigation.

The [mutation-based fuzzing chapter](https://www.fuzzingbook.org/html/MutationFuzzer.html) describes
using seeds and their mutations as search material. Retain useful seeds for replay as well as
further search. Byte-level novelty alone does not establish a new behavioural contribution.

## Reduce while preserving meaning

When byte deletion breaks required syntax before the failure, consider replacing a subtree with
a smaller compatible subtree or simpler production, or shortening a decoded operation sequence.
Recompute dependent fields where the same execution requires them. Re-run the actual same-symptom
predicate after each candidate; valid syntax alone does not establish preserved failure.

The [reduction chapter](https://www.fuzzingbook.org/html/Reducer.html) develops grammar-aware
reduction alongside ordinary delta debugging. Keep the original and last verified candidate when
a candidate is unresolved or execution is interrupted. Resume the recorded unfinished check only
while its target, observation and representation assumptions remain applicable.

Sources checked 2026-11-12. This workflow uses these fuzz-input mechanisms; it introduces no PBT
or mutation-analysis operation.
