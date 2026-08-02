# Making live AI-engine configs stable — proposal (agent 10)

**Problem statement (as given):** `make claude-push` overwrites `~/.claude/settings.json`
with the repo copy. Changes made by Claude Code at runtime — or by the user in-session —
are lost unless `make claude-pull` is remembered first. Remembering is the only safeguard.

**Thesis:** the fix is not a better reminder. The fix is to stop treating `settings.json`
as a single-owner file. It has three classes of keys with three different rightful owners,
and the deploy path currently recognises none of them. This repo already contains a correct
implementation of ownership-aware reconciliation — for Codex — and two incorrect ones.
Converging on the correct one removes the class of bug entirely, after which drift
reminders become a nicety rather than the only defence.

---

## 1. Current state

### 1.1 Three divergent strategies for the same problem

| Engine | Deploy mechanism | Ownership model | Round-trip | Tests |
|---|---|---|---|---|
| **Claude** | `ansible.builtin.copy` verbatim (`roles/devbox/tasks/install_configs.yml:100-111`) | none — repo owns 100% of the file | manual `make claude-pull` / `claude-pull-review` | none |
| **Codex** | `reconcile_config.py --managed … --target …` (`install_codex_configs.yml:48-59`) | explicit: managed fragment owns its root scalars + whole tables; everything else preserved (`dot_codex/bin/reconcile_config.py:101-120`) | not needed — app keys survive by construction | `tests/deploy/test_reconcile_codex_config.py` |
| **Antigravity** | `merge_settings.py <managed> <target>` (`install_configs.yml:181-185`) | implicit: recursive deep-merge, managed always wins, lists unioned (`dot_agy/bin/merge_settings.py:6-14`) | none | none |

Codex is the mature design. Claude is the naive one. Antigravity is a third, weaker
variant written independently. Same problem, three answers, one repo.

### 1.2 The bug is live right now

Comparing repo vs deployed on this machine (`jq -S`, top-level keys only):

```
 "enabledPlugins": {
-  "document-skills@anthropic-agent-skills": false,      # repo
-  "example-skills@anthropic-agent-skills": false,
+  "document-skills@anthropic-agent-skills": true,       # live — toggled via /plugin
+  "example-skills@anthropic-agent-skills": true,
 }
+"extraKnownMarketplaces": { "anthropic-agent-skills": … }   # live only — /plugin marketplace add
+"model": "opus[1m]"                                          # live only — /model
```

`permissions` is currently identical. So the three things at risk today are exactly the
three things Claude Code itself writes: **model selection, marketplace registrations,
plugin enablement**. A `make claude-push` right now destroys all three, and neither
`make claude-pull` (wholesale copy — would drag them into the repo, which is also wrong)
nor `make claude-pull-review` (additive, `permissions.allow` only — `scripts/claude-pull-review:242-258`
explicitly reports other keys as *"not handled here"*) resolves them correctly.

### 1.3 Secondary defects found while surveying

1. **`make claude-diff` / `make claude-pull` are broken on the current tree.**
   `Makefile:71-79` still resolves the authority protocol under `CLAUDE_SRC`
   (`roles/devbox/files/dot_claude/USER_AUTHORITY_PROTOCOL.md`), but the file has moved to
   `dot_ai/` (git: `R dot_claude/USER_AUTHORITY_PROTOCOL.md -> dot_ai/USER_AUTHORITY_PROTOCOL.md`).
   `claude-diff` prints `No such file or directory`; `claude-pull` takes the "differs" branch
   and `cp`s the deployed `~/.claude/CLAUDE.md` back to the **deleted** path, resurrecting a
   stray file in the wrong directory. The `dot_ai` split silently orphaned these targets.

2. **`scripts/claude-pull-review` performs regex surgery on JSON source text.**
   `parse_allow_sections` (`:113-137`) and `rewrite_allow` (`:162-174`) rebuild the
   `permissions.allow` array literal from a `re.DOTALL` match, purely to preserve the
   hand-maintained blank-line grouping. 304 lines, zero tests — `tests/scripts/` holds only
   `test_apply_w2_frontmatter.py` and `test_git_identity_gen.py`. A malformed match writes a
   corrupt `settings.json` into the repo with no validation step (`:296-297` writes the text
   without re-parsing it as JSON — contrast `reconcile_config.py:119`, which re-parses the
   result before returning).

3. **`merge_settings.py` fails open and writes non-atomically.**
   An unparseable managed file exits `0` (`:28-31`) and Ansible reports success — a broken
   render is indistinguishable from a no-op. `merge()` unions lists (`:10-12`), so a value
   the repo *removes* stays on the host forever. `write_text` (`:43`) is not atomic; an
   interrupted deploy truncates the live settings file.

4. **Nothing gates the push.** `claude-push` (`Makefile:655-657`) depends only on
   `$(COLLECTIONS_SENTINEL)`. There is no drift check, no backup, no confirmation. Meanwhile
   the repo already uses prerequisite-gating idiomatically elsewhere — `secrets-ready` on
   `run`/`check`/`macos-defaults`, `git-identity-ensure` on `personal`/`work`.

