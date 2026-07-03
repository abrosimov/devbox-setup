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

# Slim targets recover the active profile from MNEMOSYNE_PERISTASEOS — the env
# var that `make personal` / `make work` render into the user's shell rc (see
# devbox_shell.env in roles/devbox/defaults/main/shell.yml). Any fresh login
# shell after the first full run has it exported. Explicit PROFILE= wins if
# both are set. First-ever bootstrap: pass PROFILE=personal|work explicitly
# (or start a new shell so the just-rendered rc is sourced).
ACTIVE_PROFILE = $(or $(PROFILE),$(MNEMOSYNE_PERISTASEOS))
ACTIVE_OPTS    = $(if $(ACTIVE_PROFILE),-e @profiles/$(ACTIVE_PROFILE).yml)

define require_profile
	@if [ -z "$(ACTIVE_PROFILE)" ]; then \
		echo "ERROR: No active profile."; \
		echo "  MNEMOSYNE_PERISTASEOS is unset — start a new shell after the first"; \
		echo "  'make personal' / 'make work' run, or pass PROFILE=personal|work explicitly."; \
		exit 1; \
	fi
endef

# Dev venv — lazy bootstrap for developer-mode targets (lint-*, typecheck,
# test, test-integration, qa). The operator-flow (init / personal / work /
# *-push / upgrade-*) does NOT depend on this venv and never touches it.
# See pyproject.toml for the rationale.
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

# Ansible collections — lazy install + refresh on requirements.yml change.
# Sentinel lives next to the actual install ($HOME/.ansible/collections/) so
# wiping the install directory also wipes the sentinel and triggers reinstall.
# Required by ansible.posix.synchronize (Block 1 of install_configs.yml) and
# community.general.homebrew_cask.
COLLECTIONS_SENTINEL := $(HOME)/.ansible/collections/.devbox-collections-installed

$(COLLECTIONS_SENTINEL): requirements.yml
	@command -v ansible-galaxy >/dev/null 2>&1 || { \
		echo "ERROR: ansible-galaxy not found. Run 'make init' first."; \
		exit 1; \
	}
	@echo "Installing Ansible collections from requirements.yml..."
	@ansible-galaxy collection install -r requirements.yml
	@mkdir -p $(dir $@)
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

.PHONY: run dev help init vault-init check check-dev validate-claude validate-skills validate-configs eval-skills improve-skills \
       work personal dev-work dev-personal check-work check-personal \
       git-identity git-identity-ensure \
       upgrade-work upgrade-personal \
       list-skills list-agents audit-budget \
       audit audit-brew audit-brewfile audit-taps untap-stale \
       claude-diff claude-pull claude-pull-review claude-push \
       dotfiles-push shell-push mcp-sync local-push macos-defaults \
       sync-upstream-docs \
       test test-integration test-claude-hooks test-git-hooks test-nvim test-fish test-json test-bash \
       regenerate-fixtures \
       lint lint-ansible lint-yaml lint-py typecheck qa dev-bootstrap clean

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
	@echo "  make typecheck        - pyrefly type check"
	@echo "  make test             - pytest unit tests (excludes integration)"
	@echo "  make test-integration - pytest subprocess integration tests (slower)"
	@echo "  make test-claude-hooks - pytest under bin/'s own uv project (deployed-venv shape)"
	@echo "  make test-git-hooks   - pytest for the global git hooks (prepare-commit-msg)"
	@echo "  make qa               - lint + typecheck + test + test-integration (full gate)"
	@echo "  make dev-bootstrap    - materialise .venv only (sanity check)"
	@echo ""
	@echo "  make init             - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make vault-init       - create and encrypt vault/devbox_ssh_config.yml"
	@echo "  make upgrade-personal - upgrade all managed packages (personal profile)"
	@echo "  make upgrade-work     - upgrade all managed packages (work profile)"
	@echo "  make validate-claude  - validate Claude Code agent/skill library"
	@echo "  make audit-budget    - show detailed skill description budget report"
	@echo "  make audit           - run brew supply-chain audit: CVE scan (brew vulns) + brew audit --installed"
	@echo "  make audit-brewfile  - emit a Brewfile snapshot of devbox brew lists (stdout)"
	@echo "  make audit-taps      - report status of every tapped brew repo (declared / stale / stray)"
	@echo "  make untap-stale     - untap the curated stale-tap list (safe: nothing installed from them)"
	@echo "  make validate-skills  - validate skill evals (structure, schema, coverage)"
	@echo "  make eval-skills      - run trigger evals via Anthropic's run_eval.py (slow, needs claude CLI)"
	@echo "  make improve-skills   - optimize skill description for trigger accuracy (run_loop.py)"
	@echo ""
	@echo "Maintenance (slim playbooks, no full bootstrap):"
	@echo "  make claude-push      - deploy Claude config (no sudo, no vault)"
	@echo "  make dotfiles-push    - deploy kitty / nvim / fish / bash configs + templates + local/ overlay (no sudo, no vault)"
	@echo "  make shell-push       - refresh fish + fisher plugins + tide preset + font cache (no sudo)"
	@echo "  make mcp-sync         - re-register Claude Code MCP servers (no sudo)"
	@echo "  make local-push       - deploy only gitignored local/ overlay (surgical; already included in dotfiles-push)"
	@echo "  make macos-defaults   - re-apply Touch ID / pmset / DevToolsSecurity (sudo required)"
	@echo "  make sync-upstream-docs - pull fresh FPF-Spec.md from ailev/FPF@main and reset drift state"
	@echo ""
	@echo "Test / introspection:"
	@echo "  make validate-configs - run all repo-config validation (json + fish + nvim)"
	@echo "  make test-nvim        - headless smoke test of nvim config"
	@echo "  make test-fish        - fish shell config syntax check"
	@echo "  make test-bash        - bash script syntax check (bash -n)"
	@echo "  make test-json        - JSON config/schema validation"
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

