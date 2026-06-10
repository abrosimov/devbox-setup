# Makefile

PLAYBOOK      := playbooks/main.yml
VAULT_OPTS    := --ask-vault-pass
# Sudo password is captured via `vars_prompt: ansible_become_password` in
# playbooks/main.yml so it can also be passed to homebrew_cask.sudo_password.
# Removing `-K` here avoids a redundant second prompt.
EXTRA_VARS    ?=
TEST_VAULT    := --vault-password-file tests/vault-password -e vault_file=../tests/vault.yml
PROFILE       ?=
PROFILE_OPTS  = $(if $(PROFILE),-e @profiles/$(PROFILE).yml)

# .devbox-profile stamp file at repo root — written by `make personal` /
# `make work` (post_tasks in playbooks/main.yml), gitignored, holds a single
# token: `personal` or `work`. Slim targets read it via STAMP_PROFILE so they
# can resolve the active profile without the user repeating PROFILE=... every
# time. Hybrid resolution: explicit PROFILE= overrides the stamp.
DEVBOX_STAMP   := .devbox-profile
STAMP_PROFILE  = $(shell test -f $(DEVBOX_STAMP) && head -n1 $(DEVBOX_STAMP) | tr -d '[:space:]' || true)
ACTIVE_PROFILE = $(or $(PROFILE),$(STAMP_PROFILE))
ACTIVE_OPTS    = $(if $(ACTIVE_PROFILE),-e @profiles/$(ACTIVE_PROFILE).yml)

define require_profile
	@if [ -z "$(ACTIVE_PROFILE)" ]; then \
		echo "ERROR: No active profile."; \
		echo "  Run 'make personal' or 'make work' once to stamp the profile,"; \
		echo "  or pass PROFILE=personal|work explicitly to this target."; \
		exit 1; \
	fi
endef

# Dev venv — lazy bootstrap for developer-mode targets (lint-*, typecheck-*,
# test-py). The operator-flow (init / personal / work / *-push / upgrade-*)
# does NOT depend on this venv and never touches it. See pyproject.toml for
# the rationale.
DEV_VENV     := .venv
DEV_BIN      := $(DEV_VENV)/bin
DEV_SENTINEL := $(DEV_VENV)/.devbox-installed

$(DEV_SENTINEL): pyproject.toml
	@command -v uv >/dev/null 2>&1 || { \
		echo "ERROR: uv is required for dev tooling. Install via 'brew install uv'."; \
		exit 1; \
	}
	@echo "Bootstrapping dev venv via 'uv sync --group dev'..."
	@uv sync --group dev --quiet
	@touch $@

# Claude Code config — single source of truth for the repo-side path. The
# managed-subdirs list lives in devbox_claude_managed_dirs (roles/devbox/defaults/main/claude.yml)
# and is read by both `make personal`/`make work` and `make claude-push`.
CLAUDE_SRC          := roles/devbox/files/dot_claude
CLAUDE_DEST         := $(HOME)/.claude
# Root files where source name == destination name. The User Authority Protocol
# is handled separately because it is renamed on deploy: USER_AUTHORITY_PROTOCOL.md
# in the repo -> CLAUDE.md in ~/.claude/ (the filename Claude Code expects).
# These are used by claude-diff / claude-pull only; claude-push delegates to
# Ansible (single source of truth for the managed-subdirs list).
CLAUDE_ROOT_FILES   := settings.json hooks.json config.md
CLAUDE_AUTHORITY_SRC  := USER_AUTHORITY_PROTOCOL.md
CLAUDE_AUTHORITY_DEST := CLAUDE.md
SKILLS_DIR          := $(CLAUDE_SRC)/skills

# Verbosity levels (V=1 → -v, V=2 → -vv, etc.)
ifeq ($(V),1)
  VERBOSE := -v
else ifeq ($(V),2)
  VERBOSE := -vv
else ifeq ($(V),3)
  VERBOSE := -vvv
else ifeq ($(V),4)
  VERBOSE := -vvvv
else
  VERBOSE :=
endif

.PHONY: run dev help init vault-init check check-dev validate-claude validate-skills eval-skills improve-skills \
       work personal dev-work dev-personal check-work check-personal \
       upgrade-work upgrade-personal \
       list-skills list-agents audit-budget \
       claude-diff claude-pull claude-pull-review claude-push \
       dotfiles-push shell-push mcp-sync local-push macos-defaults \
       test test-nvim test-fish test-json test-bash test-skill-evals test-py \
       lint lint-ansible lint-yaml lint-py typecheck-py dev-bootstrap

