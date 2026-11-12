---
note_id: "202611031506007"
created: 2026-11-03
modified: 2026-11-10
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-007"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[language-facts-go]]", "[[skill-go-fuzzing]]"]
---
# FTW-D-007: Research target and runtime verification are distinct

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

Retain Go 1.27.3 as the historical target recorded by R7 §8 and §8.1. This document pass neither
installs that toolchain nor reruns those experiments. A future authoring task must verify the selected
repository toolchain, current primary documentation and the commands actually shipped.

**Basis:** [[07-lang-go|R7]] is dated evidence, not a perpetual compatibility promise;
[[language-facts-go]] and [[skill-go-fuzzing]] state verification obligations.

Do not silently upgrade a target repository or prescribe a download/proxy override from this study.
If its selected version differs, qualify the affected operation against that version. Source reading,
compilation, seed replay and active fuzzing are different evidence. Record each actually performed
check and its limits; `go vet` alone is not a compilation/replay qualification.
