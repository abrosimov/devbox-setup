---
note_id: "202611031507002"
modified: 2026-11-11
created: 2026-11-03
language: en
type: meta
subtype: open-question
note_role: artifact
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["FTW-OQ-002"]
tags: [fuzzing, design/open-question]
status: deferred-to-authoring
blocks: ["[[automation-scripts]]", "[[reference-documents]]"]
related: ["[[language-facts-rust]]", "[[language-facts-python]]"]
---
# FTW-OQ-002: Engine-output semantics need edition-specific verification

**Disposition (2026-11-10):** deferred-to-authoring.

Before implementing a parser, verify field meanings against primary documentation and the actual
engine build, then retain representative raw logs and independent parser tests. Unknown fields are
unknown, not zero. This blocks exact parser claims, not the research lifecycle methodology. Do not derive
saturation or residual risk from a feature-count column.
