---
name: self-contained-options
description: Make every AskUserQuestion option self-contained. Labels must include a concrete identifier (path, function, flag, command). Descriptions must restate context — never reference prior turns. Use when calling AskUserQuestion. Use every time.
version: 1
triggers:
  - AskUserQuestion
  - ask the user
  - options
  - choices
  - multiple choice
alwaysApply: false
---

# Self-Contained Options

When `AskUserQuestion` renders, the user sees labels and descriptions out of context. They may answer minutes or hours later, possibly after a tool-call result has scrolled prior reasoning off screen. Options that rely on prior-turn memory become unreadable. Every option MUST be a standalone artefact.

## The Three Rules

### Rule 1 — Labels must carry a concrete identifier

Every `label` MUST include at least one of:

- A file path or directory (`bin/maat.py`, `tests/`)
- A function, method, or symbol (`parse_frontmatter()`, `User.role`)
- A flag, env var, or config key (`--force`, `GOCACHE`, `output_config.format`)
- A literal command or code snippet (`mktemp -d $dir.XXXXXX`)
- A specific section/key from the prior assistant message (`§3 sandbox cache`)

If a label is pure noun-phrase ("Unique tmp + collision check"), it is **wrong**. Add the concrete identifier ("`mktemp -d $dir.converting.XXXXXX` + precheck").

### Rule 2 — Descriptions must restate enough context to read standalone

A `description` is read by someone who may not remember what was said two turns ago. It MUST contain:

1. **What the option does** in one sentence with concrete identifiers.
2. **Why this option** (the trade-off vs alternatives) in one sentence.
3. **Where it applies** (file, scope, condition) when relevant.

**Forbidden** phrases in descriptions: "as discussed", "the approach we mentioned", "the one I proposed", "the alternative". The user may not remember.

### Rule 3 — Do not rely on `preview`

The `preview` field is undocumented in Claude Code public docs and only loosely specified in Agent SDK docs (June 2026). Treat it as unstable. Put substantive content in `label` + `description`, not `preview`. Use `preview` only for genuine visual comparison (ASCII mock-ups, side-by-side code), never as a place to dump context the label was missing.

## Anti-Patterns

| Bad label | Why it fails | Better label |
|---|---|---|
| `Unique tmp + collision check` | No identifier; depends on prior reasoning | `mktemp -d $dir.XXXXXX + precheck` |
| `Option A` | Pure index; zero semantic content | `Use rsync --delete` |
| `The recommended approach` | Refers to prior context | `Add hook to PreCompact event` |
| `Refactor cleanly` | Adjective, no scope | `Extract parser to _claude_lib/transcript.py` |
| `Trap-based rollback` | Mechanism named, but missing where/what | `fish on-event fish_exit cleanup in proj convert` |

| Bad description | Why it fails |
|---|---|
| "The approach we discussed, with the safer rollback." | "we discussed" — opaque after a turn break |
| "Option 1 but applied to the secondary case." | No content; indirect reference |
| "Use the standard pattern." | "Standard" = undefined |
| "Same as before but cleaner." | Pure comparison; no concrete identifier |

## When this skill applies

Call this skill before every `AskUserQuestion` invocation:

- Drafting options to present a design choice
- Asking the user to pick among implementation alternatives
- Surfacing open questions during planning
- Confirming scope on a multi-file change

## Self-check before sending

For each option:

1. Could the user understand this option **without scrolling back** to my last few messages? If no, expand the label.
2. Does any option reference another option by name ("Like option 1 but…")? If yes, inline the content.
3. Does the description fit on 2–3 lines while still being self-contained? If not, the option is probably two options collapsed — split them.
4. If I removed the surrounding question text, would the options still be intelligible on their own? They MUST be.

## Why this rule matters

The user's answer happens in a different cognitive moment from the question. Hours may pass. The conversation may have compacted. Tool-call results may have buried the reasoning that motivated the label. Self-contained options respect that gap: the artefact carries its own context.