help:
	@echo ""
	@echo "Usage:"
	@echo "  make personal         - run with personal profile (AION_AUTOPOIESEON=~/Projects)"
	@echo "  make work             - run with work profile (AION_AUTOPOIESEON=~/Work)"
	@echo "  make dev-personal     - dev_mode + personal profile"
	@echo "  make dev-work         - dev_mode + work profile"
	@echo "  make check-personal   - dry-run with personal profile"
	@echo "  make check-work       - dry-run with work profile"
	@echo "  make check-dev        - dry-run in dev_mode (test vault)"
	@echo ""
	@echo "Developer-mode (auto-bootstraps .venv via uv on first run):"
	@echo "  make lint             - run all linters: yaml, py, ansible, type-check"
	@echo "  make lint-yaml        - yamllint only"
	@echo "  make lint-py          - ruff check + format check"
	@echo "  make lint-ansible     - ansible-playbook --syntax-check + ansible-lint"
	@echo "  make typecheck-py     - pyrefly type check"
	@echo "  make test-py          - pytest"
	@echo "  make dev-bootstrap    - materialise .venv only (sanity check)"
	@echo ""
	@echo "  make init             - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make vault-init       - create and encrypt vault/devbox_ssh_config.yml"
	@echo "  make upgrade-personal - upgrade all managed packages (personal profile)"
	@echo "  make upgrade-work     - upgrade all managed packages (work profile)"
	@echo "  make validate-claude  - validate Claude Code agent/skill library"
	@echo "  make audit-budget    - show detailed skill description budget report"
	@echo "  make validate-skills  - validate skill evals (structure, schema, coverage)"
	@echo "  make eval-skills      - run trigger evals via Anthropic's run_eval.py (slow, needs claude CLI)"
	@echo "  make improve-skills   - optimize skill description for trigger accuracy (run_loop.py)"
	@echo ""
	@echo "Maintenance (slim playbooks, no full bootstrap):"
	@echo "  make claude-push      - deploy Claude config (no sudo, no vault)"
	@echo "  make dotfiles-push    - deploy kitty / nvim / fish / bash configs + templates (no sudo, no vault)"
	@echo "  make shell-push       - refresh fish + fisher plugins + tide preset + font cache (no sudo)"
	@echo "  make mcp-sync         - re-register Claude Code MCP servers (no sudo)"
	@echo "  make local-push       - deploy gitignored local/ overlay (no sudo, no vault)"
	@echo "  make macos-defaults   - re-apply Touch ID / pmset / DevToolsSecurity (sudo required)"
	@echo ""
	@echo "Test / introspection:"
	@echo "  make test             - run all config validation tests"
	@echo "  make test-nvim        - headless smoke test of nvim config"
	@echo "  make test-fish        - fish shell config syntax check"
	@echo "  make test-json        - JSON config/schema validation"
	@echo "  make test-bash        - bash script syntax check"
	@echo "  make list-skills      - list all Claude Code skills"
	@echo "  make list-agents      - list all Claude Code agents"
	@echo "  make claude-diff      - show content drift between ~/.claude and repo"
	@echo "  make claude-pull-review - smart pull of settings.json (heuristic + interactive)"
	@echo "  make claude-pull      - wholesale copy of root files from ~/.claude to repo"
	@echo ""
	@echo "Options:"
	@echo "  V=1..4                - verbosity level (-v to -vvvv)"
	@echo "  SKILL=<name>          - target a single skill (for eval-skills, improve-skills)"
	@echo "  MODEL=<model-id>      - model for eval/improve (default: claude-opus-4-6)"
	@echo "  EXTRA_VARS='-e foo=bar' - pass extra variables"
	@echo ""

run: test
ifndef PROFILE
	$(error PROFILE is required. Use: make personal, make work, make dev-personal, or make dev-work)
endif
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook $(VERBOSE) $(VAULT_OPTS) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

dev:
	$(MAKE) run PROFILE=$(PROFILE) EXTRA_VARS='-e dev_mode=true' V=$(V)

work:
	$(MAKE) run PROFILE=work V=$(V)

