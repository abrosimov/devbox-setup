---
name: deployment-patterns
description: >
  CI/CD and deployment patterns. Triggers on: deployment, ci/cd, rollback, blue-green, canary, health checks.
---

# Deployment Patterns

## CI Pipeline Stages

```
Lint → Test → Build → Security Scan → Deploy
```

### Stage 1: Lint

Static analysis, code style, type checking.

```yaml
# GitHub Actions example
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Lint
      run: |
        golangci-lint run
        # or: ruff check (Python)
        # or: eslint . (TypeScript)
```

**Fast feedback**: Fail fast on style issues before expensive test/build stages.

### Stage 2: Test

Unit tests, integration tests, coverage.

```yaml
test:
  runs-on: ubuntu-latest
  needs: lint
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_PASSWORD: test
  steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: go test -v -race -coverprofile=coverage.out ./...
    - name: Upload coverage
      uses: codecov/codecov-action@v4
```

### Stage 3: Build

Compile, package, create container image.

```yaml
build:
  runs-on: ubuntu-latest
  needs: test
  steps:
    - uses: actions/checkout@v4
    - name: Build Docker image
      run: docker build -t myapp:${{ github.sha }} .
    - name: Push to registry
      run: |
        docker tag myapp:${{ github.sha }} myregistry/myapp:${{ github.sha }}
        docker tag myapp:${{ github.sha }} myregistry/myapp:latest
        docker push myregistry/myapp:${{ github.sha }}
        docker push myregistry/myapp:latest
```

**Tagging strategy**:
- `SHA` (e.g., `myapp:a1b2c3d`) — specific commit (immutable, rollback target)
- `latest` — most recent build (convenience, not for production)
- `v1.2.3` — semantic version (from git tags)

### Stage 4: Security Scan

Vulnerability scanning, secret detection, dependency audit.

```yaml
security:
  runs-on: ubuntu-latest
  needs: build
  steps:
    - name: Scan image
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: myregistry/myapp:${{ github.sha }}
        severity: 'CRITICAL,HIGH'
        exit-code: '1'  # Fail pipeline if vulnerabilities found
```

### Stage 5: Deploy

Deploy to staging/production.

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: security
  steps:
    - name: Deploy to staging
      run: |
        kubectl set image deployment/myapp myapp=myregistry/myapp:${{ github.sha }}
        kubectl rollout status deployment/myapp
```

## Docker Deployment

### Registry Tagging

```bash
# Build with SHA tag
docker build -t myregistry/myapp:a1b2c3d .

# Push SHA tag (immutable)
docker push myregistry/myapp:a1b2c3d

# Tag as latest (mutable, for development)
docker tag myregistry/myapp:a1b2c3d myregistry/myapp:latest
docker push myregistry/myapp:latest

# Tag with semver (from git tag)
docker tag myregistry/myapp:a1b2c3d myregistry/myapp:v1.2.3
docker push myregistry/myapp:v1.2.3
```

**Production**: Always use SHA or semver tags (immutable, rollback-safe).

### Rolling Updates

Kubernetes example:

```yaml
# deployment.yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max 1 extra pod during update (total 4)
      maxUnavailable: 1  # Max 1 pod down during update (min 2)
```

**Process**:
1. Create new pod with new image
2. Wait for readiness probe
3. Terminate old pod
4. Repeat until all pods updated

**Zero downtime**: At least `replicas - maxUnavailable` pods always running.

## Health Checks

### Readiness Probe

"Am I ready for traffic?"

```yaml
# Kubernetes
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

**Behaviour**:
- Fails → pod removed from service (no traffic)
- Passes → pod added to service
- Use case: waiting for database connection, cache warm-up

**Endpoint example** (Go):
```go
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    if !db.Ping() {
        http.Error(w, "database not ready", http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ready"))
}
```

### Liveness Probe

"Am I still alive?"

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

**Behaviour**:
- Fails → pod restarted
- Use case: deadlock detection, unrecoverable state

**Warning**: Don't check external dependencies (database, API) — transient failures will cause restart loop.

**Endpoint example** (Go):
```go
func livenessHandler(w http.ResponseWriter, r *http.Request) {
    // Check internal state only (not external dependencies)
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("alive"))
}
```

### Startup Probe

"Am I still starting up?"

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  failureThreshold: 30  # 30 * 10s = 5 minutes grace period
  periodSeconds: 10
