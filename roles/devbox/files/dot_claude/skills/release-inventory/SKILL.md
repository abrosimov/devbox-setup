---
name: release-inventory
description: >
  Sync a Jira release/sprint inventory into the Obsidian work vault — pull every issue
  where the user is assignee or reporter, lay epics, tasks and bugs out under
  `Projects/Releases/Release-X.Y/{Epics,Tasks,Bugs}/`, cross-link them, refresh the
  status fields of notes that already exist, and rebuild the release index table. Use
  when the user asks what is in a sprint or release, wants ticket statuses refreshed,
  asks to create notes for tickets, mentions Release-X.Y folders or the release
  inventory table, or runs `/release-sync`.
problem: "Sprint state is re-pulled from Jira by hand each time, notes drift out of sync with ticket fields, and the same content gets copied into both the release index and the per-ticket note."
related: [config, self-contained-options]
---

# Release inventory sync

Keeps `Projects/Releases/Release-X.Y/` in the work vault in step with Jira. Read-only against Jira — **never** transition an issue, edit a field, or post a comment.

**Vault root**: `~/Work/oiai-work-notes` (override if the user names another).
**Jira**: Atlassian MCP, cloudId `23ac9740-8e20-4ac2-a1c4-dc824fe66b78`, project `OICM`.
Load the tools with `ToolSearch`: `select:mcp__atlassian__searchJiraIssuesUsingJql,mcp__atlassian__getJiraIssue`.

Artefacts are British English. Chat replies follow the user's language.

## 1. Resolve the release argument

The user says "1.17". Three different strings derive from it and they are **not** interchangeable:

| Thing | Form | Example |
| --- | --- | --- |
| Sprint name | `vX.Y.0` | `v1.17.0` |
| Fix version name | `Version X.Y.0` | `Version 1.17.0` |
| Vault folder | `Release-X.Y` | `Release-1.17` |

Confirm the sprint and version strings exist before relying on them — board naming drifts. Probe with `project = OICM AND sprint IS NOT EMPTY AND assignee = currentUser() ORDER BY updated DESC` and read the sprint field off the result, rather than assuming.

## 2. Pull the inventory

```
project = OICM
  AND (assignee = currentUser() OR reporter = currentUser())
  AND (sprint = "vX.Y.0" OR fixVersion = "Version X.Y.0")
ORDER BY issuetype, priority DESC
```

Paginate with `nextPageToken` until `isLast`. Collect per issue: key, issuetype, status (name **and** category), resolution, priority, summary, assignee, reporter, created, updated, sprint(s), fixVersions, labels, components, parent, issue links.

For every Epic, additionally pull its children (`parent = KEY`) — **including children that are not the user's**. A sibling nobody told you about is exactly what goes missing.

## 3. Decide which release each ticket belongs to

1. **`fixVersion` set** → that version wins, whatever the sprint says.
2. **`fixVersion` empty, sprint set** → the version matching the sprint number.
3. **Neither set** → the ticket is unplaceable. List it separately; do not guess.

Record which branch fired — the note and the table must show `(explicit)` versus `(by sprint)`. A ticket placed by rule 2 is invisible to any `fixVersion = "Version X.Y.0"` query, so anyone cutting the release from that field will not see it. Say so once in the release note when rule 2 fired.

## 4. Index the vault before writing anything

```bash
python3 ~/.claude/skills/release-inventory/scripts/scan_vault.py --keys KEY1 KEY2 …
```

Returns, per key: `canonical` note path, `duplicates`, `companions`, front matter, and the ticket fields currently recorded in the note's Meta block. Plus `releases` (which `Release-X.Y` folders and buckets exist) and `problems`.

**The invariant this protects:** exactly one note per Jira key, anywhere in the vault. Obsidian resolves `[[OICM-8412]]` by filename; a second file with the same name makes every link to that key ambiguous.

So:

