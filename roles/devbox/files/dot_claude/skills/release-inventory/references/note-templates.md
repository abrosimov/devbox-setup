# Note templates

Templates for notes created by the `release-inventory` skill. Fill every `{{placeholder}}`; never emit a template with placeholders left in. All prose in British English.

`status` in front matter mirrors the Jira status category, not the status name:

| Jira status category | front matter `status` | Table glyph |
| --- | --- | --- |
| To Do (`new`) | `🚫` | 🚫 |
| In Progress (`indeterminate`) | `🟡` | 🟡 |
| Done (`done`) | `✅` | ✅ |

---

## Bug — `Release-{{X.Y}}/Bugs/{{KEY}}.md`

```markdown
---
tags:
  - project
  - bug
status: {{🚫|🟡|✅}}
aliases:
  - {{kebab-case-symptom}}
  - {{kebab-case-alternative}}
---
# {{Jira summary}}

## Meta
| Jira issue                                                           | Gitlab MR |
| -------------------------------------------------------------------- | --------- |
| [{{KEY}}](https://openinnovationai.atlassian.net/browse/{{KEY}}) | [MR]()    |

- Sprint: {{v1.17.0}}. {{fixVersion line — see the rule in SKILL.md §3}}. Release: [[Release {{X.Y}}]].
- Type: **Bug**. Jira status: **{{status name}}**. Priority: **{{priority}}**.
- Reporter: {{name}}. Assignee: {{name}}. Created {{YYYY-MM-DD}}, last updated {{YYYY-MM-DD}}.
- {{Parent epic: [[KEY]] | No parent epic}}. {{Branch or "No branch yet"}}.

## Bug summary
{{Reporter's description. Quote it verbatim when it is one or two sentences — paraphrase loses the reporter's exact wording, which is often the only evidence of which endpoint or flow they hit.}}

**Steps to reproduce**
1. {{…}}

**Expected** — {{…}}

**Actual** — {{…}}

**Environment** — {{…}}

## Root cause
*Pending — no investigation yet.*

## Plan
- [ ] Reproduce
- [ ] Root cause
- [ ] Create a branch in git
- [ ] Fix + unit test
- [ ] Run all unit tests
- [ ] Create MR
- [ ] Perform self-review
- [ ] Switch Jira task status to "Under review"
- [ ] Assign MR to reviewer
- [ ] Wait until code review is passed
- [ ] Merge MR
- [ ] Test on dev
- [ ] Switch Jira task status to "In testing"
- [ ] Change this project status to "Resolved"

## Related information
- {{[[KEY]] — one line on why it is related}}
```

---

## Task — `Release-{{X.Y}}/Tasks/{{KEY}}.md`

Same front matter with `- task` instead of `- bug`, then:

```markdown
# {{Jira summary}}

## Meta
| Jira issue                                                           | Gitlab MR |
| -------------------------------------------------------------------- | --------- |
| [{{KEY}}](https://openinnovationai.atlassian.net/browse/{{KEY}}) | [MR]()    |

- Sprint: {{v1.17.0}}. {{fixVersion line}}. Release: [[Release {{X.Y}}]].
- Type: **Task**. Jira status: **{{status name}}**. Priority: **{{priority}}**.
- Reporter: {{name}}. Assignee: {{name}}. Created {{YYYY-MM-DD}}, updated {{YYYY-MM-DD}}.
- Parent epic: [[{{EPIC-KEY}}]]. {{"No description in Jira beyond the summary." when true — that absence is itself a finding.}}

## Objective
{{Jira description, or an explicit statement that there is none.}}

## Plan
- [ ] {{…}}

## Related information
- {{[[EPIC-KEY]] — the parent epic}}
```

---

## Epic — `Release-{{X.Y}}/Epics/{{KEY}}/{{KEY}}.md`

Epics get a **directory**, not a bare file: they accumulate companion notes (design docs, findings, reviews) and those belong next to the epic.

```markdown
---
tags:
  - project
  - epic
status: {{🚫|🟡|✅}}
release:
  - "[[Release {{X.Y}}]]"
aliases:
  - {{kebab-case-theme}}
---
# {{Jira summary}}

## Meta
| Jira issue                                                           | Gitlab MRs |
| -------------------------------------------------------------------- | ---------- |
| [{{KEY}}](https://openinnovationai.atlassian.net/browse/{{KEY}}) |            |

- Sprint: {{v1.17.0}}. {{fixVersion line}}. Release: [[Release {{X.Y}}]].
- Type: **Epic**. Jira status: **{{status name}}**. Priority: **{{priority}}**.
- Reporter: {{name}}. Assignee: {{name}}. Created {{YYYY-MM-DD}}, updated {{YYYY-MM-DD}}.

## Children

| Key | Type | Status | Assignee | Mine? | Sprint | Summary |
| --- | --- | --- | --- | --- | --- | --- |
| [[{{KEY}}]] | {{Task}} | {{🟡 In Progress}} | {{name}} | {{yes/no}} | {{v1.17.0}} | {{summary}} |

{{Call out any child whose sprint differs from the epic's, or which has no sprint at all — a sprintless child cannot be placed in any release by the §3 rule and will silently miss the cut.}}

## Objective
{{…}}

## Working surface
{{Links to companion notes in this directory.}}

## Related information
- [[Release {{X.Y}}]]
```

---

## Release note — `Release-{{X.Y}}/Release {{X.Y}}.md`

The release note is an **index, not a digest**. It carries the inventory table and pointers. Root causes, evidence, plans and reviews live in the ticket notes and are never copied here.

```markdown
---
release-version: "{{X.Y}}"
---
# Top
{{Free-form. Never rewrite or reorder this section — it is hand-maintained.}}

# Meta
- Sprint **{{v1.17.0}}** (board {{n}}, id {{n}}) — {{start}} → {{end}}. State `{{future|active|closed}}` at pull time.
- **{{n}} issues** where I am assignee or reporter — {{n}} Epic, {{n}} Tasks, {{n}} Bugs.
- Inventory pulled from Jira on {{YYYY-MM-DD}} via
  `{{the exact JQL}}`.
- Naming: sprints are `vX.Y.0`, fix versions are `Version X.Y.0`. They are different strings — do not mix them in JQL.

## Which release a ticket belongs to — the rule

An empty `fixVersion` is not "unbound". Resolve it as follows:

1. **`fixVersion` set** → the ticket goes into **that** version, whatever its sprint says.
2. **`fixVersion` empty, sprint set** → the ticket goes into the version **matching the sprint number** (`v1.17.0` → `Version 1.17.0`).

Applied here: {{n of m land in X.Y}}; {{exceptions with the reason}}.

# Full inventory

{{One sentence on which sprint they share and what `(by sprint)` means.}}

| Key | Type | Epic | Status | Priority | fixVersion | → Release | Summary | My role | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

{{Reporters other than me: …}}

{{Epic ownership line: which other children the epic owns that are not in my inventory, and why they are absent — no sprint, someone else's, already closed.}}

# Companion notes

- {{[[note]] — one line on what it holds}}

# Notes on this inventory

- {{Where notes live and why, when the layout is not uniform.}}
- {{Anything that would be misread — e.g. bulk-edit timestamps that look like activity.}}
```
