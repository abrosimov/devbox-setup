# Handoff template

Every stage file and every `vNN/HANDOFF.md` uses these five sections (A.15.10). Keep only what the
next performer needs to act: purpose, method, what is established, what is not, where the
material is, and the next operation. No transcript, no account of the session's attempts. A
handoff grants no authority: the receiver acts within its own contract and brief, and a missing
permission or access stays missing until its owner supplies it.

## Stage file

```markdown
---
aliases:
  - ADR-0NN vNN <stage>
---
# ADR-0NN vNN — <stage>

## 1. Purpose recovered
What this stage obtains for this version, and for whom.

## 2. Method used
Patterns applied (IDs), sources read (links below), commands run with where their output is.

## 3. Usable results
### Established
### Tentative
### Not done

## 4. Limits
What this file cannot support, and what would change it.

## 5. Next operation
The next stage, its input files, and anything it must check first.
```

## Version handoff (`vNN/HANDOFF.md`)

```markdown
---
aliases:
  - ADR-0NN vNN handoff
---
# ADR-0NN vNN — handoff

## 1. Purpose recovered
- Reviewed ADR: <title>, page <id>, page version <PP>, snapshot
  [[ADR-0NN Review/AI/sources/ADR-0NN-pPP|ADR-0NN source page PP (from vMM)]].
- This version answers [[ADR-0NN Review/AI/vNN/00-feedback|ADR-0NN feedback on vMM]].
- Class: early | late, because <reason from the goal>.
- Goal: [[ADR-0NN Review/AI/vNN/10-goal|ADR-0NN vNN goal]].

## 2. Method used
The stage order of the skill; deviations, if any, with the reason (for example, a stage performed
inline and therefore not independent).

## 3. Usable results
| Stage | State | File |
|---|---|---|
| Goal | done | [[ADR-0NN Review/AI/vNN/10-goal|ADR-0NN vNN goal]] |
| Explore | not needed / done / <topics> | … |
| Edit | done | [[ADR-0NN Review/AI/vNN/40-comment|ADR-0NN vNN comment]], [[ADR-0NN Review/AI/vNN/41-changes|ADR-0NN vNN changes]] |
| Review round N of <bound> | done / pending | [[ADR-0NN Review/AI/vNN/5N-review-rN|ADR-0NN vNN review rN]] |
| Accept | pending | |
| Checks | pending | |

Open findings: <finding, severity, file>. Decisions added this version: <names>.

## 4. Limits
Conditions that could have changed since this was written and must be re-checked on resuming:
ADR page version, new feedback, files edited by another session, links not re-opened.

## 5. Next operation
One operation, its agent, its input files. Anything waiting for the user, stated as what they do.

## Sessions
- <date>: <what this session established, one line>
```

## Links

Write every link as path plus alias: `[[ADR-0NN Review/AI/vNN/<file>|<alias>]]`, path without
`.md`. The path keeps the link unique where file names repeat; the alias is what the reader sees.
In a stage file a line reference is plain text after the link: `… comment]] line 58`.
