---
note_id: "20261103150102"
created: 2026-11-03
modified: 2026-11-11
language: en
type: design
subtype: framing
note_role: artifact
artifact_kind: system-characterisation
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["System characterisation"]
tags: [fuzzing, design/framing]
related: ["[[fpf-framing]]", "[[agent-procedure]]", "[[repository-placement]]"]
---
# System characterisation

**System of interest:** a fuzzing agent, six skill procedures, persistent research support and
independent evaluations. Intended engines: Claude Code and Codex. Languages: Go, Python and Rust.

**Input after invocation:** an authorised scope, a research question and receiving use, relevant
commit/experiment/dataset snapshot, available contracts/seeds and any prior checkpoint. The
procedure recovers existing conclusions before assessing a justified next experiment; it records
the charter before writing a target. It does not choose its own
invocation policy; discovery, routing and command selection are deferred.

**Work inside the boundary:** inspect the scoped input-processing path, justify a fuzzing oracle,
construct or adapt a target and seeds, compile and replay, conduct an admitted experiment,
classify findings, retain useful inputs and report evidence. Correcting a harness the agent wrote
is included; fixing product code is separate work.

**Outputs:** reviewable target/corpus changes, replay instructions, evidence and a durable research
record with ACTIVE/PAUSED/CLOSED state and its reason. Experiment status and finding classification
are separate. A completed process need not answer the research question; a closed question can
retain an explicitly inconclusive answer. Pauses preserve useful progress across sessions.

**Outside this capability:** PBT, mutation analysis, continuous-fuzzing infrastructure provisioning,
unrequested CI changes, external publication and autonomous product repairs. Network/database/GUI
integration campaigns are not supplied operations in this edition. Local files needed for an
isolated input-processing harness are not categorically forbidden, but effects must remain within
the authorised workspace and justified experiment limits.

**Parts and responsibilities:** [[agent-procedure]] sequences work; the six `skill-*` notes supply
operations; [[automation-scripts]] specifies checkpoint, evidence and transition support;
[[eval-plan]] specifies independent qualification. [[repository-placement]] records authoring
constraints without pretending shared configuration has identical provider semantics.

**Context:** repository conventions and user authority govern effects. Useful inputs remain
available for replay. Retention does not authorise Git commits. A tool allowlist does not establish
filesystem or network isolation. The eventual provider adapters must demonstrate the facilities
that enforce the shared contract.

**Identity boundary:** the research question/use persists while relevant subject versions are recorded.
A new commit or dataset requires checking affected assumptions; it does not reset all evidence.
Changed scope has a linked successor only within authority. An agent session is an execution episode,
not a new research identity. [[stopping-algorithm]] owns these rules.
