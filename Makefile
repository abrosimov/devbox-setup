# Makefile

PLAYBOOK      := playbooks/main.yml
VAULT_OPTS    := --ask-vault-pass
SUDO_OPTS     := -K
EXTRA_VARS    ?=
TEST_VAULT    := --vault-password-file tests/vault-password -e vault_file=../tests/vault.yml
PROFILE       ?=
PROFILE_OPTS  = $(if $(PROFILE),-e @profiles/$(PROFILE).yml)

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

.PHONY: run dev help init vault-init lint check check-dev validate-claude validate-skills eval-skills improve-skills \
       work personal dev-work dev-personal check-work check-personal \
       upgrade-work upgrade-personal \
       fixfish list-skills list-agents \
       claude-diff claude-pull \
       test test-nvim test-fish test-json test-bash test-skill-evals

help:
	@echo ""
	@echo "Usage:"
	@echo "  make personal         - run with personal profile (PROJECTS_DIR=~/Projects)"
	@echo "  make work             - run with work profile (PROJECTS_DIR=~/Work)"
	@echo "  make dev-personal     - dev_mode + personal profile"
	@echo "  make dev-work         - dev_mode + work profile"
	@echo "  make check-personal   - dry-run with personal profile"
	@echo "  make check-work       - dry-run with work profile"
	@echo "  make check-dev        - dry-run in dev_mode (test vault)"
	@echo "  make lint             - syntax check + ansible-lint"
	@echo "  make init             - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make vault-init       - create and encrypt vault/devbox_ssh_config.yml"
	@echo "  make upgrade-personal - upgrade all managed packages (personal profile)"
	@echo "  make upgrade-work     - upgrade all managed packages (work profile)"
	@echo "  make validate-claude  - validate Claude Code agent/skill library"
	@echo "  make validate-skills  - validate skill evals (structure, schema, coverage)"
	@echo "  make eval-skills      - run trigger evals via Anthropic's run_eval.py (slow, needs claude CLI)"
	@echo "  make improve-skills   - optimize skill description for trigger accuracy (run_loop.py)"
	@echo "  make fixfish           - upgrade fish, update plugins, apply tide config"
	@echo "  make test             - run all config validation tests"
	@echo "  make test-nvim        - headless smoke test of nvim config"
	@echo "  make test-fish        - fish shell config syntax check"
	@echo "  make test-json        - JSON config/schema validation"
	@echo "  make test-bash        - bash script syntax check"
	@echo "  make list-skills      - list all Claude Code skills"
	@echo "  make list-agents      - list all Claude Code agents"
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
	ansible-playbook $(SUDO_OPTS) $(VERBOSE) $(VAULT_OPTS) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

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

lint:
	ansible-playbook --syntax-check $(TEST_VAULT) $(PLAYBOOK)
	ansible-lint $(PLAYBOOK)

check:
ifndef PROFILE
	$(error PROFILE is required. Use: make check-personal or make check-work)
endif
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(SUDO_OPTS) $(VERBOSE) $(VAULT_OPTS) $(PROFILE_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

check-work:
	$(MAKE) check PROFILE=work V=$(V)

check-personal:
	$(MAKE) check PROFILE=personal V=$(V)

upgrade-work:
	$(MAKE) run PROFILE=work EXTRA_VARS='-e upgrade_mode=true' V=$(V)

upgrade-personal:
	$(MAKE) run PROFILE=personal EXTRA_VARS='-e upgrade_mode=true' V=$(V)

check-dev:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(TEST_VAULT) -e dev_mode=true $(PLAYBOOK)

fixfish:
	@echo "Upgrading fish and applying tide config..."
	brew upgrade fish
	fish -c 'fisher remove ilancosman/tide@v6 2>/dev/null; fisher install ilancosman/tide; fisher update'
	fish -c 'tide configure --auto --style=Rainbow --prompt_colors='"'"'True color'"'"' --show_time='"'"'24-hour format'"'"' --rainbow_prompt_separators=Angled --powerline_prompt_heads=Sharp --powerline_prompt_tails=Flat --powerline_prompt_style='"'"'One line'"'"' --prompt_spacing=Compact --icons='"'"'Many icons'"'"' --transient=No'
	@echo "Done. Restart your shell to apply changes."

init:
	@./scripts/init.sh

vault-init:
	@./scripts/vault-init.sh

list-skills:
	@ls -1 $(SKILLS_DIR) | sort | nl -ba

list-agents:
	@ls -1 roles/devbox/files/.claude/agents/*.md 2>/dev/null | xargs -I{} basename {} .md | sort | nl -ba

validate-claude:
	@python3 roles/devbox/files/.claude/bin/validate-config.py --root roles/devbox/files/.claude

validate-skills:
	@echo "Validating skill eval files..."
	@python3 roles/devbox/files/.claude/bin/validate-skill-evals

# Anthropic skill-creator scripts (installed via claude-plugins-official)
EVAL_SCRIPTS := $(shell ls -d ~/.claude/plugins/cache/anthropic-agent-skills/example-skills/*/skills/skill-creator/scripts 2>/dev/null | head -1)
SKILLS_DIR   := roles/devbox/files/.claude/skills
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

CLAUDE_ROOT_FILES := CLAUDE.md settings.json hooks.json config.md
CLAUDE_SRC        := roles/devbox/files/.claude
CLAUDE_DEST       := $(HOME)/.claude

claude-diff:
	@echo "=== Drift: deployed ~/.claude vs repo (root files only) ==="
	@drift=0; \
	for f in $(CLAUDE_ROOT_FILES); do \
		if ! diff -q $(CLAUDE_SRC)/$$f $(CLAUDE_DEST)/$$f >/dev/null 2>&1; then \
			echo "  CHANGED: $$f"; drift=1; \
		fi; \
	done; \
	[ $$drift -eq 0 ] && echo "  No drift detected." || echo "  Run 'make claude-pull' to back-propagate."

claude-pull:
	@echo "=== Pulling root files from ~/.claude to repo ==="
	@for f in $(CLAUDE_ROOT_FILES); do \
		if ! diff -q $(CLAUDE_SRC)/$$f $(CLAUDE_DEST)/$$f >/dev/null 2>&1; then \
			cp $(CLAUDE_DEST)/$$f $(CLAUDE_SRC)/$$f; \
			echo "  PULLED: $$f"; \
		else \
			echo "  SKIP:   $$f (no changes)"; \
		fi; \
	done
	@echo "Review with: git diff"

test: test-json test-fish test-bash test-nvim test-skill-evals
	@echo "All tests passed."

test-json:
	@echo "Validating JSON files..."
	@fail=0; \
	for f in $$(find roles/devbox/files/.claude -name '*.json' -not -path '*/local/*'); do \
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
	for f in $$(find roles/devbox/files/.claude/bin -type f); do \
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
	@python3 roles/devbox/files/.claude/bin/validate-skill-evals