run: test $(COLLECTIONS_SENTINEL)
ifndef PROFILE
	$(error PROFILE is required. Use: make personal, make work, make dev-personal, or make dev-work)
endif
	@ANSIBLE_FORCE_COLOR=1 ./scripts/with_sudo_keepalive.sh \
	    ansible-playbook $(VERBOSE) $(VAULT_OPTS) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

dev:
	$(MAKE) run PROFILE=$(PROFILE) EXTRA_VARS='-e dev_mode=true' V=$(V)

# git-identity — generate a per-profile git identity (user.name/email/signing key)
# into the gitignored local overlay and apply it to ~/.config/git/ immediately.
# Standalone: `make git-identity` (uses the active profile). It is also a
# prerequisite of personal/work via git-identity-ensure, which only generates
# when the identity is missing (idempotent — no prompt on later runs).
git-identity:
	@./scripts/git-identity-gen.sh $(or $(ACTIVE_PROFILE),$(error PROFILE is required: make git-identity PROFILE=personal|work))

git-identity-ensure:
	@test -f roles/devbox/local/.config/git/identity-$(PROFILE).gitconfig \
	    || ./scripts/git-identity-gen.sh $(PROFILE)

work: PROFILE = work
work: git-identity-ensure
	$(MAKE) run PROFILE=work V=$(V)

personal: PROFILE = personal
personal: git-identity-ensure
	$(MAKE) run PROFILE=personal V=$(V)

dev-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e dev_mode=true' V=$(V)

dev-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e dev_mode=true' V=$(V)

# `lint` aggregates all dev-mode linters. Runs them in sequence so the first
# failure stops the rest (sequence chosen by cost: fast/cheap → slow).
lint: lint-yaml lint-py lint-ansible typecheck

dev-bootstrap: $(DEV_SENTINEL)
	@echo "Dev venv ready: $(DEV_VENV)"
	@$(DEV_BIN)/python --version

# ANSIBLE_VAULT_PASSWORD_FILE is a defence-in-depth alongside .ansible-lint's
# extra_vars override (see that file's comment block). The test password also
# decrypts the test vault stub if it ever has to be touched.
lint-ansible: $(DEV_SENTINEL) $(COLLECTIONS_SENTINEL)
	@$(DEV_BIN)/ansible-playbook --syntax-check $(TEST_VAULT) $(PLAYBOOK)
	@ANSIBLE_VAULT_PASSWORD_FILE=tests/vault-password $(DEV_BIN)/ansible-lint $(PLAYBOOK)

lint-yaml: $(DEV_SENTINEL)
	@$(DEV_BIN)/yamllint .

