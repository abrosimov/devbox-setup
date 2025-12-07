# Makefile

PLAYBOOK      := playbooks/main.yml
VAULT_OPTS    := --ask-vault-pass
SUDO_OPTS     := -K
EXTRA_VARS    ?=

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

.PHONY: run dev help init vault-init

help:
	@echo ""
	@echo "Usage:"
	@echo "  make run           - run playbook normally"
	@echo "  make run V=3       - run playbook with -vvv"
	@echo "  make dev           - run in dev_mode"
	@echo "  make dev V=2       - run in dev_mode with -vv"
	@echo "  make run EXTRA_VARS='-e foo=bar'"
	@echo "  make init          - install Homebrew, Ansible, and dependencies (macOS only)"
	@echo "  make vault-init    - create and encrypt vault/devbox_ssh_config.yml"
	@echo ""

run:
	ANSIBLE_FORCE_COLOR=1 \
	ansible-playbook $(SUDO_OPTS) $(VERBOSE) $(VAULT_OPTS) $(EXTRA_VARS) $(PLAYBOOK)

dev:
	$(MAKE) run EXTRA_VARS='-e dev_mode=true' V=$(V)

init:
	@./scripts/init.sh

vault-init:
	@./scripts/vault-init.sh
