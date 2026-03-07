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

.PHONY: run dev help init vault-init lint check check-dev validate-claude \
       work personal dev-work dev-personal check-work check-personal \
       test test-nvim test-fish test-json test-bash

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
	@echo "  make validate-claude  - validate Claude Code agent/skill library"
	@echo "  make test             - run all config validation tests"
	@echo "  make test-nvim        - headless smoke test of nvim config"
	@echo "  make test-fish        - fish shell config syntax check"
	@echo "  make test-json        - JSON config/schema validation"
	@echo "  make test-bash        - bash script syntax check"
	@echo ""
	@echo "Options:"
	@echo "  V=1..4                - verbosity level (-v to -vvvv)"
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

check-dev:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(TEST_VAULT) -e dev_mode=true $(PLAYBOOK)

init:
	@./scripts/init.sh

vault-init:
	@./scripts/vault-init.sh

validate-claude:
	@roles/devbox/files/.claude/bin/validate-library

test: test-json test-fish test-bash test-nvim
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
