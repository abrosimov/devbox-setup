---
note_id: "20261103150102"
created: 2026-11-03
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

- **Name**: fuzzing-tests-writer capability (agent + skills + scripts + evals).
- **Boundary**: given a diff, module or named entry point in a Go, Python or Rust repository, it
  decides whether and how to fuzz, writes the harness and seed corpus, wires the seed corpus into the
  normal test run and a budgeted fuzz job, runs a bounded campaign, and returns a campaign report
  with bucketed findings.
- **Not inside the boundary**: continuous-fuzzing infrastructure (OSS-Fuzz, ClusterFuzzLite) beyond
  producing targets it can consume; example-based unit tests (`unit_tests_writer` keeps them);
  fuzzing across network, database or filesystem boundaries.
- **Parts**: [[agent-procedure]]; three methodology skills ([[skill-fuzzing-applicability]],
  [[skill-fuzzing-campaign]], [[skill-structured-input-generation]]); three language skills
  ([[skill-go-fuzzing]], [[skill-python-fuzzing]], [[skill-rust-fuzzing]]); [[reference-documents]];
  [[automation-scripts]]; [[eval-fixtures]] and suites.
- **Crossings**: receives work from `/techne-fuzz` (see [[FTW-D-005-techne-fuzz-command]]) or the
  user; produces files for the repository and a report for `code_reviewer` / the user; consumes the
  engine command lines (`go test -fuzz`, `cargo fuzz`, `pytest`, Atheris harnesses) and their stdout.
- **Context rules**: British English; `techne-` prefix for any command; skills vendor-neutral to be
  admitted to the Codex shared list; the global rules budget is untouched because nothing here goes
  into the global rules.
