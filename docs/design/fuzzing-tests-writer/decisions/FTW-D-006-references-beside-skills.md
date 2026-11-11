---
note_id: "202611031506006"
modified: 2026-11-12
created: 2026-11-03
language: en
type: meta
subtype: decision
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-D-006"]
tags: [fuzzing, design/decision]
status: accepted
supersedes: []
superseded_by: []
related: ["[[reference-documents]]", "[[research-index]]"]
---
# FTW-D-006: References accompany the operations that need them

*Amended in draft on 2026-11-10 by the methodology revision ([[methodology-review]]).*

Keep concise operational references beside the skill that consumes them when authoring. The
historical annexes remain in `docs/design/fuzzing-tests-writer/research/` as evidence, not automatically
loaded context. [[reference-documents]] defines the required subjects without creating extra skills.

**Basis:** separate executable instructions from provenance and long historical research; SYSE.48.
[[repository-placement]] records the authored layout and loading choices for Claude Code and Codex.
[[authoring-validation]] separates local checks from actual provider behaviour still to qualify.

**Alternatives:** a Claude-only global docs path would bind shared method to one provider; copying
all annexes into skills would import superseded policies and excluded material. Where references are
shared, keep one meaning and verify packaging rather than duplicating incompatible rules.