# `ruff check` is in advisory mode (--exit-zero) until the legacy Python debt in
# roles/devbox/files/dot_claude/bin/ is cleaned up — see
# roles/devbox/files/dot_claude/future_projects/ruff_strict_migration.md.
# The formatter is enforced strictly: it is deterministic and auto-fixable.
#
# Scope: roles/devbox/files/dot_claude/ — covers bin/ (hook scripts, shared lib)
# and skills/*/scripts/ (skill-bundled utilities). Other Python files in the repo
# (.config/kitty/) are not project code; pyrefly's project-includes handles those.
lint-py: $(DEV_SENTINEL)
	@$(DEV_BIN)/ruff check --exit-zero roles/devbox/files/dot_claude/
	@$(DEV_BIN)/ruff format --check roles/devbox/files/dot_claude/

typecheck: $(DEV_SENTINEL) ## Pyrefly type check across dot_claude/bin/
	@$(DEV_BIN)/pyrefly check roles/devbox/files/dot_claude/bin/

test: $(DEV_SENTINEL) ## Pytest unit tests in dot_claude/ (excludes integration — see test-integration)
	@$(DEV_BIN)/pytest roles/devbox/files/dot_claude/ -m "not integration"

test-integration: $(DEV_SENTINEL) ## Pytest subprocess integration tests (smoke + hypothesis)
	@$(DEV_BIN)/pytest roles/devbox/files/dot_claude/bin/test_integration/ -m integration -v

test-git-hooks: $(DEV_SENTINEL) ## Pytest for the global git hooks (prepare-commit-msg)
	@$(DEV_BIN)/pytest tests/git_hooks -q

# Isolated check against the deployed-shape venv: same uv sync --frozen that
# Ansible runs in production, then pytest from bin/'s own dev group. Catches
# drift between bin/uv.lock and the test suite (e.g. bashlex version skew)
# that `make test` would miss because it uses the root dev venv.
test-claude-hooks: ## Pytest under bin/'s own uv project (mirrors deployed venv)
	@uv sync --project roles/devbox/files/dot_claude/bin --quiet
	@uv run --project roles/devbox/files/dot_claude/bin \
	  pytest roles/devbox/files/dot_claude/bin

qa: lint-py typecheck test test-integration ## Full Python quality gate (lint + typecheck + tests + integration)

regenerate-fixtures: $(DEV_SENTINEL) ## Re-extract recorded fixtures + regenerate synthetic ones
	@$(DEV_BIN)/python roles/devbox/files/dot_claude/bin/test_integration/extract_fixtures.py --max-per-bucket 50
	@$(DEV_BIN)/python roles/devbox/files/dot_claude/bin/test_integration/generate_fixtures.py --all --seed 42 --count 30

check: $(COLLECTIONS_SENTINEL)
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

check-dev: $(COLLECTIONS_SENTINEL)
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
	@python3 $(CLAUDE_SRC)/bin/validate_config.py --root $(CLAUDE_SRC)

audit-budget:
	@python3 $(CLAUDE_SRC)/bin/validate_config.py --root $(CLAUDE_SRC) --budget

# Supply-chain audit for Homebrew packages. Uses Homebrew/brew-vulns (an official
# subcommand that queries OSV.dev) for CVE scanning, and `brew audit --installed`
# for metadata health (broken URLs, deprecated deps, missing licences).
#
# `brew audit --installed` without --strict deliberately stays out of style-check
# territory: those checks are author-facing and produce noise for packages we
# don't maintain. We only want operator signal.
#
# `audit` runs against the live local install (everything currently in /opt/homebrew).
# `audit-brewfile` emits the static repo-defined package set as a Brewfile — used
# by .github/workflows/brew-audit.yml on a clean macos-latest runner.
PACKAGES_YML  := roles/devbox/defaults/main/packages.yml
PROFILE_YML   := profiles/$(or $(ACTIVE_PROFILE),personal).yml

audit: audit-brew

audit-brew:
	@echo "=== Ensuring brew-vulns is installed ==="
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "ERROR: brew not found in PATH."; exit 1; \
	fi
	@brew list --formula brew-vulns >/dev/null 2>&1 \
		|| brew install Homebrew/brew-vulns/brew-vulns
	@echo
	@echo "=== brew vulns (CVE scan via OSV) ==="
	@brew vulns --severity high || true
	@echo
	@echo "=== brew audit --installed (URLs / licences / deprecations) ==="
	@brew audit --installed --skip-style || true

