# Oracle selection and qualification

An oracle decides whether an observed execution violates a stated expectation. Select checks for
the question at hand; a more complex check is not automatically more reliable or necessary.

| Check | Establish before relying on it | Limit of a failure |
|---|---|---|
| Crash, panic or exception | The call is permitted; distinguish documented rejection/precondition behaviour | Unexpected termination needs classification as product, harness or environment failure |
| Resource use | A relevant bound, measurement interval, setup and execution conditions | An engine timeout or minimisation interval alone does not establish a product hang |
| Round trip or canonicalisation | Semantic equality, normalisation, lossiness and supported input domain | Different serialised spelling may be allowed |
| Differential comparison | Shared specified domain, comparable settings and independent expected examples | Disagreement does not identify which implementation is wrong |
| Invariant or postcondition | The actual contract and an independently inspectable checker | A plausible assertion is not necessarily a requirement |
| Metamorphic relation or existing model | An established relation and its assumptions already fit the fuzzing task | Do not build a separate PBT or model-testing project |
| Sanitizer diagnostic | Supported build and active instrumentation on the relevant execution | The diagnostic covers its reported failure class, not all correctness |

For example, before asserting `decode(encode(x)) == x`, establish which values the pair supports and
what equivalence the contract promises. If encoding normalises ordering, compare the promised
semantics rather than inventing byte equality. A comparator sharing the target's defect is not
independent confirmation.

Before accepting a candidate failure:

1. Preserve original bytes, diagnostic, command, configuration and subject version.
2. Compare the assertion with contract examples and ordinary tests. Check expected domain errors
   separately from unexpected failures; broad exception suppression can hide the sought defect.
3. Replay the input independently of the search loop when feasible within the current experiment.
4. Classify the result as confirmed product failure, harness/oracle error, environment failure,
   unconfirmed failure or no finding. An unresolved comparator remains an unresolved comparator.
5. Correct an authored harness error within scope and identify earlier results dependent on it.
   Report product defects without silently expanding into product repair.

For reduction, test the same relevant symptom, not any non-zero exit. Keep originals and useful
non-crashing inputs. Neither successful replay nor a crash count establishes absence of other bugs.