5. **Undocumented.** `README.md` never mentions `claude-diff` / `claude-pull` /
   `claude-pull-review`. Only `CLAUDE.md` does, in one line.

### 1.4 Root cause

Ownership of each key is **undeclared**. The system offers only two verbs — *push* (repo
owns everything) and *pull* (host owns everything) — for a file where the truth is
per-key. Because neither verb is ever right, the user is asked to interleave them by hand,
and human memory is the integrity mechanism.

---

## 2. Proposals

Ordered by value-per-unit-work. P1 alone eliminates the reported problem; P2-P6 harden it.

### P1 — Declare ownership; generalise the Codex reconciler to JSON *(core)*

Introduce three ownership classes:

| Class | Semantics | On push |
|---|---|---|
| `repo` | policy — the repo is the sole author | overwrite, discard host value |
| `host` | runtime state — the app is the sole author | **read live value, preserve verbatim, never enter the repo** |
| `accrete` | curated baseline that the app appends to | write repo baseline; capture host-only additions to a quarantine file for later review |

Proposed classification for `~/.claude/settings.json`:

| Key | Runtime writer | Class |
|---|---|---|
| `permissions.deny` / `.ask` / `.additionalDirectories` | none | `repo` |
| `permissions.allow` | Claude — "Always allow" | `accrete` |
| `env` | none | `repo` |
| `sandbox` | `/sandbox` toggles (see `Makefile:80-84`) | `repo` — see open question Q1 |
| `statusLine` | `/statusline` | `repo` |
| `autoMemoryEnabled`, `skipAutoPermissionPrompt` | `/config` | `repo` |
| `model` | `/model` | `host` |
| `extraKnownMarketplaces` | `/plugin marketplace add` | `host` |
| `enabledPlugins` | `/plugin` | `accrete` — see Q2 |

JSON has no comment syntax, so the marker-block trick that `reconcile_config.py` uses for
TOML (`ROOT_BEGIN`/`TABLES_BEGIN`, `:18-21`) does not transfer. Ownership must live in a
sidecar manifest — which is the point: an explicit, reviewable, testable artefact.

**Deliverable:** `roles/devbox/files/dot_ai/bin/reconcile_json.py`, modelled on
`reconcile_config.py`, with:
- `--managed <file> --target <file> --ownership <manifest>`
- dotted-path key selectors (`permissions.allow`, `enabledPlugins`)
- `--check` mode returning `changed` / `unchanged` for `changed_when` (mirrors `:156-164`)
- atomic write via `mkstemp` + `replace` and re-parse of the result before commit
  (`:119`, `:123-137`)
- **fail closed**: any parse error is a non-zero exit, not a silent `exit 0`

**Deliverable:** `roles/devbox/files/dot_claude/settings.ownership.json` (or
`devbox_claude_settings_ownership` in `defaults/main/claude.yml` — see Q4).

**Wiring:** replace the `copy:` at `install_configs.yml:100-111` for `settings.json` with a
reconcile task under the same `[configs, claude]` tags. `hooks.json` and `config.md` stay a
plain copy — the app does not write them.

Effect: `model`, `extraKnownMarketplaces` and plugin toggles survive every push, without
the user doing anything. **The reported problem disappears at this step.**

### P2 — Source `permissions.allow` from YAML; render `settings.json`

The regex surgery in `claude-pull-review` exists solely because the grouping metadata of
`permissions.allow` is encoded in *blank lines inside a JSON file* — the one place JSON
cannot represent it.

Move `permissions.allow` into `roles/devbox/defaults/main/claude.yml` as a commented,
grouped YAML list, and render `settings.json` from a `.j2` template. Then:

- grouping and rationale become native YAML comments — no whitespace parsing;
- absorbing an "Always allow" entry becomes *appending to a YAML list*, a structural edit;
- `claude-pull-review` keeps its genuinely valuable part — the `KEEP_PATTERNS` /
  `DROP_PATTERNS` / `HYPER_SPECIFIC_MARKERS` classifier (`:31-76`) and the interactive
  review loop — and loses `parse_allow_sections` / `rewrite_allow` / `pick_section` entirely
  (~90 lines of the riskiest code in the repo).

Precedent exists in-repo on both sides: `dot_agy/cli/settings.json.j2` already renders
Antigravity settings from a template, and `install_configs.yml` Block 5 already renders six
`.j2` files. The checked-in `dot_claude/settings.json` would become a build artefact and
should be dropped from VCS.

### P3 — Make loss recoverable and make the push refuse to be silent

Even with P1, `accrete`-class additions can still be judged away. Two cheap guards:

1. **Pre-write snapshot.** The reconciler copies the live file to
   `~/.claude/.settings-history/<UTC-timestamp>.json` before writing, retaining the last
   ~20. Cost: a few kB. Benefit: every past mistake becomes recoverable, including ones
   made before this proposal is implemented.
2. **`claude-guard` prerequisite.** `claude-push: claude-guard` where `claude-guard` runs
   the reconciler with `--check` and fails when unabsorbed `accrete` drift exists, printing
   the entries and the two resolutions (`make claude-pull-review`, or `FORCE=1`). Follows
   the existing `secrets-ready` / `git-identity-ensure` prerequisite idiom.

