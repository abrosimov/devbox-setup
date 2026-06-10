# Prompt: Standardise per-project sandbox-writable scratch directory

Feed this to a planner-mode LLM to produce a full spec + enforcers for a
convention that contains tool caches/tmp/state inside each project tree (so
sandboxed sessions don't need to write outside it).

---

ROLE: You are a polyglot devops architect designing a per-project convention.

CONTEXT:
- I run ~50 projects under $PROJECTS_DIR (~/Projects or ~/Work) inside
  sandboxed Claude Code sessions.
- Many tools write outside the project tree by default: Go's GOCACHE/GOMODCACHE,
  pip/uv caches, npm/pnpm caches, Ansible ~/.ansible/tmp, pre-commit, ruff,
  mypy, pytest, hugo, terraform plugin cache, etc.
- The sandbox blocks writes outside the project tree + a few explicit allow
  paths, so every default-path tool either fails or requires per-command
  permission prompts which accumulate in .claude/settings.local.json.
- Today I work around it ad-hoc: env-var overrides in .claude/settings.json
  redirecting paths into project-local dirs (tmp/, .tmp/, .work/, debug/).
- I want a single convention I can apply across all projects and enforce
  programmatically.

PROPOSED CONVENTION (starting point — challenge if better exists):
- Single root: `var/` at project root.
- Subdirs by category: `var/cache/`, `var/tmp/`, `var/state/`, `var/log/`.
- Tool-specific leaves: e.g. `var/cache/go/`, `var/tmp/ansible/`.

DELIVERABLES (in this order, each in its own section):

1. CONVENTION REVIEW
   - Confirm or counter-propose the dir name + subdir layout.
   - Compare against ≥3 alternatives (`.work/`, `tmp/`, `.cache/`+`.tmp/`+`.state/`
     as separate roots). Decide one. State why.

2. ENV-VAR SCHEMA
   - Table: tool | env var | redirected path under the convention | source link.
   - Cover: Go (GOCACHE, GOMODCACHE, GOPATH), Python (UV_CACHE_DIR, PIP_CACHE_DIR,
     RUFF_CACHE_DIR, MYPY_CACHE_DIR, PYTEST_CACHE_DIR), Node (npm_config_cache,
     PNPM_HOME), Ansible (ANSIBLE_LOCAL_TEMP, ANSIBLE_REMOTE_TEMP, also config
     file directives), Rust (CARGO_HOME, CARGO_TARGET_DIR), Terraform/OpenTofu
     (TF_PLUGIN_CACHE_DIR), pre-commit (PRE_COMMIT_HOME), Hugo (HUGO_CACHEDIR).
   - For tools without env-var redirect, name the config file directive instead.

3. PROJECT FILES
   - `.gitignore` lines to add.
   - `.claude/settings.json` "env" block defining all the env vars.
   - Sandbox writable-paths additions if needed.

4. ENFORCEMENT — three tiers
   a. Manual: a short PROJECT README snippet documenting the convention.
   b. Validator: a bash script (`scripts/check-var-convention`) that exits
      non-zero if `var/` is missing, gitignore is missing the entry, or
      .claude/settings.json doesn't define the expected env vars. No
      dependencies beyond bash + jq.
   c. Scaffolder: an idempotent Ansible task (or `make scaffold-var` target)
      that creates the dirs, appends to .gitignore, and patches settings.json.

5. MIGRATION
   - One-screen runbook for retrofitting an existing project. Cover:
     detecting which existing dirs (tmp/, .tmp/, .work/, debug/) hold what,
     where to move them, what to update.

CONSTRAINTS:
- macOS + Linux only. No Windows quirks.
- No admin/root.
- No new tooling beyond ansible, make, bash, jq.
- Convention should not interfere with framework conventions that own a
  root-level dir name (e.g. Rust's `target/`, Node's `node_modules/`,
  Hugo's `public/`). Document conflicts and recommend resolutions.

STYLE: terse. Tables for any list of >3 items. No filler prose.