personal:
	$(MAKE) run PROFILE=personal V=$(V)

dev-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e dev_mode=true' V=$(V)

dev-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e dev_mode=true' V=$(V)

# `lint` aggregates all dev-mode linters. Runs them in sequence so the first
# failure stops the rest (sequence chosen by cost: fast/cheap → slow).
lint: lint-yaml lint-py lint-ansible typecheck-py

dev-bootstrap: $(DEV_SENTINEL)
	@echo "Dev venv ready: $(DEV_VENV)"
	@$(DEV_BIN)/python --version

# ANSIBLE_VAULT_PASSWORD_FILE is a defence-in-depth alongside .ansible-lint's
# extra_vars override (see that file's comment block). The test password also
# decrypts the test vault stub if it ever has to be touched.
lint-ansible: $(DEV_SENTINEL)
	@$(DEV_BIN)/ansible-playbook --syntax-check $(TEST_VAULT) $(PLAYBOOK)
	@ANSIBLE_VAULT_PASSWORD_FILE=tests/vault-password $(DEV_BIN)/ansible-lint $(PLAYBOOK)

lint-yaml: $(DEV_SENTINEL)
	@$(DEV_BIN)/yamllint .

# `ruff check` is in advisory mode (--exit-zero) until the legacy Python debt in
# roles/devbox/files/dot_claude/bin/ is cleaned up — see
# roles/devbox/files/dot_claude/future_projects/ruff_strict_migration.md.
# The formatter is enforced strictly: it is deterministic and auto-fixable.
lint-py: $(DEV_SENTINEL)
	@$(DEV_BIN)/ruff check --exit-zero .
	@$(DEV_BIN)/ruff format --check .

typecheck-py: $(DEV_SENTINEL)
	@$(DEV_BIN)/pyrefly check

test-py: $(DEV_SENTINEL)
	@$(DEV_BIN)/pytest

check:
ifndef PROFILE
	$(error PROFILE is required. Use: make check-personal or make check-work)
endif
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(VAULT_OPTS) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

check-work:
	$(MAKE) check PROFILE=work V=$(V)

check-personal:
	$(MAKE) check PROFILE=personal V=$(V)

upgrade-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e devbox_upgrade_mode=true' V=$(V)

upgrade-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e devbox_upgrade_mode=true' V=$(V)

check-dev:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(TEST_VAULT) \
	    -e dev_mode=true -e ansible_become_password=dev-mode-placeholder $(PLAYBOOK)

init:
	@./scripts/init.sh

vault-init:
	@./scripts/vault-init.sh

list-skills:
	@ls -1 $(SKILLS_DIR) | sort | nl -ba

list-agents:
	@ls -1 $(CLAUDE_SRC)/agents/*.md 2>/dev/null | xargs -I{} basename {} .md | sort | nl -ba

validate-claude:
	@python3 $(CLAUDE_SRC)/bin/validate-config.py --root $(CLAUDE_SRC)

audit-budget:
	@python3 $(CLAUDE_SRC)/bin/validate-config.py --root $(CLAUDE_SRC) --budget

validate-skills:
	@echo "Validating skill eval files..."
	@python3 $(CLAUDE_SRC)/bin/validate-skill-evals

# Anthropic skill-creator scripts (installed via claude-plugins-official)
EVAL_SCRIPTS := $(shell ls -d ~/.claude/plugins/cache/anthropic-agent-skills/example-skills/*/skills/skill-creator/scripts 2>/dev/null | head -1)
SKILL        ?=
MODEL        ?= claude-opus-4-6
EVAL_WORKERS ?= 5

eval-skills:
ifndef EVAL_SCRIPTS
	$(error Anthropic skill-creator plugin not found. Install via: claude plugins install @anthropic/skill-creator)