Note the asymmetry: with P1, `host` keys need no guard — they are safe by construction. The
guard covers only the class where human judgement is genuinely required.

### P4 — Passive drift visibility

`roles/devbox/files/.config/fish/functions/_tide_item_fpf_drift.fish` is an existing,
working pattern: background refresh, cache file under
`$XDG_CACHE_HOME/devbox-setup/`, badge rendered only when the count is non-zero, prompt
never blocked. Clone it as `_tide_item_claude_drift.fish` reading a
`claude-drift` state file written by a `--check` run.

This is deliberately ranked below P1-P3: a badge that reminds you to pull is a fallback for
a system that can still lose data. After P1 it is an ergonomics win, not a safety measure.

### P5 — Tests and a CI classification check

- `tests/deploy/test_reconcile_json_config.py`, mirroring
  `tests/deploy/test_reconcile_codex_config.py`. Table cases: host key preserved; repo key
  overwritten; accrete key unioned; unparseable target; unparseable managed; atomicity;
  idempotence (second run reports `unchanged`).
- `tests/scripts/test_claude_pull_review.py` — the classifier (`classify`, `is_subsumed`)
  is pure and trivially testable; it has no coverage today.
- **CI gate on unclassified keys.** Extend `make validate-configs` to fail when a key
  present in the repo settings (or in the live file on a developer run) has no entry in the
  ownership manifest. This is the load-bearing check: when a future Claude Code release
  introduces a new runtime-written key, the build fails loudly instead of the key silently
  falling into whichever class the default happens to be.

### P6 — Retire `merge_settings.py`; unify all three engines

Point the Antigravity task (`install_configs.yml:181-185`) at `reconcile_json.py` with its
own ownership manifest and delete `dot_agy/bin/merge_settings.py`. Optionally re-express
`reconcile_config.py` as the TOML backend of the same tool. One reconciler, one test suite,
one mental model across Claude / Codex / Antigravity — and any future engine gets it free.

### P0 — Fix the orphaned path first *(trivial, do immediately)*

`Makefile:71-79`: repoint `CLAUDE_AUTHORITY_SRC` at `$(AI_SRC)` so `claude-diff` stops
erroring and `claude-pull` stops resurrecting a deleted file. Independent of everything
above; a two-line change.

---

## 3. Suggested sequencing

| Step | Work | Outcome |
|---|---|---|
| 0 | P0 — Makefile path fix | `claude-diff` works again |
| 1 | P1 — manifest + `reconcile_json.py` + tests | **reported bug eliminated** |
| 2 | P1 wiring + P6 — swap Claude and Antigravity onto the reconciler | one strategy, not three |
| 3 | P3 — snapshot + `claude-guard` | losses recoverable, pushes non-silent |
| 4 | P5 — CI unclassified-key gate | future-proofed against upstream key churn |
| 5 | P2 — YAML source + `.j2` render | ~90 lines of regex surgery deleted |
| 6 | P4 — tide badge | drift visible without asking |

Steps 0-2 are the minimum that closes the reported problem. Steps 3-6 are hardening and
can be deferred independently.

---

## 4. Open questions

- **Q1 — `sandbox` class.** `Makefile:80-84` records that `/sandbox` rewrites the file
  in-session. Is a `/sandbox` toggle an intentional policy change that should flow back to
  the repo (`accrete`), or a temporary local relaxation the next push should revert
  (`repo`)? The comment implies the latter; the behaviour implies churn.
- **Q2 — `enabledPlugins` class.** The two live flips (`document-skills`, `example-skills`
  false→true) look intentional. If the repo's `false` is a real policy, class is `repo` and
  the flips should be reverted; if it is stale, class is `accrete` or `host`.
- **Q3 — profile scope.** Should `host`-class values (notably `model`) ever differ
  deliberately between the `personal` and `work` profiles, or is per-machine divergence
  always incidental?
- **Q4 — manifest location.** Standalone `settings.ownership.json` (testable without
  Ansible, keeps the reconciler a plain CLI) versus `defaults/main/claude.yml` (follows the
  repo's variable-driven convention, `devbox_claude_managed_dirs` precedent). I lean
  standalone, with the *path* declared in `claude.yml`.
- **Q5 — does the repo keep a checked-in `settings.json` after P2?** Dropping it removes a
  redundant artefact but breaks any external consumer that reads it directly (e.g. the
  devcontainer bind-mount described in `CLAUDE.md` § Devcontainer Template).

---

## 5. Non-goals

- Project-level `.claude/settings.local.json` — machine-local by design, out of scope.
- `hooks.json`, `config.md` — the app does not write these; a plain copy remains correct.
- Managed subdirectories (`agents/`, `skills/`, …) — one-way `--delete` rsync is the right
  model there and is already documented as such (`CLAUDE.md` § Editing Claude Code Config).
- Karabiner — `karabiner-pull` (`Makefile`) already implements a correct projection-based
  round-trip for the portable subset; it is a fourth strategy, but a deliberate and
  well-suited one for a GUI-owned file.
