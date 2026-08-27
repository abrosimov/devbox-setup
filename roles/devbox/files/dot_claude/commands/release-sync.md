---
description: Sync a Jira sprint/release inventory into the Obsidian vault — refresh statuses, create missing notes, rebuild the release index
argument-hint: "[release, e.g. 1.17]"
---

Sync release `$ARGUMENTS` from Jira into the work vault.

If `$ARGUMENTS` is empty, look at `~/Work/oiai-work-notes/Projects/Releases/` and use the highest `Release-X.Y` folder present; state which one you picked before doing anything.

Follow the `release-inventory` skill. In short:

1. Resolve the sprint name (`vX.Y.0`) and fix version name (`Version X.Y.0`) — confirm both exist in Jira rather than assuming.
2. Pull every issue where the user is assignee **or** reporter in that sprint or fix version, plus the children of every epic found.
3. Place each ticket in a release by the rule: explicit `fixVersion` wins; empty `fixVersion` + sprint → the version matching the sprint number; neither → unplaceable, list separately.
4. Run `scripts/scan_vault.py` first. One note per key, vault-wide — update in place if it exists, create under `Release-X.Y/{Epics,Tasks,Bugs}/` if it does not. Stop and report if the scan returns `problems`.
5. Refresh only the fields the skill owns. Never touch objectives, root causes, plan checkboxes or hand-written callouts.
6. Rebuild the `Release X.Y.md` inventory table. It is an index — no root causes, no evidence, no per-ticket digests.
7. Report the delta since the last run in chat. If nothing changed, say exactly that.

Read-only against Jira: no transitions, no field edits, no comments.

Do not run root-cause investigations, create tickets, or migrate legacy notes out of `Projects/Programming/` unless the user asks in this turn.
