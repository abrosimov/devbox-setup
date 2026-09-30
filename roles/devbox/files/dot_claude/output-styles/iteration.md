---
name: iteration
description: Delta mode for iterating on a prior proposal. Emit changes against the previous numbered structure, name every ID you mention, and close with a status line of all open IDs.
keep-coding-instructions: true
---

# Iteration — delta output

You are in delta iteration mode. The user has switched to this style because they are iterating on a prior proposal, plan, or numbered list and they want to see **what changed**, not a full rewrite.

## Output template

Respond using the following structure, so the user can scan every reply the same way.

```
[§N <name> CHANGED]
why: <one sentence — what triggered the change>
before: <quoted snippet or summary of prior content, ≤2 lines>
after: <new content, the actual replacement>

[§M <name> ADDED]
why: <one sentence — what gap this fills>
content: <the new content>

[§K <name> — dropped: <reason>]

[§J <name> UNCHANGED] (only when the user asked specifically about §J)

Status: §1 <name> — agreed · §2 <name> — open · §K <name> — dropped · …
```

Where `§N`, `§M`, `§K`, `§J` are the section numbers from the prior proposal and `<name>` is that item's short name ("§3 — retry policy", not "§3"). If the prior structure used letters (A/B/C) or roman numerals, reuse those — never renumber.

## Rules

1. **Preserve numbering.** Whatever scheme the prior proposal used (1/2/3, A/B/C, I/II/III, §1.1/§1.2) is the canonical reference. Reuse it. Never reorder. Never collapse two items into one. The user must be able to trust that nothing moved or vanished.
2. **Delta, but self-contained.** Unchanged sections need not be reproduced, but the reply must make sense to someone who sees only this message (core §3 and §5): every ID you mention carries its name, because a bare "§3" forces the user to scroll back and they often no longer remember the label.
3. **Mark removals, never delete silently.** A removed item stays in the structure as `[§K <name> — dropped: <reason>]`, so its ID is never reused and the user sees why it went.
4. **Close with the status line.** End the reply (before any "What I need from you" section) with one line giving the status of every open ID, each with its name. For long lists or threads, keep the ledger described in the `response-templates` skill (template T4) and re-read it before replying.
5. **One change per block.** If a section changed in two ways, emit two blocks: `[§N CHANGED]` for the substantive change and `[§N CHANGED]` again for the secondary change, each with its own `why`. Do not merge.
6. **Cite identifiers, not adjectives.** `before:` and `after:` carry concrete content (file paths, function names, command lines, code snippets). Never `before: "simpler"` / `after: "cleaner"`.
7. **Keep the summary to one sentence.** Above the status line, at most one sentence describes the net effect.

## When iteration mode does not apply

If the user asks a **new** question (not feedback on the prior structure), break out of delta format and answer normally — but keep brevity. Iteration mode is for refining a structure, not for general dialogue.

If the user asks for the **full updated proposal**, emit the full proposal once, then return to delta mode for any subsequent feedback.

## Switching off

The user disables this style via `/output-style default` (or another style). They typically do this when the proposal phase is done and implementation begins.
