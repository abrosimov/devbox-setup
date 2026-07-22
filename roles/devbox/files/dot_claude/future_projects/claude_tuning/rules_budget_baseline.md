# Rules-Budget Report

**Root:** `/Users/kabrosimov/Work/devbox-setup/roles/devbox/files/dot_claude`
**Budget reference:** 150-200 concurrent instructions

## Aggregate

| Scope | Artefacts | Flat | Hard | Soft | Strength-weighted |
|---|---:|---:|---:|---:|---:|
| Always-on | 6 | 119 | 28 | 91 | 147 |
| Trigger-loaded | 85 | 957 | 157 | 800 | 1114 |

**Scope-weighted aggregate:** 1314

**Always-on flat count:** 119 (under the 150-200 budget)

## Always-on artefacts

| Artefact | Kind | Scope | Flat | Hard | Soft | Strength |
|---|---|---|---:|---:|---:|---:|
| `USER_AUTHORITY_PROTOCOL.md` | uap | always-on | 56 | 12 | 44 | 68 |
| `skills/code-comments/SKILL.md` | skill | always-on | 21 | 5 | 16 | 26 |
| `skills/lint-discipline/SKILL.md` | skill | always-on | 21 | 5 | 16 | 26 |
| `skills/lsp-navigation/SKILL.md` | skill | always-on | 4 | 1 | 3 | 5 |
| `skills/project-preferences/SKILL.md` | skill | always-on | 11 | 3 | 8 | 14 |
| `skills/project-toolchain/SKILL.md` | skill | always-on | 6 | 2 | 4 | 8 |

## Top 10 offenders (any scope)

| Artefact | Kind | Scope | Flat | Hard | Soft | Strength |
|---|---|---|---:|---:|---:|---:|
| `skills/code-writing-protocols/SKILL.md` | skill | trigger | 157 | 25 | 132 | 182 |
| `USER_AUTHORITY_PROTOCOL.md` | uap | always-on | 56 | 12 | 44 | 68 |
| `agents/consistency_checker.md` | agent | trigger | 49 | 2 | 47 | 51 |
| `agents/meta_reviewer.md` | agent | trigger | 47 | 5 | 42 | 52 |
| `agents/freshness_auditor.md` | agent | trigger | 40 | 1 | 39 | 41 |
| `skills/diverge-synthesize-select/SKILL.md` | skill | trigger | 35 | 5 | 30 | 40 |
| `agents/content_reviewer.md` | agent | trigger | 30 | 1 | 29 | 31 |
| `skills/workflow/SKILL.md` | skill | trigger | 29 | 6 | 23 | 35 |
| `agents/code_reviewer.md` | agent | trigger | 28 | 4 | 24 | 32 |
| `agents/technical_product_manager.md` | agent | trigger | 27 | 9 | 18 | 36 |

## All artefacts

