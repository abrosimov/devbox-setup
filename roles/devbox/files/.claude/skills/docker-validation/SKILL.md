---
name: docker-validation
description: >
  Docker validation patterns — Dockerfile linting with hadolint, docker-compose linting with dclint,
  and runtime smoke testing conventions. Triggers on: dockerfile, docker-compose, hadolint, dclint, smoke test, container validation.
alwaysApply: false
---

# Docker Validation

Static linting and runtime smoke testing for Docker artifacts.

## Tools

| Tool | Purpose | Install | Requires Daemon |
|------|---------|---------|-----------------|
| hadolint | Dockerfile linter | `brew install hadolint` | No |
| dclint | docker-compose linter | `npm install -g dclint` | No |

Both are static analysis tools — no Docker daemon needed.

## Hadolint (Dockerfile Linting)

### Usage

```bash
# Lint a single Dockerfile
hadolint Dockerfile

# Lint with specific trusted registries
hadolint --trusted-registry docker.io Dockerfile

# Ignore specific rules
hadolint --ignore DL3008 --ignore DL3009 Dockerfile
```

### Configuration (`.hadolint.yaml`)

```yaml
ignored:
  - DL3008  # Pin versions in apt-get install
  - DL3009  # Delete apt-get lists after install
trustedRegistries:
  - docker.io
  - ghcr.io
```

### Key Rules

| Rule | Description | Severity |
|------|-------------|----------|
| DL3006 | Always tag the version of an image explicitly | Warning |
| DL3007 | Using latest is always a bad idea | Warning |
| DL3008 | Pin versions in apt-get install | Warning |
| DL3015 | Avoid additional packages with apt-get install | Info |
| DL3025 | Use JSON notation for CMD/ENTRYPOINT arguments | Warning |
| DL4006 | Set the SHELL option -o pipefail before a pipe | Warning |
| SC2086 | Double quote to prevent globbing and word splitting | Warning |

### File Detection

Hadolint runs on files matching:
- Exact name `Dockerfile`
- Starting with `Dockerfile.` (e.g., `Dockerfile.prod`)
- Ending with `.dockerfile` (e.g., `app.dockerfile`)

## DCLint (Docker Compose Linting)

### Usage

```bash
# Lint compose files in current directory
dclint .

# Lint a specific file
dclint docker-compose.yml
```

### File Detection

DCLint runs on files matching:
- `docker-compose.yml` / `docker-compose.yaml`
- `compose.yml` / `compose.yaml`

## Smoke Test Conventions

Runtime verification that containers actually start and respond correctly. Two conventions are supported:

### Convention 1: Makefile Target

```makefile
.PHONY: smoke
smoke:
	docker compose up -d
	sleep 5
	curl -sf http://localhost:8080/health || (docker compose logs && exit 1)
	docker compose down
```

Detected by: `make -qn smoke` succeeds (target exists).

### Convention 2: Script

```bash
#!/usr/bin/env bash
# scripts/smoke-test.sh
set -euo pipefail
docker compose up -d
trap 'docker compose down' EXIT
sleep 5
curl -sf http://localhost:8080/health
```

Detected by: `scripts/smoke-test.sh` is executable.

### Build-Boot-Probe-Kill Pattern

The standard smoke test pattern:

1. **Build**: `docker compose build` (or `docker build`)
2. **Boot**: `docker compose up -d`
3. **Probe**: `curl -sf http://localhost:PORT/health` (or similar readiness check)
4. **Kill**: `docker compose down` (always — use `trap` for cleanup)

```bash
# Full pattern
docker compose build
docker compose up -d
trap 'docker compose down' EXIT
sleep 5
curl -sf http://localhost:8080/health
echo "Smoke test passed"
```

## Integration with verify-se-completion

The `verify-se-completion` script includes Docker validation as phases 5 and 6:

- **Phase 5 (Docker Lint)**: Runs always. Finds Dockerfiles (maxdepth 3) and runs hadolint; finds compose files and runs dclint. Exit code 6 on failure.
- **Phase 6 (Smoke Test)**: Skipped in `--quick` mode. Detects smoke test convention and runs it. Exit code 7 on failure.

Both phases skip gracefully if tools are not installed or no Docker files are found.

## Post-Edit Hook Integration

The `post-edit-lint` hook automatically runs:
- **hadolint** when editing Dockerfiles
- **dclint** when editing compose files

No configuration needed — detection is by filename pattern.
