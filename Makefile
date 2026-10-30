# Makefile

# Bare `make` prints the target list. Without this the default goal would be the
# first rule in the file — the dev-venv sentinel — so `make` would silently run
# `uv sync --group dev` instead of the help text.
.DEFAULT_GOAL := help

PLAYBOOK      := playbooks/main.yml
# Sudo password now comes from macOS login keychain slot `devbox-sudo` via
# `become_password_file = scripts/keychain-become-pass.sh` (see ansible.cfg
# [privilege_escalation]). Homebrew cask tasks read the same slot through the
# `devbox_sudo_password` var defined in roles/devbox/defaults/main/core.yml.
# The SSH passphrase (formerly in vault/) lives in slot `devbox-ssh-passphrase`.
# Both slots are seeded by scripts/ensure_secrets.sh (target `secrets-ready`),
# invoked automatically as a prereq of run/check/macos-defaults.
EXTRA_VARS    ?=
PROFILE       ?=
PROFILE_OPTS  = $(if $(PROFILE),-e @profiles/$(PROFILE).yml)

# A provisioning run always names its profile: `make personal` / `make work` pass
# it on the command line, and bare `make run` / `make check` refuse to guess (see
# the ifndef guards in those targets). There is deliberately no "currently active
# profile" notion above PROFILE — a real deploy is never decided by ambient state.
#
# The slim maintenance targets are the one exception, and only as a convenience:
# when no PROFILE is given they fall back to MNEMOSYNE_PERISTASEOS, the env var
# that the previous full run rendered into the shell rc (devbox_shell.env in
# roles/devbox/defaults/main/shell.yml). Explicit PROFILE= always wins. These two
# variables are scoped to that fallback — hence SLIM_, not ACTIVE_.
#
# This stays a separate variable rather than a target-specific default on PROFILE
# itself, because make offers no spelling of the latter that keeps both halves of
# the contract: `PROFILE ?=` in a target is a no-op once PROFILE is defined above
# (the fallback silently dies), and plain `PROFILE =` in a target overrides even a
# command-line PROFILE= (explicit silently loses). Verified both ways.
SLIM_PROFILE = $(or $(PROFILE),$(MNEMOSYNE_PERISTASEOS))
SLIM_OPTS    = $(if $(SLIM_PROFILE),-e @profiles/$(SLIM_PROFILE).yml)

define require_profile
	@if [ -z "$(SLIM_PROFILE)" ]; then \
		echo "ERROR: No profile given and none to fall back on."; \
		echo "  Pass PROFILE=personal|work explicitly, or start a new shell after the"; \
		echo "  first 'make personal' / 'make work' run, which exports"; \
		echo "  MNEMOSYNE_PERISTASEOS from the shell rc."; \
		exit 1; \
	fi
endef

# The post-run otelbox smoke is advisory, not a gate: `make personal` provisions
# thirteen steps and a dead collector must not block the other twelve. But a
# bare `|| true` made the failure invisible — it scrolled past under a few
# hundred lines of ansible output and the run still reported success. Keep the
# exit code zero, make the failure impossible to miss.
define otelbox_smoke_advisory
	@./scripts/otelbox-edge-test.py || { \
		echo ""; \
		echo "################################################################"; \
		echo "# ADVISORY: the otelbox edge smoke test FAILED."; \
		echo "#"; \
		echo "# Provisioning itself succeeded — every playbook step completed."; \
		echo "# What did not pass is the post-run liveness and delivery check,"; \
		echo "# so this machine is most likely not shipping telemetry."; \
		echo "#"; \
		echo "# Re-run the check alone:   make otelbox-edge-test"; \
		echo "# Set endpoint / token:     make otelbox-edge-config"; \
		echo "################################################################"; \
		echo ""; \
	}
endef

# Dev venv — lazy bootstrap for developer-mode targets (lint-*, typecheck,
# test, test-integration, qa). The operator-flow (init / personal / work /
# *-push / upgrade-*) does NOT depend on this venv and never touches it.
# See pyproject.toml for the rationale.
DEV_VENV     := .venv
DEV_BIN      := $(DEV_VENV)/bin
DEV_SENTINEL := $(DEV_VENV)/.devbox-installed
VALIDATE_PYTHON ?= $(if $(wildcard $(DEV_BIN)/python),$(DEV_BIN)/python,python3)

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

AI_CONFIG           := scripts/ai-config
CLAUDE_SRC          := roles/devbox/files/dot_claude
AI_SRC              := roles/devbox/files/dot_ai
CODEX_SRC           := roles/devbox/files/dot_codex
SKILLS_DIR          := $(AI_SRC)/skills