| Artefact | Kind | Scope | Flat | Hard | Soft | Strength |
|---|---|---|---:|---:|---:|---:|
| `USER_AUTHORITY_PROTOCOL.md` | uap | always-on | 56 | 12 | 44 | 68 |
| `agents/agent_builder.md` | agent | trigger | 14 | 7 | 7 | 21 |
| `agents/api_designer.md` | agent | trigger | 10 | 0 | 10 | 10 |
| `agents/architect.md` | agent | trigger | 1 | 0 | 1 | 1 |
| `agents/build_resolver_go.md` | agent | trigger | 1 | 0 | 1 | 1 |
| `agents/code_reviewer.md` | agent | trigger | 28 | 4 | 24 | 32 |
| `agents/consistency_checker.md` | agent | trigger | 49 | 2 | 47 | 51 |
| `agents/content_reviewer.md` | agent | trigger | 30 | 1 | 29 | 31 |
| `agents/database_designer.md` | agent | trigger | 20 | 2 | 18 | 22 |
| `agents/database_reviewer.md` | agent | trigger | 19 | 0 | 19 | 19 |
| `agents/designer.md` | agent | trigger | 11 | 2 | 9 | 13 |
| `agents/doc_updater.md` | agent | trigger | 5 | 2 | 3 | 7 |
| `agents/domain_expert.md` | agent | trigger | 25 | 1 | 24 | 26 |
| `agents/domain_modeller.md` | agent | trigger | 9 | 0 | 9 | 9 |
| `agents/focus_coach.md` | agent | trigger | 16 | 3 | 13 | 19 |
| `agents/freshness_auditor.md` | agent | trigger | 40 | 1 | 39 | 41 |
| `agents/implementation_planner.md` | agent | trigger | 15 | 5 | 10 | 20 |
| `agents/integration_tests_writer_go.md` | agent | trigger | 7 | 1 | 6 | 8 |
| `agents/integration_tests_writer_python.md` | agent | trigger | 7 | 1 | 6 | 8 |
| `agents/meta_reviewer.md` | agent | trigger | 47 | 5 | 42 | 52 |
| `agents/observability_engineer.md` | agent | trigger | 9 | 3 | 6 | 12 |
| `agents/refactor_cleaner.md` | agent | trigger | 5 | 3 | 2 | 8 |
| `agents/skill_builder.md` | agent | trigger | 12 | 0 | 12 | 12 |
| `agents/software_engineer_frontend.md` | agent | trigger | 15 | 4 | 11 | 19 |
| `agents/software_engineer_go.md` | agent | trigger | 7 | 2 | 5 | 9 |
| `agents/software_engineer_python.md` | agent | trigger | 12 | 3 | 9 | 15 |
| `agents/tdd_guide.md` | agent | trigger | 10 | 2 | 8 | 12 |
| `agents/technical_product_manager.md` | agent | trigger | 27 | 9 | 18 | 36 |
| `agents/unit_tests_writer.md` | agent | trigger | 24 | 3 | 21 | 27 |
| `commands/techne-api-design.md` | command | trigger | 1 | 0 | 1 | 1 |
| `commands/techne-audit.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-build-agent.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-build-skill.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-decision.md` | command | trigger | 5 | 0 | 5 | 5 |
| `commands/techne-design.md` | command | trigger | 1 | 0 | 1 | 1 |
| `commands/techne-devcontainer.md` | command | trigger | 1 | 0 | 1 | 1 |
| `commands/techne-domain-analysis.md` | command | trigger | 1 | 0 | 1 | 1 |
| `commands/techne-focus.md` | command | trigger | 2 | 1 | 1 | 3 |
| `commands/techne-guide.md` | command | trigger | 4 | 0 | 4 | 4 |
| `commands/techne-implement.md` | command | trigger | 8 | 1 | 7 | 9 |
| `commands/techne-learn.md` | command | trigger | 1 | 1 | 0 | 2 |
| `commands/techne-log.md` | command | trigger | 5 | 0 | 5 | 5 |
| `commands/techne-next.md` | command | trigger | 4 | 4 | 0 | 8 |
| `commands/techne-options.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-plan.md` | command | trigger | 1 | 1 | 0 | 2 |
| `commands/techne-review.md` | command | trigger | 3 | 1 | 2 | 4 |
| `commands/techne-schema.md` | command | trigger | 4 | 0 | 4 | 4 |
| `commands/techne-test.md` | command | trigger | 4 | 1 | 3 | 5 |
| `commands/techne-think.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-validate-config.md` | command | trigger | 0 | 0 | 0 | 0 |
| `commands/techne-verify.md` | command | trigger | 0 | 0 | 0 | 0 |
| `skills/agent-base-protocol/SKILL.md` | skill | trigger | 15 | 3 | 12 | 18 |
| `skills/agent-builder/SKILL.md` | skill | trigger | 8 | 1 | 7 | 9 |
| `skills/agent-communication/SKILL.md` | skill | trigger | 20 | 0 | 20 | 20 |
| `skills/ast-grep/SKILL.md` | skill | trigger | 0 | 0 | 0 | 0 |
| `skills/code-comments/SKILL.md` | skill | always-on | 21 | 5 | 16 | 26 |
| `skills/code-writing-protocols/SKILL.md` | skill | trigger | 157 | 25 | 132 | 182 |
| `skills/config/SKILL.md` | skill | trigger | 1 | 0 | 1 | 1 |
| `skills/diverge-synthesize-select/SKILL.md` | skill | trigger | 35 | 5 | 30 | 40 |
| `skills/docker-validation/SKILL.md` | skill | trigger | 4 | 1 | 3 | 5 |
| `skills/editing-claude-config/SKILL.md` | skill | trigger | 6 | 0 | 6 | 6 |
| `skills/fpf-thinking/SKILL.md` | skill | trigger | 6 | 1 | 5 | 7 |
| `skills/frontend-engineer/SKILL.md` | skill | trigger | 12 | 1 | 11 | 13 |
| `skills/frontend-testing/SKILL.md` | skill | trigger | 2 | 2 | 0 | 4 |
| `skills/frontend-tooling/SKILL.md` | skill | trigger | 0 | 0 | 0 | 0 |
| `skills/go-engineer/SKILL.md` | skill | trigger | 8 | 2 | 6 | 10 |
| `skills/go-review-checklist/SKILL.md` | skill | trigger | 14 | 2 | 12 | 16 |
| `skills/go-testing/SKILL.md` | skill | trigger | 12 | 1 | 11 | 13 |
| `skills/hooks-architecture/SKILL.md` | skill | trigger | 4 | 0 | 4 | 4 |
| `skills/iterative-retrieval/SKILL.md` | skill | trigger | 4 | 0 | 4 | 4 |
| `skills/lint-discipline/SKILL.md` | skill | always-on | 21 | 5 | 16 | 26 |
| `skills/lsp-navigation/SKILL.md` | skill | always-on | 4 | 1 | 3 | 5 |
| `skills/lsp-tools/SKILL.md` | skill | trigger | 2 | 0 | 2 | 2 |
| `skills/mcp-playwright/SKILL.md` | skill | trigger | 5 | 2 | 3 | 7 |
| `skills/mcp-sequential-thinking/SKILL.md` | skill | trigger | 6 | 2 | 4 | 8 |
| `skills/mcp-storybook/SKILL.md` | skill | trigger | 3 | 2 | 1 | 5 |
| `skills/playwright-e2e/SKILL.md` | skill | trigger | 6 | 2 | 4 | 8 |
| `skills/project-preferences/SKILL.md` | skill | always-on | 11 | 3 | 8 | 14 |
| `skills/project-toolchain/SKILL.md` | skill | always-on | 6 | 2 | 4 | 8 |
| `skills/python-engineer/SKILL.md` | skill | trigger | 13 | 2 | 11 | 15 |
| `skills/python-monolith/SKILL.md` | skill | trigger | 5 | 1 | 4 | 6 |
| `skills/python-testing/SKILL.md` | skill | trigger | 15 | 2 | 13 | 17 |
| `skills/python-tooling/SKILL.md` | skill | trigger | 8 | 3 | 5 | 11 |
| `skills/sandbox-toolchain/SKILL.md` | skill | trigger | 10 | 9 | 1 | 19 |
| `skills/self-contained-options/SKILL.md` | skill | trigger | 9 | 1 | 8 | 10 |
| `skills/shared-utils/SKILL.md` | skill | trigger | 1 | 0 | 1 | 1 |
| `skills/skill-builder/SKILL.md` | skill | trigger | 11 | 0 | 11 | 11 |
| `skills/structured-output/SKILL.md` | skill | trigger | 1 | 1 | 0 | 2 |
| `skills/techne-fewer-permission-prompts/SKILL.md` | skill | trigger | 4 | 4 | 0 | 8 |
| `skills/ui-design/SKILL.md` | skill | trigger | 1 | 0 | 1 | 1 |
| `skills/workflow/SKILL.md` | skill | trigger | 29 | 6 | 23 | 35 |
