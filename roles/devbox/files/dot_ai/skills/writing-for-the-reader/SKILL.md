---
name: writing-for-the-reader
description: Writes every user-facing message so that someone who sees only that message can understand and act on it. Covers final reports, end-of-turn summaries, questions, option lists passed to the question tool, and explanations of technical artefacts such as texts, labels, tooltips, and config. Use when writing any final report, question, option list, or explanation of a technical artefact for the user.
version: 1
triggers:
  - final report
  - end of turn
  - summary
  - ask the user
  - question
  - options
  - choices
  - multiple choice
  - AskUserQuestion
  - request_user_input
alwaysApply: false
problem: "Final messages and questions lean on labels and context the reader no longer has, so the user cannot understand or answer them without scrolling back."
related: [agent-communication, response-templates, diverge-synthesize-select]
---

# Writing for the Reader

The user runs several threads at once and returns to this one later. The message they read may be
the only one on screen: earlier turns have scrolled away, the context may have been compacted, and
the labels you coined an hour ago mean nothing to them now. Write each message, above all the last
one of a turn, for a reader who sees only that message.

## Examples first

### 1. A question about a text shown to someone else

Bad:

> Keep the `Explanation.Formula` wording "the increase of X in each interval" or rewrite?

The user has to reconstruct who reads this string, where, and what it currently means to them.

Good:

> **Who reads it:** a dashboard user hovering over the "Requests" panel. `Explanation.Formula` is
> the tooltip text under the chart title.
>
> **What they see now:** "Requests: the increase of X in each interval". They do not know what X is
> or how long an interval is, so a bar of 1 200 could mean per second, per minute, or per day.
>
> **Option A — keep it:** same tooltip; the reader still guesses the unit.
> **Option B — "Requests received in each 5-minute bucket":** they read a bar of 1 200 as
> 1 200 requests in five minutes, about 4 per second.
> **Option C — "Requests per second, averaged over 5 minutes":** they read the value as a rate and
> can compare it with the 50 req/s alert threshold on the same dashboard.
>
> **Recommendation:** C, because the alert is expressed per second and the reader can compare the
> two numbers without arithmetic.

The question tool then offers only the three picks, each label naming the wording it would ship.

### 2. The end of a turn with several goals

Bad:

> Done with goal 1. Goal 2 is blocked — see above.

Good:

> Moved the nightly metrics dump from production to staging (goal 1): the cron entry in
> `deploy/cron.yaml`, which schedules the dump, now targets `staging-db`. Rotating the read-only
> database password (goal 2) is blocked: the vault path `secret/metrics/ro` is writable only by
> the platform team, so I could not update it.

Each goal is re-introduced by what it does, and each identifier carries a clause saying what it is.

### 3. An action the user has to take

Bad:

> You'll need to reseed the keychain before the next run.

Good:

> Your macOS login password changed, so the stored sudo password no longer works and the next
> playbook run will fail at the first privileged task. Run:
>
> ```
> make sudo-reseed
> ```
>
> It prompts once for the new password. Check it with `make check-personal`, which should reach the
> end without a sudo prompt.

The reader gets the reason, the exact command, and a way to confirm it worked.

## Rules for every message

- **Lead with the outcome.** The first sentence says what happened or what you found; the reader
  decides from it whether to read on.
- **Re-introduce earlier items by name.** "Goal 1 — move the metrics dump to staging", never a bare
  "goal 1": the number is your bookkeeping, the name is what the reader remembers.
- **Give every identifier a plain-language clause.** A file, flag, commit, key, or metric name is
  followed by what it is or does ("`pmset disablesleep`, which keeps the laptop awake with the lid
  shut"). The reader may not know the codebase as well as you do right now.
- **Do not invent labels without their meaning.** A shorthand you coined ("the fallback path",
  "plan B") is opaque to anyone who did not watch you coin it. Say what it is each time it appears
  in a new message.
- **Avoid pointers into history.** "As discussed", "see above", "the approach we mentioned", "same
  as before" all send the reader scrolling. Restate the content in a sentence instead.
- **Name the command for every user action.** An action without its command, or without a way to
  verify it, leaves the reader to rediscover what you already knew.

## Questions about texts and artefacts

When the question concerns something another person will read or use — UI copy, a tooltip, an error
message, a log line, a config value, an API field — answer these in the message body before asking:

1. **Who reads it**, and where they encounter it.
2. **What they see now**, rendered as they would see it, not as a code reference.
3. **What they would see under each option**, rendered the same way.
4. **What they would understand or do** in each case.
5. **Your recommendation**, with the reason.

Show, then ask. Previews, rendered examples, and context belong in the message body, where they stay
readable; the question tool (for example `AskUserQuestion` in Claude Code or `request_user_input`
in Codex) only collects the pick. Some engines render option previews poorly or not at all, so do
not rely on a preview field to carry substance.

## Option lists for the question tool

The user may answer long after the question was asked, so each option has to stand on its own.

- **Labels carry a concrete identifier** — a path, symbol, flag, command, or the literal wording
  that would ship: `Use rsync --delete`, `Extract parser to _lib/transcript.py`. "Option A",
  "Refactor cleanly", or "The recommended approach" name nothing.
- **An ID travels with its name.** `§3 sandbox cache` alone is a pointer the reader has to resolve;
  `§3 sandbox cache — move GOCACHE into $TMPDIR` is readable on its own.
- **Descriptions read standalone:** what the option does, in one sentence with identifiers; why it
  and not the others, in one sentence; where it applies, when that matters.
- **Options do not refer to each other.** "Like option 1 but for the secondary case" makes the
  reader hold two options at once; write out what the option does.
- If a description needs more than two or three lines, it is probably two options folded into one.

## Self-check before sending

1. If this were the only message the user saw today, could they understand and act on it?
2. Does every numbered or lettered item carry its name?
3. Does every identifier have a clause saying what it is?
4. For a question about a text: have I shown what the end reader sees under each option?
5. For every action I hand over: is the command there, and a way to verify it?