- Key **has** a canonical note → update it **in place**, wherever it lives. Never create a second note in `Release-X.Y/` because the layout would be tidier.
- Key **has no** note → create it under `Release-X.Y/{Epics,Tasks,Bugs}/` per the type.
- `problems` non-empty → report it and stop before writing. A duplicate key is a data-integrity fault, not something to work around.

Legacy notes under `Projects/Programming/{Epics,Tasks}/` are normal — they predate the release layout. Report the mismatch in the sync report so the user can decide, and **never move a file without being asked**.

## 5. Create missing notes

Templates: `references/note-templates.md`. Epics get a directory (`Release-X.Y/Epics/KEY/KEY.md`) because they accumulate companion notes; tasks and bugs are single files.

Create the bucket directory if absent. Fill every placeholder — never leave `{{…}}` in a written file. For a bug, quote the reporter's description verbatim when it is one or two sentences; their exact wording is often the only evidence of which endpoint they hit.

New notes get `## Root cause` → `*Pending — no investigation yet.*`. This skill does **not** investigate; root-cause work is a separate, explicitly-requested job.

## 6. Refresh notes that already exist

Update only the fields this skill owns:

- front matter `status` (glyph mapped from the Jira status **category** — see the templates)
- the Meta bullets: sprint, fixVersion, `→ release`, Jira status, priority, assignee, reporter, created/updated dates
- the `## Meta` Jira link if the key was somehow wrong

Leave everything else — objective, root cause, plan checkboxes, related information, hand-written callouts — untouched. Those are the user's.

**Report, do not silently absorb, these divergences:**

- The Jira **summary changed** since the note was written. Add a dated `> [!warning] State check YYYY-MM-DD` callout stating both wordings. A rewritten summary often means the ticket was re-scoped, and a re-scope can invalidate a root cause already recorded in the note.
- The note's recorded status disagrees with Jira.
- The ticket left the sprint, or its fixVersion moved.
- The ticket is closed but its note's plan still has unticked items.
- `updated` is recent but every field matches a batch of other issues' timestamps to the second — that is a bulk field edit, not activity. Say so; otherwise the freshness reads as progress.

## 7. Cross-link

- Epic note lists every child in its `## Children` table, with `Mine?` and each child's sprint. Flag any child whose sprint differs from the epic's, or which has none.
- Each child note names its parent epic in Meta and in `## Related information`.
- Every note links `[[Release X.Y]]`; the release note links back through the inventory table's `Note` column.
- Where two tickets are linked in Jira (duplicate, relates, blocks), mirror the link in `## Related information` with one line saying why it matters — not just the key.

## 8. Rebuild the release index

`Release X.Y.md` is an **index, not a digest**. It holds: `# Top` (hand-maintained — never rewrite or reorder), `# Meta` with the JQL and the §3 rule, `# Full inventory` table, `# Companion notes`, `# Notes on this inventory`.

**Do not** copy into it: root causes, evidence, `path:line` citations, plans, reviews, per-ticket findings. Those live in the ticket notes and the release note links to them. A status-count table, a per-release split table and a per-bug findings section are all restatements of columns already in the inventory table — leave them out.

Content that belongs to no ticket (a worktree sweep, a direction review) goes in its own note in the release folder and is listed under `# Companion notes`.

## 9. Report the diff

The value of a repeat run is the delta. Report in chat, not in the file:

- **Status changes** — `KEY: In Progress → Under review`
- **New in the inventory** since the last run, and what was created for them
- **Gone** — left the sprint, or fixVersion moved elsewhere
- **Divergences** from §6, each with the ticket key
- **Nothing changed** — say exactly that; do not manufacture a report

Then stop. Creating tickets, transitioning issues, running root-cause investigations and migrating legacy notes are all separate, explicitly-requested jobs.

## Do not

- Write to Jira in any form.
- Create a second note for a key that already has one.
- Move or delete an existing note without being asked.
- Overwrite `# Top` in the release note.
- Copy per-ticket findings into the release note.
- Invent a fixVersion for an unplaceable ticket.
