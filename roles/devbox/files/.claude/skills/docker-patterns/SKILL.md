---
name: docker-patterns
description: >
  Docker patterns for development and deployment. Triggers on: docker, dockerfile, docker-compose, container, multi-stage build.
---

# Docker Patterns

## Multi-Stage Builds

Separate build environment from production image (minimise size, attack surface).

### Go Example

```dockerfile
# Stage 1: Build
FROM golang:1.24-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main .

# Stage 2: Production
FROM alpine:3.21
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]
```

**Result**: Builder image ~800MB, production image ~15MB.

### Node.js Example

```dockerfile
# Stage 1: Build
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Production
FROM node:24-alpine
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

## Docker Compose for Local Development

### Service Dependencies

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    depends_on:
      db:
        condition: service_healthy  # Wait for healthcheck
    environment:
      DATABASE_URL: postgres://postgres:dev@db:5432/mydb
    ports:
      - "8080:8080"
```

**Without healthcheck**: `depends_on` only waits for container start (not readiness).

### Volume Management

```yaml
services:
  app:
    image: myapp
    volumes:
      # Named volume (persistent, managed by Docker)
      - pgdata:/var/lib/postgresql/data

      # Bind mount (development: sync local changes)
      - ./src:/app/src

      # tmpfs (ephemeral, in-memory)
      - type: tmpfs
        target: /tmp

volumes:
  pgdata:  # Declare named volume
```

**When to use**:
- **Named volumes**: production data, databases
- **Bind mounts**: development (hot reload)
- **tmpfs**: temporary files, caches (never persist)

### Networking

```yaml
services:
  frontend:
    networks:
      - public

  backend:
    networks:
      - public
      - private

  db:
    networks:
      - private  # Not exposed to frontend

networks:
  public:
  private:
    internal: true  # No external access
```

**Automatic DNS**: `backend` resolves to backend container IP.

### Environment Variables

```yaml
# .env file (not committed to git)
DB_PASSWORD=secret123
API_KEY=xyz

# docker-compose.yml
services:
  app:
    env_file:
      - .env  # Load all variables
    environment:
      # Override or add specific variables
      DATABASE_URL: postgres://user:${DB_PASSWORD}@db/mydb
      DEBUG: "true"
```

## Container Security

### Non-Root User

```dockerfile
FROM alpine:3.21

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Switch to non-root user
USER appuser

COPY --chown=appuser:appgroup . /app
WORKDIR /app
CMD ["./app"]
```

**Why**: Limit damage if container is compromised (no root privileges).

### Read-Only Filesystem

```yaml
services:
  app:
    image: myapp
    read_only: true
    tmpfs:
      - /tmp  # Allow writes to temporary directory
      - /var/run
```

**Why**: Prevent malicious code from modifying application files.

### No New Privileges

```yaml
services:
  app:
    image: myapp
    security_opt:
      - no-new-privileges:true
```

**Why**: Prevent privilege escalation via setuid binaries.

### Minimal Base Images

| Image | Size | Use Case |
|-------|------|----------|
| **distroless** | ~2MB | Production (Go, Java, Node) — no shell, no package manager |
| **alpine** | ~5MB | Production (when you need apk for runtime dependencies) |
| **scratch** | 0MB | Static binaries (Go with CGO_ENABLED=0) |
| **ubuntu** | ~70MB | Development, complex dependencies |

```dockerfile
# Distroless example (Go)
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/main /app
CMD ["/app"]
```

**No shell** = no debugging with `docker exec` (use ephemeral debug container).

## Health Checks

### Dockerfile

```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY . .
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["node", "server.js"]
```

### Docker Compose

```yaml
services:
  api:
    build: .
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s  # Grace period for slow startup
```

**Status**: `docker ps` shows health status (healthy, unhealthy, starting).

## .dockerignore

Exclude files from build context (faster builds, smaller images).

```
# .dockerignore
.git
.env
.env.local
*.md
node_modules
dist
coverage
.DS_Store
*.log
```

**Why**: Reduces build context size sent to Docker daemon (especially large for bind mounts).

## Layer Caching Optimisation

Order matters — least-changed files first.

### Bad (cache invalidated on every code change)

```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY . .  # Everything in one layer
RUN npm ci
CMD ["node", "server.js"]
```

### Good (cache package install layer)

```dockerfile
FROM node:24-alpine
WORKDIR /app

# 1. Copy dependency files (rarely change)
COPY package*.json ./

# 2. Install dependencies (cached until package.json changes)
RUN npm ci

# 3. Copy application code (changes frequently)
COPY . .

CMD ["node", "server.js"]
```

**Result**: Code changes don't re-run `npm ci` (saves minutes per build).

## Debug Patterns

### View Logs

```bash
# Follow logs
docker logs -f container_name

# Last 100 lines
docker logs --tail 100 container_name

# Logs since timestamp
docker logs --since 2024-01-01T10:00:00 container_name
```

### Execute Commands

```bash
# Interactive shell
docker exec -it container_name sh

# Run single command
docker exec container_name ls -la /app

# Run as root (for debugging)
docker exec -u root -it container_name sh
```

### Inspect Container

```bash
# Full container details (JSON)
docker inspect container_name

# Specific field (IP address)
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' container_name

# Environment variables
docker inspect -f '{{.Config.Env}}' container_name
```

### Debug Distroless Images

No shell → use ephemeral debug container:

```bash
# Start debug container with shared process namespace
docker run -it --pid=container:target_container --net=container:target_container \
  alpine sh

# Now you can inspect processes, network, filesystem of target_container
```

### Volume Inspection

```bash
# List volumes
docker volume ls

# Inspect volume (find mount point)
docker volume inspect volume_name

# Backup volume
docker run --rm -v volume_name:/data -v $(pwd):/backup alpine \
  tar czf /backup/volume_backup.tar.gz -C /data .

# Restore volume
docker run --rm -v volume_name:/data -v $(pwd):/backup alpine \
  tar xzf /backup/volume_backup.tar.gz -C /data
```

## Best Practises

1. **One process per container** (not multiple services in one container)
2. **Use .dockerignore** (exclude unnecessary files)
3. **Multi-stage builds** (separate build from runtime)
4. **Pin base image versions** (`alpine:3.21`, not `alpine:latest`)
5. **Layer caching** (order Dockerfile instructions by change frequency)
6. **Health checks** (for production deployments)
7. **Non-root user** (security)
8. **Read-only filesystem** (when possible)