audit-brewfile:
	@command -v yq >/dev/null 2>&1 || { \
		echo "ERROR: yq is required (brew install yq)."; exit 1; \
	}
	@printf '# Generated from %s + %s — do not edit.\n' "$(PACKAGES_YML)" "$(PROFILE_YML)"
	@for tap in $$(yq -r '.devbox_brew_taps[]' $(PACKAGES_YML)); do \
		printf 'tap "%s"\n' "$$tap"; \
	done
	@for f in $$(yq -r '.devbox_brew_primary[],.devbox_brew_primary_special[],.devbox_brew_secondary[]' $(PACKAGES_YML)); do \
		printf 'brew "%s"\n' "$$f"; \
	done
	@for f in $$(yq -r '.devbox_extra_brew[]? // empty' $(PROFILE_YML) 2>/dev/null); do \
		printf 'brew "%s"\n' "$$f"; \
	done
	@for c in $$(yq -r '.devbox_brew_primary_casks[],.devbox_brew_secondary_casks[],.devbox_brew_secondary_casks_no_binaries[]' $(PACKAGES_YML)); do \
		printf 'cask "%s"\n' "$$c"; \
	done
	@for c in $$(yq -r '.devbox_extra_brew_casks[]?,.devbox_extra_brew_casks_no_binaries[]?' $(PROFILE_YML) 2>/dev/null); do \
		printf 'cask "%s"\n' "$$c"; \
	done

# Curated list of third-party brew taps we want gone. Re-evaluated periodically
# via `make audit-taps`. Adding a tap here is a one-way intent: if it ever
# becomes needed again, declare it in roles/devbox/defaults/main/packages.yml
# (devbox_brew_taps) and remove from this list. Verified empty/unused as of
# 2026-06-20 — see git log for the audit that produced this list.
STALE_TAPS := \
  go-task/tap \
  homebrew/cask-fonts \
  hudochenkov/sshpass \
  jakehilborn/jakehilborn

audit-taps:
	@command -v yq >/dev/null 2>&1 || { \
		echo "ERROR: yq is required (brew install yq)."; exit 1; \
	}
	@declared=$$(yq -r '.devbox_brew_taps[]' $(PACKAGES_YML) | tr '[:upper:]' '[:lower:]'); \
	stale=$$(printf '%s\n' $(STALE_TAPS)); \
	printf "%-40s %-12s %s\n" "TAP" "DECLARED" "STATUS"; \
	printf "%-40s %-12s %s\n" "---" "--------" "------"; \
	brew tap | while read tap; do \
		lc=$$(printf '%s' "$$tap" | tr '[:upper:]' '[:lower:]'); \
		if printf '%s\n' "$$tap" | grep -qE '^homebrew/(core|cask)$$'; then \
			d="official"; s="-"; \
		elif printf '%s\n' "$$declared" | grep -qx "$$lc"; then \
			d="yes"; s="OK"; \
		elif printf '%s\n' "$$stale" | grep -qx "$$tap"; then \
			d="no"; s="STALE (run: make untap-stale)"; \
		else \
			d="no"; s="STRAY — declare in devbox_brew_taps or add to STALE_TAPS"; \
		fi; \
		printf "%-40s %-12s %s\n" "$$tap" "$$d" "$$s"; \
	done

untap-stale:
	@for tap in $(STALE_TAPS); do \
		if brew tap | grep -qx "$$tap"; then \
			echo "untap: $$tap"; \
			brew untap "$$tap" || true; \
		else \
			echo "skip:  $$tap (already untapped)"; \
		fi; \
	done

validate-skills:
	@echo "Validating skill eval files..."
	@python3 $(CLAUDE_SRC)/bin/validate_skill_evals.py

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
# Slim targets resolve the active profile via MNEMOSYNE_PERISTASEOS (or
# explicit PROFILE=...). This prevents accidental renders of profile-dependent
# vars (e.g. devbox_projects_dir) with the wrong value when invoked outside the
# main personal/work workflow.
claude-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags claude $(ACTIVE_OPTS) playbooks/claude.yml

# Fast-path: kitty / nvim / fish / bash configs + Jinja templates + local overlay.
# Reuses Blocks 3-5 (dotfiles) and Block 6 (local) of install_configs.yml.
# Use `make local-push` if you want to iterate on the overlay alone.
dotfiles-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags dotfiles,local $(ACTIVE_OPTS) playbooks/dotfiles.yml

