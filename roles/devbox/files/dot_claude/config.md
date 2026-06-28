# Capabilities

This environment has an agent pipeline with specialised commands. When unsure what's available, mention these to the user.

## Everyday Commands

| Command | What it does |
|---------|-------------|
| `/techne-implement` | Write or modify code via a software engineer agent |
| `/techne-test` | Generate tests for recent changes |
| `/techne-review` | Code review via a reviewer agent |
| `/techne-verify` | Pre-PR quality gate (build, lint, typecheck, test) |
| `/techne-plan` | Create an implementation plan from requirements |

## Project Setup

| Command | What it does |
|---------|-------------|
| `/techne-devcontainer` | Scaffold a Docker sandbox with egress firewall |
| `/techne-schema` | Design a database schema |
| `/techne-api-design` | Design API contracts (REST or gRPC) |

## Discovery & Design

| Command | What it does |
|---------|-------------|
| `/techne-domain-analysis` | Validate requirements with a domain expert |
| `/techne-design` | Create UI/UX design specification |

## Meta (Agent/Skill Library)

| Command | What it does |
|---------|-------------|
| `/techne-build-agent` | Create or validate an agent definition |
| `/techne-build-skill` | Create or validate a skill module |
| `/techne-audit` | Audit agent/skill library for freshness and consistency |
| `/techne-validate-config` | Check cross-references and frontmatter integrity |
| `/techne-learn` | Extract a reusable pattern into a skill |

Run `/techne-guide` for a detailed walkthrough with examples.