```

**Behaviour**:
- Disables liveness/readiness probes until passes
- Use case: slow startup (data loading, cache warm-up)

**When to use**: Application takes >30s to start (otherwise use `initialDelaySeconds` on liveness).

## Graceful Shutdown

### SIGTERM Handling

Kubernetes sends SIGTERM before SIGKILL (default 30s grace period).

```go
// Go example
func main() {
    server := &http.Server{Addr: ":8080", Handler: router}

    // Start server
    go func() {
        if err := server.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatal(err)
        }
    }()

    // Wait for SIGTERM
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)
    <-quit

    // Graceful shutdown (30s timeout)
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    log.Println("shutting down server...")
    if err := server.Shutdown(ctx); err != nil {
        log.Fatal("forced shutdown:", err)
    }
    log.Println("server exited")
}
```

### Connection Draining

Stop accepting new requests, finish in-flight requests.

```python
# Python (FastAPI)
import signal
import sys

def signal_handler(sig, frame):
    print("Graceful shutdown initiated")
    # Mark as not ready (fail readiness probe)
    app.state.ready = False
    # Wait for in-flight requests (up to 30s)
    time.sleep(30)
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
```

**Kubernetes behaviour**:
1. Pod marked for termination
2. Removed from service endpoints (no new connections)
3. SIGTERM sent to container
4. Grace period (default 30s)
5. SIGKILL if still running

### Timeout Before SIGKILL

```yaml
# deployment.yaml
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 60  # Wait 60s before SIGKILL
```

**Recommendation**: Set to max request duration + buffer (e.g., 60s for 30s max request).

## Rollback Strategies

### Revert to Previous Image

```bash
# Kubernetes: rollback to previous deployment
kubectl rollout undo deployment/myapp

# Or: rollback to specific revision
kubectl rollout history deployment/myapp
kubectl rollout undo deployment/myapp --to-revision=3

# Docker Swarm: update to previous image
docker service update --image myregistry/myapp:previous_sha myapp
```

### Database Migration Rollback

**Problem**: Code rollback with incompatible database schema.

**Solutions**:

1. **Backwards-compatible migrations** (expand/contract pattern):
   - Deploy 1: Add new column (nullable)
   - Deploy 2: Write to both old and new columns
   - Deploy 3: Migrate data
   - Deploy 4: Drop old column

2. **Separate migration deployment**:
   - Deploy 1: Run migration (forwards only)
   - Deploy 2: Deploy code (assumes new schema)
   - Rollback: Only code rollback (schema stays forwards)

**Never**: Auto-run migrations on startup (makes rollback impossible).

## Blue-Green Deployment

Two identical environments, switch traffic atomically.

```
Blue (current production) ← 100% traffic
Green (new version) ← 0% traffic

Deploy to Green → Test Green → Switch traffic

Green (new production) ← 100% traffic
Blue (old version) ← 0% traffic (kept for rollback)
```

### Kubernetes Example

```yaml
# Blue deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: myapp
        image: myregistry/myapp:v1.0.0

---
# Service (initially routes to blue)
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: blue  # Switch to "green" to flip traffic
  ports:
  - port: 80
    targetPort: 8080
```

**Switch traffic**:
```bash
kubectl patch service myapp -p '{"spec":{"selector":{"version":"green"}}}'
```

**Rollback**:
```bash
kubectl patch service myapp -p '{"spec":{"selector":{"version":"blue"}}}'
```

**Pros**: Instant rollback, full production testing before switch.
**Cons**: Double infrastructure cost.

## Canary Deployment

Gradual traffic shift (1% → 5% → 25% → 100%).

```
Version A: 100% traffic

Deploy Version B: 1% traffic → Monitor metrics

No errors → 5% traffic → Monitor

No errors → 25% traffic → Monitor

No errors → 100% traffic (promote)
```

### Kubernetes Example (Istio)

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: myapp
spec:
  hosts:
  - myapp
  http:
  - match:
    - headers:
        canary:
          exact: "true"  # Header-based routing
    route:
    - destination:
        host: myapp
        subset: v2
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 95  # 95% to stable
    - destination:
        host: myapp
        subset: v2
      weight: 5   # 5% to canary
```

**Metric-based promotion**:
```bash
# Monitor error rate, latency
if error_rate < 0.1% and p95_latency < 200ms:
    increase canary weight to 25%
else:
    rollback (set weight to 0%)
```

**Pros**: Low risk, gradual rollout, real production data.
**Cons**: Complex routing, requires metrics monitoring.

> **See also:** `reliability-patterns` for health check best practices (never check external deps in liveness), circuit breakers, and graceful degradation with feature flags. `durable-execution` for workflow-based deployment orchestration.
