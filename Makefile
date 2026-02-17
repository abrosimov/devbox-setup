# Makefile

PLAYBOOK      := playbooks/main.yml
VAULT_OPTS    := --ask-vault-pass
SUDO_OPTS     := -K
EXTRA_VARS    ?=
TEST_VAULT    := --vault-password-file tests/vault-password -e vault_file=../tests/vault.yml

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

.PHONY: run dev help init vault-init lint check check-dev validate-claude

help:
	@echo ""
	@echo "Usage:"
	@echo "  make run           - run playbook normally"
	@echo "  make run V=3       - run playbook with -vvv"
	@echo "  make dev           - run in dev_mode"
	@echo "  make dev V=2       - run in dev_mode with -vv"
	@echo "  make run EXTRA_VARS='-e foo=bar'"
	@echo "  make lint          - syntax check + ansible-lint"
	@echo "  make check         - dry-run (check mode)"
	@echo "  make check-dev     - dry-run in dev_mode"
	@echo "  make init          - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make vault-init    - create and encrypt vault/devbox_ssh_config.yml"
	@echo "  make validate-claude - validate Claude Code agent/skill library"
	@echo ""

run:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook $(SUDO_OPTS) $(VERBOSE) $(VAULT_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

dev:
	$(MAKE) run EXTRA_VARS='-e dev_mode=true' V=$(V)

lint:
	ansible-playbook --syntax-check $(TEST_VAULT) $(PLAYBOOK)
	ansible-lint $(PLAYBOOK)

check:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(SUDO_OPTS) $(VERBOSE) $(VAULT_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

check-dev:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook --check $(VERBOSE) $(TEST_VAULT) -e dev_mode=true $(PLAYBOOK)

init:
	@./scripts/init.sh

vault-init:
	@./scripts/vault-init.sh

validate-claude:
	@roles/devbox/files/.claude/bin/validate-library