endif
	@echo "Running trigger evals via Anthropic's run_eval.py..."
	@if [ -n "$(SKILL)" ]; then \
		skills="$(SKILLS_DIR)/$(SKILL)"; \
	else \
		skills=$$(find $(SKILLS_DIR) -name trigger_evals.json -exec dirname {} \; | xargs -I{} dirname {}); \
	fi; \
	pass=0; fail=0; skip=0; \
	for skill_dir in $$skills; do \
		name=$$(basename $$skill_dir); \
		trigger_file="$$skill_dir/evals/trigger_evals.json"; \
		if [ ! -f "$$trigger_file" ]; then \
			skip=$$((skip + 1)); \
			continue; \
		fi; \
		echo "  Testing $$name..."; \
		result=$$(PYTHONPATH=$(EVAL_SCRIPTS)/.. python3 -m scripts.run_eval \
			--eval-set "$$trigger_file" \
			--skill-path "$$skill_dir" \
			--num-workers $(EVAL_WORKERS) \
			--timeout 30 \
			--model $(MODEL) \
			--verbose 2>&1 1>/dev/null) || true; \
		echo "$$result" | sed 's/^/    /'; \
		if echo "$$result" | grep -q "failed: 0"; then \
			pass=$$((pass + 1)); \
		else \
			fail=$$((fail + 1)); \
		fi; \
	done; \
	echo ""; \
	echo "  $$pass passed, $$fail failed, $$skip skipped (no trigger_evals.json)"; \
	[ $$fail -eq 0 ]

improve-skills:
ifndef EVAL_SCRIPTS
	$(error Anthropic skill-creator plugin not found. Install via: claude plugins install @anthropic/skill-creator)
endif
ifndef SKILL
	$(error SKILL is required. Example: make improve-skills SKILL=lint-discipline)
endif
	@echo "Optimizing description for $(SKILL) via Anthropic's run_loop.py..."
	@skill_dir="$(SKILLS_DIR)/$(SKILL)"; \
	trigger_file="$$skill_dir/evals/trigger_evals.json"; \
	if [ ! -f "$$trigger_file" ]; then \
		echo "  ERROR: $$trigger_file not found"; exit 1; \
	fi; \
	PYTHONPATH=$(EVAL_SCRIPTS)/.. python3 -m scripts.run_loop \
		--skill-path "$$skill_dir" \
		--eval-set "$$trigger_file" \
		--model $(MODEL) \
		--verbose

claude-diff:
	@echo "=== Drift: deployed ~/.claude vs repo (root files only) ==="
	@drift=0; \
	if ! diff -q $(CLAUDE_SRC)/$(CLAUDE_AUTHORITY_SRC) $(CLAUDE_DEST)/$(CLAUDE_AUTHORITY_DEST) >/dev/null 2>&1; then \
		echo ""; \
		echo "--- $(CLAUDE_AUTHORITY_SRC) <-> $(CLAUDE_AUTHORITY_DEST) ---"; \
		diff -u $(CLAUDE_SRC)/$(CLAUDE_AUTHORITY_SRC) $(CLAUDE_DEST)/$(CLAUDE_AUTHORITY_DEST) || true; \
		drift=1; \
	fi; \
	for f in $(CLAUDE_ROOT_FILES); do \
		if ! diff -q $(CLAUDE_SRC)/$$f $(CLAUDE_DEST)/$$f >/dev/null 2>&1; then \
			echo ""; \
			echo "--- $$f ---"; \
			diff -u $(CLAUDE_SRC)/$$f $(CLAUDE_DEST)/$$f || true; \
			drift=1; \
		fi; \
	done; \
	if [ $$drift -eq 0 ]; then \
		echo "  No drift detected."; \
	else \
		echo ""; \
		echo "Smart pull (settings.json):   make claude-pull-review"; \
		echo "Dumb pull (all files):        make claude-pull"; \
	fi

claude-pull:
	@echo "=== Pulling root files from ~/.claude to repo (wholesale copy) ==="
	@if ! diff -q $(CLAUDE_SRC)/$(CLAUDE_AUTHORITY_SRC) $(CLAUDE_DEST)/$(CLAUDE_AUTHORITY_DEST) >/dev/null 2>&1; then \
		cp $(CLAUDE_DEST)/$(CLAUDE_AUTHORITY_DEST) $(CLAUDE_SRC)/$(CLAUDE_AUTHORITY_SRC); \
		echo "  PULLED: $(CLAUDE_AUTHORITY_DEST) -> $(CLAUDE_AUTHORITY_SRC)"; \
	else \
		echo "  SKIP:   $(CLAUDE_AUTHORITY_SRC) (no changes)"; \
	fi
	@for f in $(CLAUDE_ROOT_FILES); do \
		if ! diff -q $(CLAUDE_SRC)/$$f $(CLAUDE_DEST)/$$f >/dev/null 2>&1; then \
			cp $(CLAUDE_DEST)/$$f $(CLAUDE_SRC)/$$f; \
			echo "  PULLED: $$f"; \
		else \
			echo "  SKIP:   $$f (no changes)"; \
		fi; \
	done
	@echo "Review with: git diff"

