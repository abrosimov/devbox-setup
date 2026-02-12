---
name: security-patterns
description: >
  Security patterns for backend (Go/Python), frontend (React/Next.js), and gRPC services.
  Covers three-tier severity model (CRITICAL/GUARDED/CONTEXT), OWASP Top 10 2025, injection
  prevention (SQL, command, path, SSTI, deserialisation), XSS three-layer defence, CSRF, CORS,
  CSP, security headers, JWT validation, password hashing, timing-safe comparisons, secure random,
  secrets management, gRPC transport/auth/streaming security, and dev/prod separation patterns.
  Triggers on: security, injection, SQL, XSS, CSRF, CORS, JWT, CSP, secrets, sanitise,
  authentication, password hashing, argon2, bcrypt, timing-safe, secure random, gRPC security,
  TLS, mTLS, OWASP, supply chain, SSTI, template injection, Content-Security-Policy,
  SameSite, dangerouslySetInnerHTML, postMessage, clickjacking, open redirect, cookie security,
  fail-open, fail-closed, security headers, HSTS, rate limiting, build tags, dev prod separation,
  IDOR, access control, privilege escalation, session management.
---

# Security Patterns

Three-tier severity model for secure coding across Go, Python, and frontend stacks.

## Table of Contents

- [Severity Model](#severity-model)
- [OWASP Top 10 2025](#owasp-top-10-2025)
- [Injection Prevention](#injection-prevention)
- [XSS Three-Layer Defence](#xss-three-layer-defence)
- [Cryptography and Secrets](#cryptography-and-secrets)
- [Authentication and Authorisation](#authentication-and-authorisation)
- [HTTP Security](#http-security)
- [Frontend Security](#frontend-security)
- [gRPC Security](#grpc-security)
- [Dev/Prod Separation Patterns](#devprod-separation-patterns)
- [Supply Chain Security](#supply-chain-security)
- [Security Checklists](#security-checklists)

---

## Severity Model

Every security pattern is classified into one of three tiers:

| Tier | Meaning | Action |
|------|---------|--------|
| **CRITICAL** | Never acceptable in any context (including dev/test) | Block in CI, reject in review |
| **GUARDED** | Acceptable in dev/test only, MUST be isolated from production | Use separation patterns (build tags, config, env checks) |
| **CONTEXT** | Depends on use case, requires judgment | Document the rationale |

### CRITICAL Examples

| Pattern | Language | Why |
|---------|----------|-----|
| `==` for token/key/hash comparison | All | Timing attack leaks secret length |
| `math/rand` for security tokens | Go | Predictable PRNG |
| `random` module for tokens | Python | Predictable PRNG |
| `eval()` / `exec()` with user input | Python | Arbitrary code execution |
| `pickle.load` on untrusted data | Python | Remote code execution |
| SQL string concatenation | All | SQL injection |
| Hardcoded production secrets | All | Credential exposure |
| Logging passwords/tokens | All | Credential leakage |
| `shell=True` with user input | Python | Command injection |
| `sh -c` with user input | Go | Command injection |

### GUARDED Examples

- **`grpc.WithInsecure()`** (Go) — safe with build tags (`//go:build` for non-prod)
- **`InsecureSkipVerify: true`** (Go) — safe with build tags
- **`verify=False`** (Python) — safe when config-driven (`if settings.DEBUG`)
- **`reflection.Register()`** (Go) — safe with env check (non-production guard)
- **`CORS: *`** (All) — safe in dev-only config
- **Verbose error details in responses** (All) — safe when config-driven
- **No rate limiting** (All) — safe in dev/test environments only

### CONTEXT Examples

| Pattern | OK When | Not OK When |
|---------|---------|-------------|
| `md5` | File checksums, cache keys | Password hashing, signatures |
| `random` module | UI jitter, shuffling display | Tokens, keys, nonces |
| No auth on endpoint | Public health checks, docs | Any data-returning endpoint |
| No CSRF protection | Stateless JWT-only APIs | Cookie-based session APIs |

---

## OWASP Top 10 2025

| # | Category | Key Prevention |
|---|----------|----------------|
| A01 | Broken Access Control | Authorisation checks on every request, IDOR prevention, default-deny |
| A02 | Security Misconfiguration | Secure defaults, disable debug in prod, security headers |
| A03 | Software Supply Chain Failures (NEW) | `govulncheck`, `pip-audit`, `npm audit`, lock files |
| A04 | Cryptographic Failures | Argon2id for passwords, TLS everywhere, `crypto/rand` |
| A05 | Injection | Parameterised queries, no `shell=True`, template sandboxing |
| A06 | Insecure Design | Threat modelling, fail-closed, least privilege |
| A07 | Authentication Failures | MFA, secure session management, timing-safe comparison |
| A08 | Data Integrity Failures | Signature verification, CI/CD pipeline security |
| A09 | Security Logging & Alerting Failures | Log security events, protect logs, no secrets in logs |
| A10 | Mishandling of Exceptional Conditions (NEW) | Fail-closed, default-deny, graceful degradation |

---

## Injection Prevention

### SQL Injection — CRITICAL

**Python:**
```python
# CRITICAL — string formatting
query = f"SELECT * FROM users WHERE id = '{user_id}'"

# SAFE — parameterised query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# SAFE — SQLAlchemy ORM
user = session.query(User).filter(User.id == user_id).first()

# SAFE — SQLAlchemy Core with bindparams
stmt = text("SELECT * FROM users WHERE id = :id").bindparams(id=user_id)
```

**Go:**
```go
// CRITICAL — string concatenation
query := fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID)

// SAFE — parameterised query
db.QueryContext(ctx, "SELECT * FROM users WHERE id = $1", userID)

// SAFE — prepared statement
stmt, err := db.PrepareContext(ctx, "SELECT * FROM users WHERE id = $1")
```

### Command Injection — CRITICAL

**Python:**
```python
# CRITICAL — shell=True with user input
subprocess.run(f"echo {user_input}", shell=True)

# CRITICAL — os.system
os.system(f"ls {directory}")

# SAFE — list arguments, no shell
subprocess.run(["echo", user_input], shell=False, check=True)

# SAFE — explicit argument list
subprocess.run(["ls", "-la", directory], shell=False, check=True)
```

**Go:**
```go
// CRITICAL — shell execution with user input
exec.Command("sh", "-c", "echo "+userInput).Run()

// SAFE — direct command, no shell
exec.Command("echo", userInput).Run()
```

### Path Traversal — CRITICAL

**Python:**
```python
from pathlib import Path

# CRITICAL — no validation
file_path = os.path.join(base_dir, user_input)

# SAFE — pathlib with strict resolution
base = Path(base_dir).resolve()
target = (base / user_input).resolve()
if not target.is_relative_to(base):
    raise ValueError("invalid path")
```

**Go:**
```go
// CRITICAL — no validation
filePath := filepath.Join(baseDir, userInput)

// SAFE — validate resolved path
realPath, err := filepath.Abs(filepath.Join(baseDir, userInput))
if err != nil {
    return err
}
realBase, _ := filepath.Abs(baseDir)
if !strings.HasPrefix(realPath, realBase+string(os.PathSeparator)) {
    return errors.New("invalid path: directory traversal attempt")
}
```

### Unsafe Deserialisation — CRITICAL

**Python:**
```python
# CRITICAL — pickle on untrusted data (RCE)
data = pickle.load(untrusted_file)

# CRITICAL — yaml.load without SafeLoader
data = yaml.load(untrusted_string)

# SAFE — yaml.safe_load
data = yaml.safe_load(untrusted_string)

# SAFE — JSON + Pydantic
validated = UserInput.model_validate_json(untrusted_string)
```

### SSTI (Server-Side Template Injection) — CRITICAL

**Python (Flask/Jinja2):**
```python
# CRITICAL — user input in template string
@app.route("/greet")
def greet():
    name = request.args.get("name")
    return render_template_string(f"Hello {name}")  # RCE via {{config}}

# SAFE — pass as variable
@app.route("/greet")
def greet():
    name = request.args.get("name")
    return render_template_string("Hello {{ name }}", name=name)

# SAFE — use template files (preferred)
@app.route("/greet")
def greet():
    return render_template("greet.html", name=request.args.get("name"))
```

Jinja2 sandboxing for untrusted templates:
```python
from jinja2 import SandboxedEnvironment

env = SandboxedEnvironment()
template = env.from_string(untrusted_template)
result = template.render(context)
```

### Allowlists Over Denylists

```python
# BAD — denylist (attackers find bypasses)
if "<script>" in user_input:
    raise ValueError("XSS detected")

# GOOD — allowlist
import re
if not re.match(r"^[a-zA-Z0-9_-]+$", user_input):
    raise ValueError("invalid characters")
```

> For input validation patterns (Pydantic, struct tags, boundary validation), see `validation` skill.

---

## XSS Three-Layer Defence

XSS prevention requires defence in depth across all three layers. Raw user input is never stored — the sanitised form IS the canonical stored form.

| Layer | Where | What | Tools |
|-------|-------|------|-------|
| 1 — Sanitise on input | Backend, before DB write | Strip dangerous HTML/JS | Go: `bluemonday`, Python: `nh3` |
| 2 — Encode on output | API response | Context-appropriate encoding | JSON encoding, HTML entity encoding |
| 3 — Encode on render | Frontend | Framework auto-escaping + DOMPurify for raw HTML | React JSX, DOMPurify |

If raw unsanitised content is needed (e.g. markdown source, admin audit), store in an explicit separate field with access controls.

### Layer 1 — Backend Sanitisation

**Go (bluemonday):**
```go
import "github.com/microcosmos-cc/bluemonday"

p := bluemonday.UGCPolicy()

func sanitiseUserContent(raw string) string {
    return p.Sanitize(raw)
}

func (s *Service) CreateComment(ctx context.Context, req CreateCommentRequest) error {
    req.Body = sanitiseUserContent(req.Body)
    return s.repo.Save(ctx, req)
}
```

**Python (nh3 — bleach is deprecated):**
```python
import nh3

def sanitise_user_content(raw: str) -> str:
    return nh3.clean(raw)

def create_comment(self, body: str) -> Comment:
    sanitised = sanitise_user_content(body)
    return self.__repo.save(Comment(body=sanitised))
```

### Layer 2 — API Response Encoding

JSON serialisation handles encoding automatically. Ensure you never inject raw HTML into JSON string values that were not sanitised at Layer 1.

### Layer 3 — Frontend Rendering

```typescript
// SAFE — React auto-escapes JSX expressions
function UserGreeting({ name }: { name: string }) {
  return <p>Hello, {name}</p>
}

// CRITICAL — unsanitised user input in dangerouslySetInnerHTML
function UserBio({ bio }: { bio: string }) {
  return <div dangerouslySetInnerHTML={{ __html: bio }} />
}

// SAFE — DOMPurify as last line of defence (content already sanitised at Layer 1)
import DOMPurify from 'dompurify'

function UserBio({ bio }: { bio: string }) {
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bio) }} />
}

// SAFE — markdown renderer instead of raw HTML
import ReactMarkdown from 'react-markdown'

function UserBio({ bio }: { bio: string }) {
  return <ReactMarkdown>{bio}</ReactMarkdown>
}
```

### URL Injection — CRITICAL

```typescript
// CRITICAL — javascript: protocol in href
function UserLink({ url }: { url: string }) {
  return <a href={url}>Visit</a>
}

// SAFE — validate protocol
function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}
```

---

## Cryptography and Secrets

### Password Hashing

**Preferred: Argon2id** (m=19456 KiB, t=2, p=1). **Fallback: bcrypt** (cost >= 10, 72-byte limit).

**Go:**
```go
import (
    "crypto/rand"
    "crypto/subtle"

    "golang.org/x/crypto/argon2"
    "golang.org/x/crypto/bcrypt"
)

func hashPasswordArgon2(password string) ([]byte, []byte, error) {
    salt := make([]byte, 16)
    if _, err := rand.Read(salt); err != nil {
        return nil, nil, fmt.Errorf("generate salt: %w", err)
    }
    hash := argon2.IDKey([]byte(password), salt, 2, 19456, 1, 32)
    return hash, salt, nil
}

func hashPasswordBcrypt(password string) ([]byte, error) {
    return bcrypt.GenerateFromPassword([]byte(password), 10)
}
```

**Python:**
```python
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return ph.verify(stored_hash, password)
    except Exception:
        return False
```

### Timing-Safe Comparisons — CRITICAL

Never use `==` for tokens, keys, hashes, or any secret material.

**Go:**
```go
import "crypto/subtle"

// CRITICAL — timing attack
if token == expectedToken { }

// SAFE — constant-time comparison
if subtle.ConstantTimeCompare([]byte(token), []byte(expectedToken)) == 1 { }
```

**Python:**
```python
import hmac

# CRITICAL — timing attack
if token == expected_token: ...

# SAFE — constant-time comparison
if hmac.compare_digest(token, expected_token): ...
```

### Secure Random — CRITICAL

**Go:**
```go
import "crypto/rand"

// CRITICAL — predictable PRNG
import "math/rand"
token := rand.Int63()

// SAFE — cryptographic random
b := make([]byte, 32)
if _, err := rand.Read(b); err != nil {
    return fmt.Errorf("generate token: %w", err)
}
token := base64.URLEncoding.EncodeToString(b)
```

**Python:**
```python
import secrets

# CRITICAL — predictable PRNG
import random
token = random.randint(0, 999999)

# SAFE — cryptographic random
token = secrets.token_urlsafe(32)
otp = secrets.randbelow(1000000)
```

### JWT Validation

Verify signature, enforce algorithm (prevent `alg:none`), check expiry, validate claims.

**Go:**
```go
import "github.com/golang-jwt/jwt/v5"

func validateJWT(tokenString string, publicKey any) (*jwt.Token, error) {
    token, err := jwt.Parse(tokenString,
        func(token *jwt.Token) (any, error) {
            if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
                return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
            }
            return publicKey, nil
        },
        jwt.WithValidMethods([]string{"RS256"}),
        jwt.WithExpirationRequired(),
    )
    if err != nil {
        return nil, fmt.Errorf("parse JWT: %w", err)
    }
    return token, nil
}
```

**Python:**
```python
import jwt

def validate_jwt(token: str, public_key: str) -> dict:
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"require": ["exp", "iat", "sub"]},
    )
```

### Secrets Management

```python
# CRITICAL — hardcoded secret
API_KEY = "sk-1234567890abcdef"

# SAFE — environment variable
API_KEY = os.environ["API_KEY"]
```

```go
// CRITICAL — hardcoded
const APIKey = "sk-1234567890abcdef"

// SAFE — environment variable
apiKey := os.Getenv("API_KEY")
if apiKey == "" {
    log.Fatal("API_KEY not set")
}
```

### Never Log Secrets — CRITICAL

```python
# CRITICAL — logging password
logger.info(f"User login: {username}, password: {password}")

# SAFE — redact sensitive fields
safe_headers = {k: v for k, v in request.headers.items()
                if k.lower() not in ("authorization", "cookie")}
```

```go
// CRITICAL
log.Printf("API call with key: %s", apiKey)

// SAFE
log.Printf("API call with key: [REDACTED]")
```

---

## Authentication and Authorisation

### Fail-Closed / Default-Deny — OWASP A10

```go
// CRITICAL — fail-open: error skips auth
func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, err := authenticate(r)
        if err != nil {
            next.ServeHTTP(w, r)  // WRONG: unauthenticated request proceeds
            return
        }
        ctx := context.WithValue(r.Context(), userKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// SAFE — fail-closed: error blocks request
func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, err := authenticate(r)
        if err != nil {
            http.Error(w, "unauthorised", http.StatusUnauthorized)
            return
        }
        ctx := context.WithValue(r.Context(), userKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

**Python:**
```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            raise UnauthorisedError("authentication required")
        return f(*args, **kwargs)
    return decorated

def require_role(role: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.has_role(role):
                raise ForbiddenError(f"role '{role}' required")
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Resource-Level Authorisation (IDOR Prevention)

```python
def get_document(doc_id: str) -> Document:
    doc = document_repo.find_by_id(doc_id)
    if doc is None:
        raise NotFoundError(f"document {doc_id} not found")

    if doc.owner_id != current_user.id:
        raise ForbiddenError("access denied")

    return doc
```

### Token Storage (Frontend)

| Storage | XSS Risk | CSRF Risk | Recommendation |
|---------|----------|-----------|----------------|
| `localStorage` | Vulnerable | Safe | **Avoid** |
| `sessionStorage` | Vulnerable | Safe | **Avoid** |
| `httpOnly` cookie | Safe | Needs SameSite | **Preferred** |

```typescript
// CRITICAL — JWT in localStorage (accessible to XSS)
localStorage.setItem('token', jwt)

// SAFE — httpOnly cookie (not accessible to JavaScript)
// Server sets: Set-Cookie: token=jwt; HttpOnly; Secure; SameSite=Lax; Path=/
// Client sends automatically:
fetch('/api/data', { credentials: 'include' })
```

### Environment Variables (Next.js)

```typescript
// CRITICAL — secret in client-visible env var
NEXT_PUBLIC_API_SECRET=sk-1234567890  // Bundled into client JS!

// SAFE — server-only env var
API_SECRET=sk-1234567890

// SAFE — only public values use NEXT_PUBLIC_ prefix
NEXT_PUBLIC_API_URL=https://api.example.com
```

### Auth State — Server-Side Preferred

```typescript
// SAFE — server-side auth check (Next.js middleware)
export function middleware(request: NextRequest) {
  const token = request.cookies.get('session')
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}
```

---

## HTTP Security

### Timeouts — CRITICAL (missing timeouts)

```python
# CRITICAL — no timeout (hangs forever)
response = requests.get(url)

# SAFE — explicit timeout (connect, read)
response = requests.get(url, timeout=(5, 30))
```

```go
// CRITICAL — no timeout
client := &http.Client{}

// SAFE — explicit timeout
client := &http.Client{Timeout: 30 * time.Second}
```

### TLS Verification — GUARDED

```python
# GUARDED — only in dev with config guard
requests.get(url, verify=not settings.DEBUG)

# SAFE — verify enabled (default)
requests.get(url, verify=True)
```

### SSRF Prevention

```python
from urllib.parse import urlparse
import ipaddress

ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}

def fetch_url(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"host not allowed: {parsed.hostname}")

    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback:
            raise ValueError("internal addresses not allowed")
    except ValueError:
        pass

    return requests.get(url, timeout=(5, 30)).content
```

### Security Headers (Full Set)

**Next.js middleware example:**
```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const response = NextResponse.next()

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self'",
    "connect-src 'self' https://api.example.com",
    "frame-ancestors 'self'",
    "form-action 'self'",
    "base-uri 'self'",
  ].join('; ')

  response.headers.set('Content-Security-Policy', csp)
  response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')

  return response
}
```

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | See above | Controls resource loading sources |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing |
| `X-Frame-Options` | `DENY` or `SAMEORIGIN` | Prevents clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer info leakage |
| `Permissions-Policy` | `camera=(), microphone=()` | Disables browser features |

---

## Frontend Security

### CSRF Prevention

**SameSite Cookies:**

| `SameSite` Value | Cross-Site Subrequests | Top-Level Navigation | When to Use |
|------------------|----------------------|---------------------|-------------|
| `Strict` | Not sent | Not sent | Sensitive operations (banking) |
| `Lax` | Not sent | Sent (GET only) | Default for most apps |
| `None` | Sent | Sent | Third-party integrations (requires `Secure`) |

**Anti-CSRF for custom API routes:**
```typescript
// SAFE — verify Origin header
export async function POST(request: Request) {
  const origin = request.headers.get('origin')
  if (origin !== process.env.ALLOWED_ORIGIN) {
    return new Response('Forbidden', { status: 403 })
  }
  const data = await request.json()
  await updateUser(data)
}

// SAFE — custom header check (non-simple requests trigger preflight)
fetch('/api/users', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
  body: JSON.stringify(data),
})
```

### CORS — GUARDED (`*` with credentials)

```typescript
// GUARDED — wildcard origin (dev only)
Access-Control-Allow-Origin: *

// CRITICAL — reflecting Origin without validation
const origin = request.headers.get('origin')
response.headers.set('Access-Control-Allow-Origin', origin!)

// SAFE — allowlist validation
const ALLOWED_ORIGINS = ['https://app.example.com', 'https://admin.example.com']
const origin = request.headers.get('origin')
if (origin && ALLOWED_ORIGINS.includes(origin)) {
  response.headers.set('Access-Control-Allow-Origin', origin)
  response.headers.set('Access-Control-Allow-Credentials', 'true')
}
```

### Iframe Security

```typescript
// Clickjacking prevention — CSP approach (preferred)
Content-Security-Policy: frame-ancestors 'self'

// Embedding untrusted content — sandbox
<iframe
  src={userProvidedUrl}
  sandbox="allow-scripts allow-same-origin"
  referrerPolicy="no-referrer"
/>
```

### postMessage Security

```typescript
// CRITICAL — no origin check
window.addEventListener('message', (event) => {
  processData(event.data)
})

// SAFE — validate origin
window.addEventListener('message', (event) => {
  if (event.origin !== 'https://trusted.example.com') return
  processData(event.data)
})
```

### Open Redirect Prevention

```typescript
// CRITICAL — redirect to user-controlled URL
router.push(returnTo)

// SAFE — validate against own origin only
function handleLogin(returnTo: string) {
  try {
    const url = new URL(returnTo, window.location.origin)
    if (url.origin !== window.location.origin) {
      router.push('/dashboard')
      return
    }
    router.push(url.pathname)
  } catch {
    router.push('/dashboard')
  }
}
```

---

## gRPC Security

### Transport Security (TLS/mTLS) — GUARDED

Insecure transport is acceptable in dev/test ONLY with proper separation.

**Go — build tag separation:**
```go
// file: grpc_transport_prod.go
//go:build prod

package server

func transportCredentials() grpc.ServerOption {
    creds, err := credentials.NewServerTLSFromFile("cert.pem", "key.pem")
    if err != nil {
        log.Fatal().Err(err).Msg("load TLS credentials")
    }
    return grpc.Creds(creds)
}
```

```go
// file: grpc_transport_dev.go
//go:build !prod

package server

func transportCredentials() grpc.ServerOption {
    return grpc.Creds(insecure.NewCredentials())
}
```

**Go client — build tag separation:**
```go
// file: grpc_dial_prod.go
//go:build prod

func dialOption() grpc.DialOption {
    return grpc.WithTransportCredentials(credentials.NewTLS(&tls.Config{}))
}
```

```go
// file: grpc_dial_dev.go
//go:build !prod

func dialOption() grpc.DialOption {
    return grpc.WithTransportCredentials(insecure.NewCredentials())
}
```

**Python — config-driven:**
```python
def create_channel(target: str, *, secure: bool = True) -> grpc.Channel:
    if secure:
        credentials = grpc.ssl_channel_credentials(
            root_certificates=open("ca.pem", "rb").read(),
        )
        return grpc.secure_channel(target, credentials)
    return grpc.insecure_channel(target)
```

### Auth Interceptors

**Go — unary interceptor:**
```go
func authUnaryInterceptor(
    ctx context.Context,
    req any,
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (any, error) {
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.Unauthenticated, "missing metadata")
    }

    tokens := md.Get("authorization")
    if len(tokens) == 0 {
        return nil, status.Error(codes.Unauthenticated, "missing authorization")
    }

    user, err := validateToken(tokens[0])
    if err != nil {
        return nil, status.Error(codes.Unauthenticated, "invalid token")
    }

    ctx = context.WithValue(ctx, userKey, user)
    return handler(ctx, req)
}
```

**Go — stream interceptor:**
```go
func authStreamInterceptor(
    srv any,
    ss grpc.ServerStream,
    info *grpc.StreamServerInfo,
    handler grpc.StreamHandler,
) error {
    md, ok := metadata.FromIncomingContext(ss.Context())
    if !ok {
        return status.Error(codes.Unauthenticated, "missing metadata")
    }

    tokens := md.Get("authorization")
    if len(tokens) == 0 {
        return status.Error(codes.Unauthenticated, "missing authorization")
    }

    user, err := validateToken(tokens[0])
    if err != nil {
        return status.Error(codes.Unauthenticated, "invalid token")
    }

    wrapped := &authStream{ServerStream: ss, ctx: context.WithValue(ss.Context(), userKey, user)}
    return handler(srv, wrapped)
}
```

**Python:**
```python
class AuthInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        token = metadata.get("authorization")
        if not token:
            return grpc.unary_unary_rpc_method_handler(
                lambda req, ctx: ctx.abort(grpc.StatusCode.UNAUTHENTICATED, "missing token")
            )
        return continuation(handler_call_details)
```

### Metadata Sanitisation

Sanitise gRPC metadata before logging or forwarding to downstream services:

```go
func sanitiseMetadata(md metadata.MD) metadata.MD {
    safe := metadata.MD{}
    sensitive := map[string]bool{
        "authorization": true,
        "cookie":        true,
        "x-api-key":     true,
    }
    for k, v := range md {
        if sensitive[strings.ToLower(k)] {
            safe.Set(k, "[REDACTED]")
        } else {
            safe[k] = v
        }
    }
    return safe
}
```

### Streaming Limits

```go
server := grpc.NewServer(
    grpc.MaxRecvMsgSize(4 * 1024 * 1024),  // 4 MiB max message
    grpc.MaxSendMsgSize(4 * 1024 * 1024),
)
```

For streaming RPCs, enforce message count limits and deadlines:
```go
func (s *Server) WatchOrders(req *pb.WatchRequest, stream pb.OrderService_WatchOrdersServer) error {
    ctx := stream.Context()
    ctx, cancel := context.WithTimeout(ctx, 30*time.Minute)
    defer cancel()

    msgCount := 0
    const maxMessages = 10000

    for {
        select {
        case <-ctx.Done():
            return status.Error(codes.DeadlineExceeded, "stream timeout")
        case event := <-s.events:
            if msgCount >= maxMessages {
                return status.Error(codes.ResourceExhausted, "message limit reached")
            }
            if err := stream.Send(event); err != nil {
                return fmt.Errorf("send event: %w", err)
            }
            msgCount++
        }
    }
}
```

### Error Info Leakage

Use `status.Error` in gRPC handlers, never `fmt.Errorf` or raw error strings:

```go
// CRITICAL — leaks internal details to client
func (s *Server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    user, err := s.repo.Get(ctx, req.GetId())
    if err != nil {
        return nil, fmt.Errorf("database query failed: %w", err)  // Exposes DB details
    }
    return user, nil
}

// SAFE — structured gRPC status
func (s *Server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    user, err := s.repo.Get(ctx, req.GetId())
    if err != nil {
        if errors.Is(err, storage.ErrNotFound) {
            return nil, status.Error(codes.NotFound, "user not found")
        }
        s.logger.Error().Err(err).Str("user_id", req.GetId()).Msg("get user failed")
        return nil, status.Error(codes.Internal, "internal error")
    }
    return user, nil
}
```

### Reflection Service — GUARDED

```go
import "google.golang.org/grpc/reflection"

if os.Getenv("ENV") != "production" {
    reflection.Register(server)
}
```

### Interceptor Ordering

Order matters. Recovery must be outermost, auth before business logic:

```go
server := grpc.NewServer(
    grpc.ChainUnaryInterceptor(
        recoveryInterceptor,    // 1. Catch panics (outermost)
        authUnaryInterceptor,   // 2. Authentication
        rateLimitInterceptor,   // 3. Rate limiting (see go-concurrency skill for implementation)
        loggingInterceptor,     // 4. Request logging
        tracingInterceptor,     // 5. Distributed tracing
    ),
)
```

### Proto Validation

Proto types alone are NOT sufficient for validation. Use `protovalidate` (buf) for field-level constraints (complements `api-design-proto` skill which covers message design):

```protobuf
import "buf/validate/validate.proto";

message CreateUserRequest {
  string email = 1 [(buf.validate.field).string.email = true];
  string name = 2 [(buf.validate.field).string = {min_len: 1, max_len: 100}];
  int32 age = 3 [(buf.validate.field).int32 = {gte: 0, lte: 150}];
}
```

```go
import "github.com/bufbuild/protovalidate-go"

validator, _ := protovalidate.New()

func (s *Server) CreateUser(ctx context.Context, req *pb.CreateUserRequest) (*pb.User, error) {
    if err := validator.Validate(req); err != nil {
        return nil, status.Error(codes.InvalidArgument, err.Error())
    }
    // proceed with validated request
}
```

---

## Dev/Prod Separation Patterns

How to safely use GUARDED patterns in development without them leaking into production.

### Go Build Tags

```go
// file: config_prod.go
//go:build prod

package config

const (
    TLSEnabled     = true
    DebugMode      = false
    VerboseErrors  = false
)

// file: config_dev.go
//go:build !prod

package config

const (
    TLSEnabled     = false
    DebugMode      = true
    VerboseErrors  = true
)
```

Build: `go build -tags prod ./...`

### Python Config-Driven

```python
import os

class Settings:
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = ENV != "production"
    TLS_VERIFY: bool = ENV == "production"
    VERBOSE_ERRORS: bool = ENV != "production"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

settings = Settings()
```

### Environment Check Pattern

```go
func isProduction() bool {
    return os.Getenv("ENV") == "production"
}

func corsConfig() CORSConfig {
    if isProduction() {
        return CORSConfig{AllowedOrigins: []string{"https://app.example.com"}}
    }
    return CORSConfig{AllowedOrigins: []string{"*"}}
}
```

### Secure Defaults (Flask/Django)

```python
# Flask
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Django
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

---

## Supply Chain Security

OWASP 2025 A03 — Software Supply Chain Failures.

### Dependency Scanning

```bash
# Go
govulncheck ./...

# Python
pip-audit

# Node.js
npm audit
pnpm audit
```

### Lock Files

Always commit lock files (`go.sum`, `poetry.lock` / `requirements.txt` with hashes, `pnpm-lock.yaml`).

### Principles

- Pin exact versions in production
- Review new dependencies before adding (check maintenance, download counts, contributors)
- Use `--frozen-lockfile` in CI (`pnpm install --frozen-lockfile`)
- Audit periodically, not just at install time

---

## Security Checklists

### Backend Checklist

- [ ] **CRITICAL** — No SQL string concatenation; parameterised queries only
- [ ] **CRITICAL** — No `shell=True` / `sh -c` with user input
- [ ] **CRITICAL** — No `pickle.load` / `yaml.load` on untrusted data
- [ ] **CRITICAL** — No `==` for token/key/hash comparison; use constant-time
- [ ] **CRITICAL** — No `math/rand` / `random` for security tokens; use `crypto/rand` / `secrets`
- [ ] **CRITICAL** — No hardcoded production secrets; env vars or secret manager
- [ ] **CRITICAL** — No secrets in logs; redact authorization/cookie headers
- [ ] **CRITICAL** — No `render_template_string` with user input (SSTI)
- [ ] Timeouts on all external HTTP requests
- [ ] TLS verification enabled in production
- [ ] SSRF prevention for user-controlled URLs
- [ ] Path traversal prevention on file operations
- [ ] Auth check on every protected endpoint (fail-closed)
- [ ] Resource-level authorisation (IDOR prevention)
- [ ] Password hashing with Argon2id or bcrypt (never MD5/SHA for passwords)
- [ ] JWT: verify signature, enforce algorithm, check expiry
- [ ] XSS Layer 1: sanitise user HTML input before storage (bluemonday / nh3)
- [ ] Input validated at system boundaries (see `validation` skill)
- [ ] Supply chain: `govulncheck` / `pip-audit` in CI
- [ ] GUARDED patterns isolated with build tags / config / env checks

### Frontend Checklist

- [ ] **CRITICAL** — No `dangerouslySetInnerHTML` with unsanitised input
- [ ] **CRITICAL** — No secrets in `NEXT_PUBLIC_` env vars
- [ ] **CRITICAL** — URLs validated against `javascript:` protocol
- [ ] CSP headers configured with nonce-based `script-src`
- [ ] All security headers set (HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- [ ] `SameSite` attribute on cookies (`Lax` or `Strict`)
- [ ] State-changing API routes verify Origin or custom header (CSRF)
- [ ] JWT/session tokens in `httpOnly` cookies, not `localStorage`
- [ ] Server-side auth checks in middleware
- [ ] `frame-ancestors` CSP or `X-Frame-Options` set
- [ ] `postMessage` handlers validate `event.origin`
- [ ] Redirect URLs validated against own origin
- [ ] CORS allowlist, not wildcard with credentials
- [ ] XSS Layer 3: DOMPurify for any rendered HTML
- [ ] Supply chain: `npm audit` / `pnpm audit` in CI

### gRPC Checklist

- [ ] **GUARDED** — TLS/mTLS in production; insecure only with build tags / config guard
- [ ] **GUARDED** — Reflection service disabled in production (env check)
- [ ] Auth interceptor on all non-public RPCs
- [ ] Stream interceptors for auth (not just unary)
- [ ] `status.Error` for client responses, not `fmt.Errorf`
- [ ] Metadata sanitised before logging (redact auth headers)
- [ ] `MaxRecvMsgSize` / `MaxSendMsgSize` limits set
- [ ] Streaming RPCs have message count limits and deadlines
- [ ] Interceptor order: recovery -> auth -> rate-limit -> logging -> tracing
- [ ] Proto validation with `protovalidate` (proto types alone insufficient)
- [ ] CORS middleware for gRPC-Web/gRPC-Gateway (if browser clients)
- [ ] GUARDED patterns isolated with build tags / config / env checks