# Fast-path: fish + fisher plugins + tide preset + font cache.
# Reuses fish/tide/font-cache tasks in apply_configs.yml under `shell`.
# Replaces the old `fixfish` shell incantation. No sudo (slim playbook bypasses
# the defensive self-become via devbox_skip_become).
shell-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags shell $(ACTIVE_OPTS) playbooks/shell.yml

# Fast-path: re-register Claude Code MCP servers via `claude mcp add`.
# Reuses the MCP register tasks in apply_configs.yml under `mcp`. No sudo.
mcp-sync: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags mcp $(ACTIVE_OPTS) playbooks/mcp.yml

# Fast-path: gitignored local overlay (roles/devbox/local/).
# Reuses Block 6 of install_configs.yml under `local`.
local-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags local $(ACTIVE_OPTS) playbooks/local.yml

# Re-apply macOS basics: Touch ID for sudo, pmset disablesleep, DevToolsSecurity.
# Reuses configure_macos_basics.yml under `macos`. Sudo IS required.
# Wrapped in with_sudo_keepalive.sh — see scripts/with_sudo_keepalive.sh for
# the rationale (pam_tid + ansible stdin race on Tahoe 26.x).
macos-defaults: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	@ANSIBLE_FORCE_COLOR=1 ./scripts/with_sudo_keepalive.sh \
	    ansible-playbook --tags macos $(ACTIVE_OPTS) playbooks/macos.yml

# Pull a fresh copy of the upstream FPF spec into dot_claude/docs/ and reset the
# drift state file used by the statusline / tide badge. Run when the badge (or
# curiosity) tells you the vendored copy lags upstream. Atomic: state file is
# only updated after curl succeeds.
FPF_LOCAL    := roles/devbox/files/dot_claude/docs/FPF-Spec.md
FPF_UPSTREAM := https://raw.githubusercontent.com/ailev/FPF/main/FPF-Spec.md
FPF_STATE    := $(if $(XDG_CACHE_HOME),$(XDG_CACHE_HOME),$(HOME)/.cache)/devbox-setup/fpf-drift

sync-upstream-docs:
	@tmp=$$(mktemp) && \
		curl -sfSL --max-time 15 $(FPF_UPSTREAM) -o $$tmp && \
		mv $$tmp $(FPF_LOCAL) && \
		mkdir -p $(dir $(FPF_STATE)) && \
		echo 0 > $(FPF_STATE) && \
		echo "Synced $(notdir $(FPF_LOCAL)) from upstream; drift state reset"

validate-configs: test-json test-fish test-nvim ## Validate repo configs (JSON, fish, nvim)
	@echo "All config validations passed."

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

# Bash syntax check via `bash -n`. Scope = live scripts only.
# Excludes future_projects/*/hooks-snapshots/ — those are frozen historical
# copies kept for reference, not executable code in the supported set.
test-bash:
	@echo "Validating bash script syntax..."
	@fail=0; \
	for f in $$(find scripts roles/devbox/files/dot_claude/templates roles/devbox/files/dot_claude/skills -name '*.sh' -not -path '*/future_projects/*' -not -path '*/hooks-snapshots/*'); do \
		bash -n "$$f" 2>&1 || { echo "  FAIL: $$f"; fail=1; }; \
	done; \
	[ $$fail -eq 0 ] && echo "  OK: all bash scripts have valid syntax" || exit 1

test-nvim:
	@echo "Validating nvim config (headless)..."
	@ln -sfn $(CURDIR)/roles/devbox/files/.config/nvim /tmp/nvim-test
	@XDG_CONFIG_HOME=/tmp NVIM_APPNAME=nvim-test nvim --headless +"lua vim.defer_fn(function() vim.cmd('qa') end, 5000)" 2>&1 \
		&& echo "  OK: nvim config loaded without errors" \
		|| (echo "  FAIL: nvim config has errors"; exit 1)

# Wipe the hermetic state directory (.devbox/ holds ansible local_tmp,
# dev_mode dotfiles target, and any other ephemeral runtime artefacts).
# Gitignored, fully owned by this repo — safe to recreate from scratch.
clean:
	@rm -rf $(CURDIR)/.devbox
	@echo "Cleaned: $(CURDIR)/.devbox"