# Karabiner: the repo seeds the live file only when absent (Karabiner owns it at
# runtime — see install_configs.yml). karabiner-diff / karabiner-pull sync only the
# portable complex_modifications back to the repo, never the machine-local state
# (devices array, per-device "Modify events" toggles).
KARABINER_SRC       := roles/devbox/files/.config/karabiner/karabiner.json
KARABINER_DEST      := $(HOME)/.config/karabiner/karabiner.json
# jq projection of the comparable/portable part: the selected profile's
# complex_modifications (falls back to the first profile if none is selected).
KARABINER_CM_JQ     := (first(.profiles[]|select(.selected==true)) // .profiles[0]).complex_modifications

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

.PHONY: run help init check check-dev validate-claude validate-skills validate-configs eval-skills improve-skills rules-budget \
       work personal dev-work dev-personal check-work check-personal \
       git-identity git-identity-ensure \
       secrets-ready secrets-init sudo-reseed ssh-passphrase-reseed otelbox-edge-config otelbox-edge-test \
       langfuse-config \
       pub-preflight pub-e2e \
       upgrade-work upgrade-personal \
       list-skills list-agents audit-budget \
       audit audit-brewfile audit-brewfile-all audit-taps untap-stale \
       claude-diff claude-pull claude-pull-review \
       karabiner-diff karabiner-pull \
       dotfiles-push shell-push mcp-sync local-push macos-defaults drive-backup-push drive-backup-now go-proxy-verify \
       sync-upstream-docs \
       test test-integration test-ai-config test-deploy test-claude-hooks test-agy-hooks test-git-hooks test-scripts test-otelbox test-drive-backup test-nvim test-fish test-json test-bash \
       test-live test-live-guard test-langfuse-e2e \
       regenerate-fixtures \
       lint lint-ansible lint-ansible-semantics lint-yaml lint-py typecheck qa dev-bootstrap clean

help:
	@echo ""
	@echo "Usage:"
	@echo "  make personal         - run with personal profile (AION_AUTOPOIESEON=~/Projects)"
	@echo "  make work             - run with work profile (AION_AUTOPOIESEON=~/Work)"
	@echo "  make dev-personal     - dev_mode + personal profile"
	@echo "  make dev-work         - dev_mode + work profile"
	@echo "  make check-personal   - dry-run with personal profile"
	@echo "  make check-work       - dry-run with work profile"
	@echo "  make check-dev        - dry-run in dev_mode (profile from MNEMOSYNE_PERISTASEOS)"
	@echo "  make pub-preflight    - read-only WARP, Docker DNS and connectivity checks"
	@echo "  make pub-e2e          - live candidate pub on/off and restoration test"
	@echo ""
	@echo "Developer-mode (auto-bootstraps .venv via uv on first run):"
	@echo "  make lint             - run all linters: yaml, py, ansible, type-check"
	@echo "  make lint-yaml        - yamllint only"
	@echo "  make lint-py          - ruff check + format check"
	@echo "  make lint-ansible     - ansible-playbook --syntax-check + ansible-lint"
	@echo "  make lint-ansible-semantics - static catch for set_fact intra-task self-references"
	@echo "  make typecheck        - pyrefly type check"
	@echo "  make test             - pytest unit tests (excludes integration)"
	@echo "  make test-integration - pytest subprocess integration tests (slower)"
	@echo "  make test-ai-config   - pytest for the ai-config reconciler"
	@echo "  make test-deploy      - pytest for deployment structure"
	@echo "  make test-claude-hooks - pytest under bin/'s own uv project (deployed-venv shape)"
	@echo "  make test-agy-hooks   - pytest under dot_agy/bin's own uv project (deployed-venv shape)"
	@echo "  make test-git-hooks   - pytest for the global git hooks (prepare-commit-msg)"
	@echo "  make test-scripts     - pytest for scripts/ (git-identity-gen.py and friends)"
	@echo "  make test-otelbox     - pytest for the otelbox edge contract (wrapper, preflight, version pin)"
	@echo "  make test-live-guard  - pytest for the guards around test-live (hermetic)"
	@echo "  make test-live        - pytest against real claude/codex/agy binaries (opt-in, needs the CLIs)"
	@echo "                          ENGINES='claude,codex' turns a skip of those engines into a failure"
	@echo "  make test-drive-backup - drive-backup package: pytest, ruff, pyrefly, example config"
	@echo "  make qa               - lint + typecheck + unit, integration, ai-config, and deploy tests"
	@echo "  make dev-bootstrap    - materialise .venv only (sanity check)"
	@echo ""
	@echo "  make init             - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make secrets-init     - seed macOS keychain slots (devbox-sudo, devbox-ssh-passphrase)"
	@echo "  make sudo-reseed      - reseed only the devbox-sudo keychain slot (after login password rotation)"
	@echo "  make ssh-passphrase-reseed - reseed only the devbox-ssh-passphrase keychain slot"
	@echo "  make otelbox-edge-config - set otelbox edge remote endpoint (overlay) + ingestion token (keychain); ONLY=endpoint|token|cert"
	@echo "  make otelbox-edge-test - liveness smoke: binary, service, :13133, :8888, OTLP round-trip, delivery"
	@echo "  make langfuse-config  - seed or rotate the Langfuse API keys for the langfuse skill (keychain: devbox-langfuse)"
	@echo "  make drive-backup-push - (re)install the weekly drive backup (uv project + LaunchAgent) from the local overlay config"
	@echo "  make go-proxy-verify  - prove the Go module proxy client: go env contract, Tamias credential, public + private download"
	@echo "  make drive-backup-now  - run the drive backup now via launchd; log in ~/Library/Logs/drive-backup.log"
	@echo "  make upgrade-personal - upgrade all managed packages (personal profile)"
	@echo "  make upgrade-work     - upgrade all managed packages (work profile)"
	@echo "  make validate-claude  - validate Claude Code agent/skill library"
	@echo "  make audit-budget    - show detailed skill description budget report"
	@echo "  make rules-budget    - count rule-like statements across skills/agents/commands/UAP (ARGS='--json' or '--baseline PATH')"
	@echo "  make audit           - run brew supply-chain audit: CVE scan (brew vulns) + brew audit --installed"
	@echo "  make audit-brewfile  - emit a Brewfile snapshot for the active profile (stdout)"
	@echo "  make audit-brewfile-all - emit a Brewfile snapshot covering every profile (used by CI)"
	@echo "  make audit-taps      - report status of every tapped brew repo (declared / stale / stray)"
	@echo "  make untap-stale     - untap the curated stale-tap list (safe: nothing installed from them)"
	@echo "  make validate-skills  - validate skill evals (structure, schema, coverage)"
	@echo "  make eval-skills      - run trigger evals via Anthropic's run_eval.py (slow, needs claude CLI)"
	@echo "  make improve-skills   - optimize skill description for trigger accuracy (run_loop.py)"
	@echo ""
	@echo "Maintenance (slim playbooks, no full bootstrap):"
	@echo "  make dotfiles-push    - deploy kitty / nvim / fish / bash configs + templates + local/ overlay (no sudo, no vault)"
	@echo "  make shell-push       - refresh fish + fisher plugins + tide preset + font cache (no sudo)"
	@echo "  make mcp-sync         - re-register Claude Code MCP servers (no sudo)"
	@echo "  make local-push       - deploy only gitignored local/ overlay (surgical; already included in dotfiles-push)"
	@echo "  make macos-defaults   - re-apply Touch ID / pmset / DevToolsSecurity (sudo required)"
	@echo "  make sync-upstream-docs - sync the pinned FPF, Narrative and Engineering DPF bundle (ARGS=--check for preview)"
	@echo ""
	@echo "Test / introspection:"
	@echo "  make validate-configs - run all repo-config validation (json + fish + nvim)"
	@echo "  make test-nvim        - headless smoke test of nvim config"
	@echo "  make test-fish        - fish shell config syntax check"
	@echo "  make test-bash        - bash script syntax check (bash -n)"
	@echo "  make test-json        - JSON config/schema validation"
	@echo "  make list-skills      - list all Claude Code skills"
	@echo "  make list-agents      - list all Claude Code agents"
	@echo "  scripts/ai-config diff ENGINE --repo-root REPO --home HOME --profile personal|work"
	@echo "                         - inspect semantic repo/live drift (primary interface)"
	@echo "  scripts/ai-config apply ENGINE --repo-root REPO --home HOME --profile personal|work [--check]"
	@echo "                         - apply deterministic changes that require no decision"
	@echo "  scripts/ai-config reconcile ENGINE --repo-root REPO --home HOME --profile personal|work [--decisions FILE]"
	@echo "                         - reconcile explicit repo/live decisions (primary interface)"
	@echo "  scripts/ai-config bootstrap ENGINE --from-live [--write --preview-token TOKEN]"
	@echo "                         - preview or write the exact reviewed live-derived baseline"
	@echo "  make claude-diff      - compatibility alias for 'ai-config diff claude'"
	@echo "  make claude-pull-review - compatibility alias for 'ai-config reconcile claude'"
	@echo "  make claude-pull      - compatibility alias for claude-pull-review"
	@echo "  make karabiner-diff   - show drift of Karabiner complex_modifications (repo vs live)"
	@echo "  make karabiner-pull   - pull Karabiner complex_modifications from live into repo"
	@echo ""
	@echo "Options:"
	@echo "  V=1..4                - verbosity level (-v to -vvvv)"
	@echo "  SKILL=<name>          - target a single skill (for eval-skills, improve-skills)"
	@echo "  MODEL=<model-id>      - model for eval/improve (default: claude-opus-4-6)"
	@echo "  EXTRA_VARS='-e foo=bar' - pass extra variables"
	@echo ""

run: test $(COLLECTIONS_SENTINEL) secrets-ready
ifndef PROFILE
	$(error PROFILE is required. Use: make personal, make work, make dev-personal, or make dev-work)
endif
	@ANSIBLE_FORCE_COLOR=1 \
	 ANSIBLE_BECOME_PASSWORD_FILE="$(CURDIR)/scripts/keychain-become-pass.sh" \
	 ./scripts/with_sudo_keepalive.sh \
	    ansible-playbook $(VERBOSE) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

# secrets-ready is a prerequisite target that ensures both macOS keychain
# slots (devbox-sudo, devbox-ssh-passphrase) are seeded before any playbook
# run. First-time seed is interactive (prompts via `read -srp`); subsequent
# runs are silent no-ops. Non-Darwin: silent no-op.
secrets-ready:
	@./scripts/ensure_secrets.sh

# User-facing entrypoint for the interactive seed — same work as the
# secrets-ready prerequisite, named for the operator rather than for the
# dependency graph.
secrets-init: secrets-ready

sudo-reseed:
	@security delete-generic-password -a "$$USER" -s devbox-sudo >/dev/null 2>&1 || true
	@./scripts/ensure_secrets.sh --only sudo

ssh-passphrase-reseed:
	@security delete-generic-password -a "$$USER" -s devbox-ssh-passphrase >/dev/null 2>&1 || true
	@./scripts/ensure_secrets.sh --only ssh

# Interactive machine-local setup for the otelbox edge collector: remote gateway
# endpoint (gitignored local overlay) + Bearer ingestion token (login keychain).
# Pass ONLY='endpoint' or ONLY='token' to set just one.
#
# ONLY='cert' generates the optional client-certificate pair into the same
# gitignored overlay. It is not part of a bare run: most machines need no
# certificate, and regenerating one invalidates what the gateway front end
# already trusts.
otelbox-edge-config:
	@./scripts/otelbox-edge-config.py $(if $(ONLY),--only $(ONLY))

# Interactive seed (and rotation) of the Langfuse API keys the personal profile's
# langfuse Claude Code skill uses: login keychain service devbox-langfuse, accounts
# public-key / secret-key. `ai-config apply claude --profile personal` reads them.
langfuse-config:
	@./scripts/langfuse-config.py

# Liveness + delivery smoke for the otelbox edge collector — run after `make personal`.
otelbox-edge-test:
	@./scripts/otelbox-edge-test.py

# Pub mode (see README.md § Pub Mode). The interpreter is pinned to system
# python deliberately, not left to $(VALIDATE_PYTHON): pub-mode-test.py re-spawns
# its own live worker via /usr/bin/python3, and the LaunchDaemon under test runs
# the controller with the same one (devbox_pub_python_path).
pub-preflight:
	@/usr/bin/python3 scripts/pub-mode-test.py

pub-e2e:
	@/usr/bin/python3 scripts/pub-mode-test.py --live

# git-identity — generate a per-profile git identity (user.name/email/signing key)
# into the gitignored local overlay and apply it to ~/.config/git/ immediately.
# Standalone: `make git-identity` (uses the active profile). It is also a
# prerequisite of personal/work via git-identity-ensure, which only generates
# when the identity is missing (idempotent — no prompt on later runs).
git-identity:
	@./scripts/git-identity-gen.py $(or $(SLIM_PROFILE),$(error PROFILE is required: make git-identity PROFILE=personal|work))

git-identity-ensure:
	@test -f roles/devbox/local/.config/git/identity-$(PROFILE).gitconfig \
	    || ./scripts/git-identity-gen.py $(PROFILE)

work: PROFILE = work
work: git-identity-ensure
	$(MAKE) run PROFILE=work V=$(V)
	$(otelbox_smoke_advisory)

personal: PROFILE = personal
personal: git-identity-ensure
	$(MAKE) run PROFILE=personal V=$(V)
	$(otelbox_smoke_advisory)

dev-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e dev_mode=true' V=$(V)

dev-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e dev_mode=true' V=$(V)

# `lint` aggregates all dev-mode linters. Runs them in sequence so the first
# failure stops the rest (sequence chosen by cost: fast/cheap → slow).
lint: lint-yaml lint-py lint-ansible lint-ansible-semantics typecheck

dev-bootstrap: $(DEV_SENTINEL)
	@echo "Dev venv ready: $(DEV_VENV)"
	@$(DEV_BIN)/python --version

# No vault password needed — secrets migrated to macOS login keychain
# (see roles/devbox/defaults/main/core.yml + ansible.cfg become_password_file).
lint-ansible: $(DEV_SENTINEL) $(COLLECTIONS_SENTINEL)
	@$(DEV_BIN)/ansible-playbook --syntax-check $(PLAYBOOK)
	@$(DEV_BIN)/ansible-lint $(PLAYBOOK)

# Static catch for runtime-only Ansible footguns (currently: a set_fact key that
# references a sibling key in the same task — undefined at run time, invisible to
# yamllint/ansible-lint/--syntax-check).
lint-ansible-semantics: $(DEV_SENTINEL)
	@$(DEV_BIN)/python scripts/lint_ansible_semantics.py

lint-yaml: $(DEV_SENTINEL)
	@$(DEV_BIN)/yamllint .

# `ruff check` is enforced strictly (non-zero exit fails CI). The legacy Python
# debt that once forced advisory mode (--exit-zero) has been cleared — see
# roles/devbox/files/dot_claude/future_projects/ruff_strict_migration.md.
# The formatter is likewise enforced: it is deterministic and auto-fixable.
#
# Scope: the client/shared AI trees plus deploy and live tests. dot_agy is named as
# bin/ rather than as a whole tree because that is where all of its Python lives — the
# rest is TOML/Markdown config — matching the path `typecheck` already uses. Other
# Python files in the repo (.config/kitty/) are not project code; pyrefly's
# project-includes handles those.
#
# The three invocations below (ruff check, ruff format, pyrefly) used to spell
# their path lists out in full, which drifted: four paths that no longer existed
# sat in the pyrefly list unnoticed, because pyrefly skips a missing path
# without failing. One shared variable plus the per-tool delta instead.
PY_PATHS_COMMON := \
  roles/devbox/files/dot_agy/bin/ \
  roles/devbox/files/.local/bin/pub-lease.py \
  scripts/ai_config_cli.py scripts/ai_config/ \
  scripts/otelbox-edge-*.py scripts/otelbox_edge/ \
  scripts/codex-hook-trust.py scripts/codex_hook_trust/ \
  scripts/pub-mode-test.py \
  scripts/sync-upstream-docs.py \
  tests/live/ \
  tests/scripts/test_ai_config*.py \
  tests/scripts/test_otelbox_edge_*.py \
  tests/scripts/test_codex_hook_trust*.py \
  tests/scripts/test_pub_lease.py \
  tests/scripts/test_pub_mode_test.py \
  tests/scripts/test_sync_upstream_docs.py

# Lint takes the whole dot_claude / dot_ai / dot_codex trees and the deploy
# tests; typecheck takes only the bin/ subtrees, matching the dot_agy rule above.
PY_LINT_PATHS      := roles/devbox/files/dot_claude/ roles/devbox/files/dot_ai/ roles/devbox/files/dot_codex/ tests/deploy/ $(PY_PATHS_COMMON)
# dot_agy/bin is checked in its own pass: it is a diverged copy of dot_claude/bin with
# the same module names, so in a shared pass its tests resolve `import post_edit_lint`
# to the dot_claude module, whichever search-path entry comes first.
AGY_BIN_DIR        := roles/devbox/files/dot_agy/bin/
PY_TYPECHECK_PATHS := roles/devbox/files/dot_claude/bin/ roles/devbox/files/dot_codex/bin/ $(filter-out $(AGY_BIN_DIR),$(PY_PATHS_COMMON))

lint-py: $(DEV_SENTINEL)
	@bash -n scripts/ai-config
	@$(DEV_BIN)/ruff check $(PY_LINT_PATHS)
	@$(DEV_BIN)/ruff format --check $(PY_LINT_PATHS)

# Pyrefly ignores `project-excludes` from pyproject.toml whenever files are named
# explicitly on the command line, so the excludes have to be repeated as flags.
# bin/vendor/ holds verbatim upstream code (see bin/vendor/README.md) — it is not
# ours to annotate.
PYREFLY_EXCLUDES := --project-excludes '**/vendor/**' --project-excludes '**/.venv/**' --project-excludes '**/__pycache__/**'

typecheck: $(DEV_SENTINEL) ## Pyrefly type check across AI runtime scripts
	@$(DEV_BIN)/pyrefly check $(PY_TYPECHECK_PATHS) $(PYREFLY_EXCLUDES)
	@$(DEV_BIN)/pyrefly check $(AGY_BIN_DIR) --search-path $(AGY_BIN_DIR) $(PYREFLY_EXCLUDES)

# A prerequisite of `test` (and therefore of `run`): the otelbox edge contract is
# what a machine-local endpoint.env can silently break, and the failure mode is a
# collector that never deploys. Cheap enough (~2s) to gate every provisioning run.
test-otelbox: $(DEV_SENTINEL) ## Pytest for the otelbox edge collector contract
	@$(DEV_BIN)/pytest tests/deploy/test_otelbox_edge_deploy.py tests/scripts/test_otelbox_edge_*.py -q

test: $(DEV_SENTINEL) test-otelbox ## Pytest unit tests in dot_claude/ (excludes integration — see test-integration)
	@$(DEV_BIN)/pytest roles/devbox/files/dot_claude/ -m "not integration"

# The integration runner executes each hook the way the deployed `hooks` block
# does: through the venv beside the script. Without that venv it falls back to
# the script's own shebang, which needs the executable bit and an ambient
# interpreter carrying bashlex, and the CI test job has neither. Syncing the
# bin project first (the same `--frozen` sync the playbook's Block 1b runs)
# makes the target self-contained on a fresh checkout.
test-integration: $(DEV_SENTINEL) ## Pytest subprocess integration tests (smoke + hypothesis)
	@uv sync --project roles/devbox/files/dot_claude/bin --frozen --quiet
	@$(DEV_BIN)/pytest roles/devbox/files/dot_claude/bin/test_integration/ -m integration -v

test-ai-config: $(DEV_SENTINEL) ## Pytest for the ai-config reconciler
	@$(DEV_BIN)/pytest tests/scripts/test_ai_config*.py -q

test-git-hooks: $(DEV_SENTINEL) ## Pytest for the global git hooks (prepare-commit-msg)
	@$(DEV_BIN)/pytest tests/git_hooks -q

test-scripts: $(DEV_SENTINEL) ## Pytest for scripts/ (git-identity-gen.py and friends)
	@$(DEV_BIN)/pytest tests/scripts -q

test-deploy: $(DEV_SENTINEL) ## Pytest for dotfile-deploy structure (karabiner assets, hook interpreters, …)
	@$(DEV_BIN)/pytest tests/deploy -q

# packages/drive-backup is a standalone uv project (own uv.lock, Python 3.14,
# own ruff/pyrefly config) meant to be liftable into its own repository, so it is
# checked with its own toolchain rather than the root dev venv. The example config
# is validated with the same `check-config` the playbook runs against the real one.
DRIVE_BACKUP_PKG := packages/drive-backup
DRIVE_BACKUP_UV  := uv --directory $(DRIVE_BACKUP_PKG)
test-drive-backup: ## drive-backup package: pytest, ruff, pyrefly, example config
	@$(DRIVE_BACKUP_UV) sync --frozen --quiet
	@$(DRIVE_BACKUP_UV) run --frozen pytest -q
	@$(DRIVE_BACKUP_UV) run --frozen ruff check .
	@$(DRIVE_BACKUP_UV) run --frozen ruff format --check .
	@$(DRIVE_BACKUP_UV) run --frozen pyrefly check
	@AION_AUTOPOIESEON=/nonexistent/aion $(DRIVE_BACKUP_PKG)/.venv/bin/drive-backup \
	  --config roles/devbox/files/.config/drive-backup/config.toml.example check-config >/dev/null

# Isolated check against the deployed-shape venv: same uv sync --frozen that
# Ansible runs in production, then pytest from bin/'s own dev group. Catches
# drift between bin/uv.lock and the test suite (e.g. bashlex version skew)
# that `make test` would miss because it uses the root dev venv.
test-claude-hooks: ## Pytest under bin/'s own uv project (mirrors deployed venv)
	@uv sync --project roles/devbox/files/dot_claude/bin --frozen --quiet
	@uv run --project roles/devbox/files/dot_claude/bin \
	  pytest roles/devbox/files/dot_claude/bin

# Same isolation for the Antigravity hook tree, which carries its own uv project
# and its own `_agy_lib`. The two trees share an ancestry but not a venv, so a
# green `test-claude-hooks` says nothing about this one.
test-agy-hooks: ## Pytest under dot_agy/bin's own uv project (deployed-venv shape)
	@uv sync --project roles/devbox/files/dot_agy/bin --frozen --quiet
	@uv run --project roles/devbox/files/dot_agy/bin \
	  pytest roles/devbox/files/dot_agy/bin

# The guards around tests/live/ are the two things in that suite that must never
# silently stop working — the throwaway home, and the refusal to skip an engine
# CI declared — so they run hermetically with `qa` rather than only behind the
# opt-in `test-live` target. No file list: tests/live/conftest.py already hides
# the engine tests unless DEVBOX_LIVE_ENGINE_TESTS is set, so this collects
# exactly the hermetic ones and keeps collecting any that are added later.
test-live-guard: $(DEV_SENTINEL) ## Pytest for the throwaway-home and engine guards (hermetic)
	@$(DEV_BIN)/pytest tests/live -q

# Opt-in: spawns the installed claude / codex / agy binaries against a throwaway
# home and asserts each engine actually honours the configuration this repository
# generates for it. Needs the CLIs on PATH and a regular terminal, like
# `make eval-skills`. Missing binaries skip rather than fail; no engine here needs
# an account or a reachable API.
#
# ENGINES names the engines the caller installed on purpose — CI does — and turns
# every skip for one of them into a failure, so a runner whose install silently
# produced nothing cannot report green over nothing exercised.
test-live: $(DEV_SENTINEL) ## Pytest against real engine binaries (opt-in, needs claude/codex/agy)
	@DEVBOX_LIVE_ENGINE_TESTS=1 DEVBOX_LIVE_REQUIRE_ENGINES="$(ENGINES)" \
	  $(DEV_BIN)/pytest tests/live -m live -v

# Opt-in, Linux only: the Claude Langfuse handoff end to end — real Stop hook,
# the replay runner as its LaunchAgent plist starts it, and the pinned otelbox
# edge release (fetched and checked against its published .sha256) forwarding
# to a test-owned gateway. Skips when the edge cannot run here (macOS, busy edge
# ports, no download); ENGINES=otelbox-edge turns that skip into a failure.
test-langfuse-e2e: $(DEV_SENTINEL) ## Langfuse handoff against the pinned otelbox edge (opt-in, Linux)
	@DEVBOX_LIVE_ENGINE_TESTS=1 DEVBOX_LIVE_REQUIRE_ENGINES="$(ENGINES)" \
	  $(DEV_BIN)/pytest tests/live/test_live_langfuse_handoff.py -m live -v

qa: lint-py typecheck test test-integration test-ai-config test-scripts test-deploy test-live-guard ## Full Python quality gate

regenerate-fixtures: $(DEV_SENTINEL) ## Re-extract recorded fixtures + regenerate synthetic ones
	@$(DEV_BIN)/python roles/devbox/files/dot_claude/bin/test_integration/extract_fixtures.py --max-per-bucket 50
	@$(DEV_BIN)/python roles/devbox/files/dot_claude/bin/test_integration/generate_fixtures.py --all --seed 42 --count 30

check: $(COLLECTIONS_SENTINEL) secrets-ready
ifndef PROFILE
	$(error PROFILE is required. Use: make check-personal or make check-work)
endif
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

check-work:
	$(MAKE) check PROFILE=work V=$(V)

check-personal:
	$(MAKE) check PROFILE=personal V=$(V)

upgrade-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e devbox_upgrade_mode=true' V=$(V)

upgrade-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e devbox_upgrade_mode=true' V=$(V)

# Profile still has to resolve to something, even though dev mode already
# redirects every destination to ../debug/dotfiles and overrides both secrets:
# the Claude/agy settings-reconciliation tasks pass {{ devbox_active_profile }}
# straight through to `scripts/ai-config --profile`, which needs a real
# profiles/<name>.yml to look up. Recovering it from MNEMOSYNE_PERISTASEOS (the
# same mechanism as dotfiles-push/shell-push/mcp-sync) matches how this target
# is actually used — a quick dry-run during playbook iteration on a machine
# that has already run `make personal`/`make work` once — without forcing a
# profile pick on every invocation the way check-personal/check-work do.
check-dev: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(SLIM_OPTS) \
	    -e dev_mode=true \
	    -e devbox_sudo_password_override=dev-mode \
	    -e devbox_ssh_pass_phrase_override=dev-mode $(PLAYBOOK)

init:
	@./scripts/init.sh

list-skills:
	@ls -1 $(SKILLS_DIR) | sort | nl -ba

list-agents:
	@ls -1 $(AI_SRC)/agents/*.md 2>/dev/null | xargs -I{} basename {} .md | sort | nl -ba

validate-claude:
	@$(VALIDATE_PYTHON) $(CLAUDE_SRC)/bin/validate_config.py --root $(CLAUDE_SRC) --ai-root $(AI_SRC) --codex-root $(CODEX_SRC)

audit-budget:
	@$(VALIDATE_PYTHON) $(CLAUDE_SRC)/bin/validate_config.py --root $(CLAUDE_SRC) --ai-root $(AI_SRC) --budget

# Rules-budget instrumentation (RI1): count rule-like statements across
# skills, agents, commands, and UAP. Baseline for W2-W5 tuning decisions.
# ARGS lets callers pass through --json, --baseline PATH, etc.
rules-budget:
	@uv run --project $(CLAUDE_SRC)/bin \
	  python $(CLAUDE_SRC)/bin/rules_budget.py --root $(CLAUDE_SRC) --ai-root $(AI_SRC) $(ARGS)

# Supply-chain audit for Homebrew packages. Uses `brew vulns` (a built-in Homebrew
# command since it was merged from the now-archived Homebrew/brew-vulns tap; queries
# OSV.dev) for CVE scanning, and `brew audit --installed` for metadata health
# (broken URLs, deprecated deps, missing licences). The old tap-install step was
# removed: Homebrew deleted Homebrew/brew-vulns, so `brew install …/brew-vulns`
# fails and re-taps a dead repo.
#
# `brew audit --installed` without --strict deliberately stays out of style-check
# territory: those checks are author-facing and produce noise for packages we
# don't maintain. We only want operator signal.
#
# `audit` runs against the live local install (everything currently in /opt/homebrew).
# `audit-brewfile` emits the static repo-defined package set as a Brewfile for one
# profile; `audit-brewfile-all` emits the union over every profile and is what
# .github/workflows/brew-audit.yml runs on a clean macos-latest runner.
#
# The union matters: the CVE scan does not care which laptop installs what, it
# cares that nothing we can install goes unchecked. PROFILE_YML used to fall back
# to `personal` whenever no profile was set, which is exactly the case in CI — so
# the work profile's extras (oras, orbstack) had never been scanned at all. A
# silent default is the wrong answer where the report claims coverage, hence
# require_profile on the single-profile target.
PACKAGES_YML  := roles/devbox/defaults/main/packages.yml
PROFILE_YML    = profiles/$(SLIM_PROFILE).yml
PROFILE_YMLS  := $(wildcard profiles/*.yml)

audit:
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "ERROR: brew not found in PATH."; exit 1; \
	fi
	@echo "=== brew vulns (CVE scan via OSV) ==="
	@if brew vulns --help >/dev/null 2>&1; then \
		brew vulns --severity high || true; \
	else \
		echo "  (skipped: 'brew vulns' unavailable — built-in since the brew-vulns tap was archived; run 'brew update')"; \
	fi
	@echo
	@echo "=== brew audit --installed (URLs / licences / deprecations) ==="
	@brew audit --installed --skip-style || true

# $(1) = space-separated list of profile YAML files whose extras to fold in.
#
# One shell block so the whole thing can be piped through awk: with more than one
# profile the base lists would otherwise repeat, and `brew bundle`/`brew info`
# should not be handed the same package twice. `!seen[$$0]++` keeps first-occurrence
# order, so the output stays diffable.
#
# `.devbox_extra_brew[]?` deliberately carries no `// empty` fallback: that is a jq
# idiom, and mikefarah yq rejects it with a lexer error. The previous version had
# one, hidden behind `2>/dev/null`, so the extra-formula list was silently empty
# for every profile — `oras` had never reached the Brewfile even when the work
# profile was passed explicitly. `?` alone already tolerates a missing key.
define emit_brewfile
	@command -v yq >/dev/null 2>&1 || { \
		echo "ERROR: yq is required (brew install yq)."; exit 1; \
	}
	@{ \
		printf '# Generated from %s + %s — do not edit.\n' "$(PACKAGES_YML)" "$(strip $(1))"; \
		yq -r '.devbox_brew_taps[]' $(PACKAGES_YML) \
			| while read -r t; do printf 'tap "%s"\n' "$$t"; done; \
		yq -r '.devbox_brew_primary[],.devbox_brew_primary_special[],.devbox_brew_secondary[]' $(PACKAGES_YML) \
			| while read -r f; do printf 'brew "%s"\n' "$$f"; done; \
		for p in $(1); do \
			yq -r '.devbox_extra_brew[]?' "$$p" \
				| while read -r f; do printf 'brew "%s"\n' "$$f"; done; \
		done; \
		yq -r '.devbox_brew_primary_casks[],.devbox_brew_secondary_casks[],.devbox_brew_secondary_casks_no_binaries[]' $(PACKAGES_YML) \
			| while read -r c; do printf 'cask "%s"\n' "$$c"; done; \
		for p in $(1); do \
			yq -r '.devbox_extra_brew_casks[]?,.devbox_extra_brew_casks_no_binaries[]?' "$$p" \
				| while read -r c; do printf 'cask "%s"\n' "$$c"; done; \
		done; \
	} | awk '!seen[$$0]++'
endef

# One profile, named explicitly or recovered from the environment. No fallback:
# a Brewfile that silently describes the wrong machine is worse than an error.
audit-brewfile:
	$(require_profile)
	$(call emit_brewfile,$(PROFILE_YML))

# Every profile at once — what the CVE scan wants, since it needs completeness
# rather than fidelity to one laptop. Needs no profile, so CI can call it bare.
audit-brewfile-all:
	$(call emit_brewfile,$(PROFILE_YMLS))

# Curated list of third-party brew taps we want gone. Re-evaluated periodically
# via `make audit-taps`. Adding a tap here is a one-way intent: if it ever
# becomes needed again, declare it in roles/devbox/defaults/main/packages.yml
# (devbox_brew_taps) and remove from this list. Verified empty/unused as of
# 2026-06-20 — see git log for the audit that produced this list.
STALE_TAPS := \
  go-task/tap \
  homebrew/brew-vulns \
  homebrew/cask-fonts \
  hudochenkov/sshpass \
  jakehilborn/jakehilborn \
  mongodb/brew

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
	@$(VALIDATE_PYTHON) $(CLAUDE_SRC)/bin/validate_skill_evals.py $(SKILLS_DIR)

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
	$(require_profile)
	@$(AI_CONFIG) diff claude --repo-root "$(CURDIR)" --home "$(HOME)" --profile "$(SLIM_PROFILE)" $(ARGS)

claude-pull-review:
	$(require_profile)
	@$(AI_CONFIG) reconcile claude --repo-root "$(CURDIR)" --home "$(HOME)" --profile "$(SLIM_PROFILE)" $(ARGS)

claude-pull: claude-pull-review

# Karabiner back-propagation. The live file is edited via the Karabiner GUI; these
# targets capture ONLY the portable complex_modifications back into the repo, so the
# machine-local devices array / "Modify events" toggles are never dragged into VCS.
# Reminder-free by design is out of scope — run karabiner-pull deliberately after a
# GUI change (see karabiner_activation.md).
karabiner-diff:
	@echo "=== Drift: Karabiner complex_modifications (repo vs live ~/.config) ==="
	@if [ ! -f "$(KARABINER_DEST)" ]; then echo "  live file not found: $(KARABINER_DEST)"; exit 0; fi
	@repo_tmp=$$(mktemp); live_tmp=$$(mktemp); \
	jq -S '.profiles[0].complex_modifications' $(KARABINER_SRC) > $$repo_tmp; \
	jq -S '$(KARABINER_CM_JQ)' $(KARABINER_DEST) > $$live_tmp; \
	if diff -q $$repo_tmp $$live_tmp >/dev/null 2>&1; then \
		echo "  No drift detected."; \
	else \
		echo ""; diff -u $$repo_tmp $$live_tmp || true; \
		echo ""; echo "Pull with: make karabiner-pull"; \
	fi; \
	rm -f $$repo_tmp $$live_tmp

karabiner-pull:
	@echo "=== Pulling Karabiner complex_modifications: live ~/.config -> repo ==="
	@if [ ! -f "$(KARABINER_DEST)" ]; then echo "  ERROR: live file not found: $(KARABINER_DEST)"; exit 1; fi
	@out=$$(mktemp); \
	jq --slurpfile live $(KARABINER_DEST) \
		'.profiles[0].complex_modifications = ($$live[0] | $(KARABINER_CM_JQ))' \
		$(KARABINER_SRC) > $$out; \
	if ! jq -e . $$out >/dev/null 2>&1; then echo "  ERROR: produced invalid JSON — aborting"; rm -f $$out; exit 1; fi; \
	if diff -q $$out $(KARABINER_SRC) >/dev/null 2>&1; then \
		echo "  SKIP: no changes"; rm -f $$out; \
	else \
		mv $$out $(KARABINER_SRC); \
		echo "  PULLED: complex_modifications -> $(KARABINER_SRC)"; \
		echo "  Review with: git diff $(KARABINER_SRC)"; \
	fi

# Fast-path: kitty / nvim / fish / bash configs + Jinja templates + local overlay.
# Reuses Blocks 3-5 (dotfiles) and Block 6 (local) of install_configs.yml.
# Use `make local-push` if you want to iterate on the overlay alone.
dotfiles-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags dotfiles,local $(SLIM_OPTS) playbooks/dotfiles.yml

# Fast-path: fish + fisher plugins + tide preset + font cache.
# Reuses fish/tide/font-cache tasks in apply_configs.yml under `shell`.
# Replaces the old `fixfish` shell incantation. No sudo (slim playbook bypasses
# the defensive self-become via devbox_skip_become).
shell-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags shell $(SLIM_OPTS) playbooks/shell.yml

# Fast-path: re-register Claude Code MCP servers via `claude mcp add`.
# Reuses the MCP register tasks in apply_configs.yml under `mcp`. No sudo.
mcp-sync: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags mcp $(SLIM_OPTS) playbooks/mcp.yml

# Fast-path: gitignored local overlay (roles/devbox/local/).
# Reuses Block 6 of install_configs.yml under `local`.
local-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags local $(SLIM_OPTS) playbooks/local.yml

# Fast-path: (re)install the weekly drive backup — packages/drive-backup + the
# local.drive-backup LaunchAgent. Deploys the local overlay first: its
# ~/.config/drive-backup/config.toml is the on/off switch. No sudo.
drive-backup-push: $(COLLECTIONS_SENTINEL)
	$(require_profile)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags local,drive-backup $(SLIM_OPTS) playbooks/drive_backup.yml

# Acceptance check for the private Go module proxy (Athens behind Tamias):
# persisted go env, an existing Tamias credential, and one public + one private
# module through the proxy into a throwaway GOMODCACHE. Deliberately not part of
# `make personal`/`make work`: the credential comes from an interactive
# `tamias login`. No sudo, no profile required.
go-proxy-verify: $(COLLECTIONS_SENTINEL)
	ANSIBLE_FORCE_COLOR=1 ansible-playbook --tags go-proxy $(SLIM_OPTS) playbooks/go_proxy_verify.yml

# Run the backup now, through launchd, with exactly the scheduled environment.
drive-backup-now:
	@launchctl kickstart "gui/$$(id -u)/local.drive-backup"
	@echo "Started. Follow: tail -f ~/Library/Logs/drive-backup.log"

# Re-apply macOS basics: Touch ID for sudo, pmset disablesleep, DevToolsSecurity.
# Reuses configure_macos_basics.yml under `macos`. Sudo IS required.
# Wrapped in with_sudo_keepalive.sh — see scripts/with_sudo_keepalive.sh for
# the rationale (pam_tid + ansible stdin race on Tahoe 26.x).
macos-defaults: $(COLLECTIONS_SENTINEL) secrets-ready
	$(require_profile)
	@ANSIBLE_FORCE_COLOR=1 \
	 ANSIBLE_BECOME_PASSWORD_FILE="$(CURDIR)/scripts/keychain-become-pass.sh" \
	 ./scripts/with_sudo_keepalive.sh \
	    ansible-playbook --tags macos $(SLIM_OPTS) playbooks/macos.yml

# Stdlib-only, so it runs on bare python3 without materialising the dev venv.
sync-upstream-docs:
	@$(VALIDATE_PYTHON) scripts/sync-upstream-docs.py --repo-root "$(CURDIR)" $(ARGS)

validate-configs: test-json test-fish test-nvim ## Validate repo configs (JSON, fish, nvim)
	@echo "All config validations passed."

# settings.json.j2 is in scope deliberately. scripts/ai-config writes captured
# live values back into the UNRENDERED document, so every Jinja expression has to
# stay inside a quoted JSON value — which is exactly what jq checks here.
test-json:
	@echo "Validating JSON files..."
	@fail=0; \
	for f in $$(find $(CLAUDE_SRC) \( -name '*.json' -o -name '*.json.j2' \) -not -path '*/local/*'); do \
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
	for f in $$(find scripts roles/devbox/files/dot_claude/templates $(AI_SRC)/skills -name '*.sh' -not -path '*/future_projects/*' -not -path '*/hooks-snapshots/*'); do \
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
# playbooks/.devbox is the same directory left behind by a run whose working
# directory was playbooks/ rather than the repo root — ansible.cfg's local_tmp
# is a relative path, so it follows the CWD. `clean` used to miss it, which is
# how 15 MB of stale dev_mode dotfiles survived there for months.
clean:
	@rm -rf $(CURDIR)/.devbox $(CURDIR)/playbooks/.devbox
	@echo "Cleaned: .devbox/ and playbooks/.devbox/"