claude-pull-review:
	@python3 scripts/claude-pull-review $(ARGS)

# Fast-path Claude config deploy via dedicated slim playbook.
# Reuses Block 1 + Block 2 of roles/devbox/tasks/install_configs.yml under the
# claude tag, so this and `make personal`/`make work` share a single implementation.
# No sudo prompt, no vault load.
#
# Slim targets resolve the active profile via the .devbox-profile stamp (or
# explicit PROFILE=...). This prevents accidental renders of profile-dependent
# vars (e.g. devbox_projects_dir) with the wrong value when invoked outside the
# main personal/work workflow.
claude-push:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags claude $(ACTIVE_OPTS) playbooks/claude.yml

# Fast-path: kitty / nvim / fish / bash configs + Jinja templates.
# Reuses Blocks 3-5 of roles/devbox/tasks/install_configs.yml under `dotfiles`.
dotfiles-push:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags dotfiles $(ACTIVE_OPTS) playbooks/dotfiles.yml

# Fast-path: fish + fisher plugins + tide preset + font cache.
# Reuses fish/tide/font-cache tasks in apply_configs.yml under `shell`.
# Replaces the old `fixfish` shell incantation. No sudo (slim playbook bypasses
# the defensive self-become via devbox_skip_become).
shell-push:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags shell $(ACTIVE_OPTS) playbooks/shell.yml

# Fast-path: re-register Claude Code MCP servers via `claude mcp add`.
# Reuses the MCP register tasks in apply_configs.yml under `mcp`. No sudo.
mcp-sync:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags mcp $(ACTIVE_OPTS) playbooks/mcp.yml

# Fast-path: gitignored local overlay (roles/devbox/local/).
# Reuses Block 6 of install_configs.yml under `local`.
local-push:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags local $(ACTIVE_OPTS) playbooks/local.yml

# Re-apply macOS basics: Touch ID for sudo, pmset disablesleep, DevToolsSecurity.
# Reuses configure_macos_basics.yml under `macos`. Sudo IS required.
macos-defaults:
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags macos $(ACTIVE_OPTS) playbooks/macos.yml

test: test-json test-fish test-bash test-nvim test-skill-evals test-py
	@echo "All tests passed."

test-json:
	@echo "Validating JSON files..."
	@fail=0; \
	for f in $$(find $(CLAUDE_SRC) -name '*.json' -not -path '*/local/*'); do \
		jq . "$$f" > /dev/null 2>&1 || { echo "  FAIL: $$f"; fail=1; }; \
	done; \
	[ $$fail -eq 0 ] && echo "  OK: all JSON files valid" || exit 1

test-fish:
	@echo "Validating fish config syntax..."
	@fail=0; \
	for f in $$(find roles/devbox/files/.config/fish -name '*.fish'); do \
		fish --no-execute "$$f" 2>&1 || { echo "  FAIL: $$f"; fail=1; }; \
	done; \
	[ $$fail -eq 0 ] && echo "  OK: all fish files valid" || exit 1

test-bash:
	@echo "Validating bash script syntax..."
	@fail=0; \
	for f in $$(find $(CLAUDE_SRC)/bin -type f); do \
		head -1 "$$f" | grep -q 'bash' || continue; \
		bash -n "$$f" 2>&1 || { echo "  FAIL: $$f"; fail=1; }; \
	done; \
	[ $$fail -eq 0 ] && echo "  OK: all bash scripts valid" || exit 1

test-nvim:
	@echo "Validating nvim config (headless)..."
	@ln -sfn $(CURDIR)/roles/devbox/files/.config/nvim /tmp/nvim-test
	@XDG_CONFIG_HOME=/tmp NVIM_APPNAME=nvim-test nvim --headless +"lua vim.defer_fn(function() vim.cmd('qa') end, 5000)" 2>&1 \
		&& echo "  OK: nvim config loaded without errors" \
		|| (echo "  FAIL: nvim config has errors"; exit 1)

test-skill-evals:
	@echo "Validating skill eval files..."
	@python3 $(CLAUDE_SRC)/bin/validate-skill-evals
