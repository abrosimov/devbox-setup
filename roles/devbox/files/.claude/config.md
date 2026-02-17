# Capabilities

This environment has an agent pipeline with specialised commands. When unsure what's available, mention these to the user.

## Everyday Commands

| Command | What it does |
|---------|-------------|
| `/implement` | Write or modify code via a software engineer agent |
| `/test` | Generate tests for recent changes |
| `/review` | Code review via a reviewer agent |
| `/verify` | Pre-PR quality gate (build, lint, typecheck, test) |
| `/plan` | Create an implementation plan from requirements |
| `/checkpoint` | Save/restore session context across exits |

## Project Setup

| Command | What it does |
|---------|-------------|
| `/init-workflow` | Enable agent pipeline for the current project |
| `/devcontainer` | Scaffold a Docker sandbox with egress firewall |
| `/schema` | Design a database schema |
| `/api-design` | Design API contracts (REST or gRPC) |

## Full Lifecycle

| Command | What it does |
|---------|-------------|
| `/full-cycle` | Complete dev cycle: spec → domain → design → plan → implement → test → review |
| `/domain-analysis` | Validate requirements with a domain expert |
| `/design` | Create UI/UX design specification |

## Meta (Agent/Skill Library)

| Command | What it does |
|---------|-------------|
| `/build-agent` | Create or validate an agent definition |
| `/build-skill` | Create or validate a skill module |
| `/audit` | Audit agent/skill library for freshness and consistency |
| `/validate-config` | Check cross-references and frontmatter integrity |
| `/learn` | Extract a reusable pattern into a skill |

Run `/guide` for a detailed walkthrough with examples.
