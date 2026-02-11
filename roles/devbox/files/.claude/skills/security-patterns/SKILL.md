---
name: security-patterns
description: >
  Security patterns for input validation, secrets handling, and common vulnerability prevention
  in both backend (Python/Go) and frontend (React/Next.js). Covers SQL injection, command injection,
  XSS, CSRF, CORS, JWT, CSP, cookie security, and authentication.
  Triggers on: security, injection, SQL, XSS, CSRF, CORS, JWT, CSP, secrets, validation, sanitize,
  authentication, Content-Security-Policy, SameSite, dangerouslySetInnerHTML, postMessage,
  clickjacking, open redirect, cookie security.
---

# Security Patterns

Common security patterns and vulnerability prevention for both Python and Go.

## OWASP Top 10 Quick Reference

| Vulnerability | Prevention |
|---------------|------------|
| Injection (SQL, Command, etc.) | Parameterized queries, avoid shell=True |
| Broken Authentication | Secure session management, MFA |
| Sensitive Data Exposure | Encryption, no secrets in logs |
| XXE | Disable external entities |
| Broken Access Control | Authorization checks on every request |
| Security Misconfiguration | Secure defaults, disable debug |
| XSS | Output encoding, CSP headers |
| Insecure Deserialization | Avoid pickle/yaml.load on untrusted data |
| Known Vulnerabilities | Keep dependencies updated |
| Insufficient Logging | Log security events, protect logs |

## SQL Injection Prevention

### Python

```python
# ❌ VULNERABLE — string formatting
query = f"SELECT * FROM users WHERE id = '{user_id}'"
cursor.execute(query)

# ❌ VULNERABLE — .format()
query = "SELECT * FROM users WHERE id = '{}'".format(user_id)
cursor.execute(query)

# ❌ VULNERABLE — % formatting
query = "SELECT * FROM users WHERE id = '%s'" % user_id
cursor.execute(query)

# ✅ SAFE — parameterized query
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ✅ SAFE — SQLAlchemy ORM
user = session.query(User).filter(User.id == user_id).first()

# ✅ SAFE — SQLAlchemy Core with bindparams
stmt = text("SELECT * FROM users WHERE id = :id").bindparams(id=user_id)
```

### Go

```go
// ❌ VULNERABLE — string concatenation
query := "SELECT * FROM users WHERE id = '" + userID + "'"
db.Query(query)

// ❌ VULNERABLE — fmt.Sprintf
query := fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID)
db.Query(query)

// ✅ SAFE — parameterized query
db.Query("SELECT * FROM users WHERE id = $1", userID)

// ✅ SAFE — prepared statement
stmt, _ := db.Prepare("SELECT * FROM users WHERE id = $1")
stmt.Query(userID)
```

## Command Injection Prevention

### Python

```python
import subprocess
import shlex

# ❌ VULNERABLE — shell=True with user input
subprocess.run(f"echo {user_input}", shell=True)

# ❌ VULNERABLE — os.system
os.system(f"ls {directory}")

# ✅ SAFE — list arguments, no shell
subprocess.run(["echo", user_input], shell=False)

# ✅ SAFE — shlex.split for complex commands
subprocess.run(shlex.split(f"ls -la"), shell=False)

# ✅ SAFE — explicit argument list
subprocess.run(["ls", "-la", directory], shell=False, check=True)
```

### Go

```go
// ❌ VULNERABLE — shell execution with user input
exec.Command("sh", "-c", "echo "+userInput).Run()

// ✅ SAFE — direct command, no shell
exec.Command("echo", userInput).Run()

// ✅ SAFE — explicit arguments
cmd := exec.Command("ls", "-la", directory)
cmd.Run()
```

## Path Traversal Prevention

### Python

```python
import os

# ❌ VULNERABLE — no validation
file_path = os.path.join(base_dir, user_input)
with open(file_path) as f:
    return f.read()

# ✅ SAFE — validate resolved path
file_path = os.path.join(base_dir, user_input)
real_path = os.path.realpath(file_path)
real_base = os.path.realpath(base_dir)

if not real_path.startswith(real_base + os.sep):
    raise ValueError("Invalid path: directory traversal attempt")

with open(real_path) as f:
    return f.read()

# ✅ SAFE — pathlib with strict resolution
from pathlib import Path

base = Path(base_dir).resolve()
target = (base / user_input).resolve()

if not target.is_relative_to(base):
    raise ValueError("Invalid path")
```

### Go

```go
// ❌ VULNERABLE — no validation
filePath := filepath.Join(baseDir, userInput)
data, _ := os.ReadFile(filePath)

// ✅ SAFE — validate resolved path
filePath := filepath.Join(baseDir, userInput)
realPath, err := filepath.Abs(filePath)
if err != nil {
    return err
}

realBase, _ := filepath.Abs(baseDir)
if !strings.HasPrefix(realPath, realBase+string(os.PathSeparator)) {
    return errors.New("invalid path: directory traversal attempt")
}

data, err := os.ReadFile(realPath)
```

## Unsafe Deserialization Prevention

### Python

```python
import pickle
import yaml
import json

# ❌ VULNERABLE — pickle on untrusted data (RCE!)
data = pickle.load(untrusted_file)

# ❌ VULNERABLE — yaml.load without SafeLoader
data = yaml.load(untrusted_string)

# ✅ SAFE — yaml.safe_load
data = yaml.safe_load(untrusted_string)

# ✅ SAFE — JSON for untrusted data
data = json.loads(untrusted_string)

# ✅ SAFE — Pydantic for validation
from pydantic import BaseModel

class UserInput(BaseModel):
    name: str
    email: str

validated = UserInput.model_validate_json(untrusted_string)
```

### Go

```go
// ✅ SAFE — encoding/json (no code execution risk)
var data UserInput
json.Unmarshal(untrustedBytes, &data)

// ✅ SAFE — encoding/gob (safer than pickle, but validate source)
dec := gob.NewDecoder(reader)
dec.Decode(&data)
```

## Secrets Management

### Never Hardcode

```python
# ❌ VULNERABLE — hardcoded secret
API_KEY = "sk-1234567890abcdef"

# ❌ VULNERABLE — in config file committed to git
config = {"api_key": "sk-1234567890abcdef"}

# ✅ SAFE — environment variable
import os
API_KEY = os.environ["API_KEY"]

# ✅ SAFE — with default for development
API_KEY = os.environ.get("API_KEY", "dev-only-key")
```

```go
// ❌ VULNERABLE — hardcoded
const APIKey = "sk-1234567890abcdef"

// ✅ SAFE — environment variable
apiKey := os.Getenv("API_KEY")
if apiKey == "" {
    log.Fatal("API_KEY not set")
}
```

### Never Log Secrets

```python
# ❌ VULNERABLE — logging password
logger.info(f"User login: {username}, password: {password}")

# ❌ VULNERABLE — logging full request with auth header
logger.debug(f"Request: {request.headers}")

# ✅ SAFE — redact sensitive fields
logger.info(f"User login: {username}, password: [REDACTED]")

# ✅ SAFE — selective header logging
safe_headers = {k: v for k, v in request.headers.items()
                if k.lower() not in ("authorization", "cookie")}
logger.debug(f"Request headers: {safe_headers}")
```

```go
// ❌ VULNERABLE
log.Printf("API call with key: %s", apiKey)

// ✅ SAFE
log.Printf("API call with key: [REDACTED]")
```

## Input Validation

### At System Boundaries

```python
from pydantic import BaseModel, Field, field_validator

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(ge=0, le=150)

    @field_validator("name")
    @classmethod
    def name_must_not_contain_script(cls, v: str) -> str:
        if "<script" in v.lower():
            raise ValueError("Invalid characters in name")
        return v
```

```go
type CreateUserRequest struct {
    Name  string `json:"name" validate:"required,min=1,max=100"`
    Email string `json:"email" validate:"required,email"`
    Age   int    `json:"age" validate:"gte=0,lte=150"`
}

// Use validator
validate := validator.New()
if err := validate.Struct(req); err != nil {
    return fmt.Errorf("validation failed: %w", err)
}
```

### Allowlists Over Denylists

```python
# ❌ BAD — denylist (attackers find bypasses)
if "<script>" in user_input:
    raise ValueError("XSS detected")

# ✅ GOOD — allowlist
import re
if not re.match(r"^[a-zA-Z0-9_-]+$", user_input):
    raise ValueError("Invalid characters")

# ✅ GOOD — enum validation
from enum import Enum

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

status = Status(user_input)  # Raises if invalid
```

## HTTP Security

### Timeouts

```python
import requests

# ❌ VULNERABLE — no timeout (hangs forever)
response = requests.get(url)

# ✅ SAFE — explicit timeout (connect, read)
response = requests.get(url, timeout=(5, 30))
```

```go
// ❌ VULNERABLE — no timeout
client := &http.Client{}
resp, _ := client.Get(url)

// ✅ SAFE — explicit timeout
client := &http.Client{
    Timeout: 30 * time.Second,
}
resp, _ := client.Get(url)
```

### SSRF Prevention

```python
from urllib.parse import urlparse

ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}

def fetch_url(url: str) -> bytes:
    parsed = urlparse(url)

    # ❌ VULNERABLE — no host validation
    # return requests.get(url).content

    # ✅ SAFE — allowlist validation
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host not allowed: {parsed.hostname}")

    # Also check for internal IPs
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback:
            raise ValueError("Internal addresses not allowed")
    except ValueError:
        pass  # hostname, not IP

    return requests.get(url, timeout=(5, 30)).content
```

### TLS Verification

```python
# ❌ VULNERABLE — disabling TLS verification
requests.get(url, verify=False)

# ✅ SAFE — verify enabled (default)
requests.get(url, verify=True)

# ✅ SAFE — custom CA bundle
requests.get(url, verify="/path/to/ca-bundle.crt")
```

## Authentication & Authorisation

### Check on Every Request

```python
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            raise UnauthorisedError("Authentication required")
        return f(*args, **kwargs)
    return decorated


def require_role(role: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.has_role(role):
                raise ForbiddenError(f"Role '{role}' required")
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.route("/admin/users")
@require_auth
@require_role("admin")
def list_users():
    return users_service.list_all()
```

### Resource-Level Authorisation

```python
def get_document(doc_id: str) -> Document:
    doc = document_repo.find_by_id(doc_id)
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found")

    # ❌ VULNERABLE — no ownership check (IDOR)
    # return doc

    # ✅ SAFE — verify ownership
    if doc.owner_id != current_user.id:
        raise ForbiddenError("Access denied")

    return doc
```

## Secure Defaults

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

## Security Review Checklist

### Input Handling
- [ ] All user input validated at system boundary
- [ ] Allowlists used instead of denylists
- [ ] SQL queries use parameterized statements
- [ ] Commands use list arguments, not shell=True
- [ ] File paths validated against traversal

### Secrets
- [ ] No hardcoded secrets in code
- [ ] Secrets not logged
- [ ] Environment variables or secret manager used
- [ ] .env files in .gitignore

### Authentication
- [ ] Auth check on every protected endpoint
- [ ] Resource-level authorisation (IDOR prevention)
- [ ] Session cookies are Secure, HttpOnly, SameSite

### HTTP
- [ ] Timeouts on all external requests
- [ ] TLS verification enabled
- [ ] SSRF prevention for user-controlled URLs

### Serialisation
- [ ] No pickle.load on untrusted data
- [ ] yaml.safe_load used, not yaml.load
- [ ] JSON preferred for untrusted input

---

## Frontend Security Patterns

Security patterns specific to React, Next.js, and browser-based applications.

---

## XSS Prevention

### React's Built-in Protection

React escapes JSX expressions by default — string content is safe:

```typescript
// ✅ SAFE — React auto-escapes
function UserGreeting({ name }: { name: string }) {
  return <p>Hello, {name}</p>
}
// Even if name = "<script>alert('xss')</script>", it renders as text
```

### dangerouslySetInnerHTML

```typescript
// ❌ VULNERABLE — user input rendered as HTML
function UserBio({ bio }: { bio: string }) {
  return <div dangerouslySetInnerHTML={{ __html: bio }} />
}

// ✅ SAFE — sanitise with DOMPurify
import DOMPurify from 'dompurify'

function UserBio({ bio }: { bio: string }) {
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bio) }} />
}

// ✅ SAFE — use a markdown renderer (e.g., react-markdown) instead of raw HTML
import ReactMarkdown from 'react-markdown'

function UserBio({ bio }: { bio: string }) {
  return <ReactMarkdown>{bio}</ReactMarkdown>
}
```

### URL Injection

```typescript
// ❌ VULNERABLE — javascript: protocol in href
function UserLink({ url }: { url: string }) {
  return <a href={url}>Visit</a>
}
// Attacker sets url = "javascript:alert('xss')"

// ✅ SAFE — validate protocol
function UserLink({ url }: { url: string }) {
  const safeUrl = /^https?:\/\//i.test(url) ? url : '#'
  return <a href={safeUrl}>Visit</a>
}

// ✅ SAFE — use URL constructor for validation
function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}
```

### Content-Security-Policy (CSP)

```typescript
// next.config.ts — CSP headers
const cspHeader = `
  default-src 'self';
  script-src 'self' 'nonce-{nonce}';
  style-src 'self' 'unsafe-inline';
  img-src 'self' blob: data:;
  font-src 'self';
  connect-src 'self' https://api.example.com;
  frame-ancestors 'self';
  form-action 'self';
  base-uri 'self';
`

// In middleware.ts for Next.js
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const response = NextResponse.next()

  response.headers.set(
    'Content-Security-Policy',
    cspHeader.replace(/{nonce}/g, nonce).replace(/\n/g, '')
  )

  return response
}
```

| CSP Directive | Purpose | Recommended Value |
|---------------|---------|-------------------|
| `default-src` | Fallback for all resource types | `'self'` |
| `script-src` | JavaScript sources | `'self' 'nonce-{nonce}'` |
| `style-src` | CSS sources | `'self' 'unsafe-inline'` (Tailwind needs inline) |
| `img-src` | Image sources | `'self' blob: data:` |
| `connect-src` | Fetch/XHR/WebSocket destinations | `'self' https://api.example.com` |
| `frame-ancestors` | Who can embed this page | `'self'` (prevents clickjacking) |
| `form-action` | Form submission destinations | `'self'` |

---

## CSRF Prevention

### SameSite Cookies

```typescript
// ✅ RECOMMENDED — SameSite=Lax (default in modern browsers)
// Cookies sent on top-level navigations but NOT on cross-site subrequests
Set-Cookie: session=abc123; SameSite=Lax; Secure; HttpOnly

// ✅ STRICT — cookies never sent on cross-site requests
// Use for sensitive operations (banking, admin)
Set-Cookie: session=abc123; SameSite=Strict; Secure; HttpOnly

// ❌ AVOID — SameSite=None requires Secure and sends on all cross-site requests
Set-Cookie: session=abc123; SameSite=None; Secure; HttpOnly
```

| `SameSite` Value | Cross-Site Subrequests | Top-Level Navigation | When to Use |
|------------------|----------------------|---------------------|-------------|
| `Strict` | ❌ Not sent | ❌ Not sent | Sensitive operations (banking) |
| `Lax` | ❌ Not sent | ✅ Sent (GET only) | Default for most apps |
| `None` | ✅ Sent | ✅ Sent | Third-party integrations (requires `Secure`) |

### Anti-CSRF Tokens

```typescript
// Next.js Server Actions — CSRF protection is built in
// Server Actions automatically validate the Origin header

// For custom API routes — use the double-submit cookie pattern:

// ❌ VULNERABLE — no CSRF protection on state-changing endpoint
export async function POST(request: Request) {
  const data = await request.json()
  await updateUser(data)
}

// ✅ SAFE — verify Origin header
export async function POST(request: Request) {
  const origin = request.headers.get('origin')
  if (origin !== process.env.ALLOWED_ORIGIN) {
    return new Response('Forbidden', { status: 403 })
  }
  const data = await request.json()
  await updateUser(data)
}

// ✅ SAFE — custom header check (non-simple requests trigger preflight)
// Client sends:
fetch('/api/users', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',  // Cannot be set by forms
  },
  body: JSON.stringify(data),
})

// Server verifies:
if (!request.headers.get('x-requested-with')) {
  return new Response('Forbidden', { status: 403 })
}
```

---

## CORS

### Same-Origin Policy

Browsers block cross-origin requests by default. CORS headers explicitly allow them.

```typescript
// ❌ VULNERABLE — wildcard with credentials
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
// Browsers reject this combination, but misconfigured servers may reflect Origin

// ❌ VULNERABLE — reflecting Origin header without validation
const origin = request.headers.get('origin')
response.headers.set('Access-Control-Allow-Origin', origin!)  // Trusts any origin

// ✅ SAFE — allowlist validation
const ALLOWED_ORIGINS = ['https://app.example.com', 'https://admin.example.com']
const origin = request.headers.get('origin')

if (origin && ALLOWED_ORIGINS.includes(origin)) {
  response.headers.set('Access-Control-Allow-Origin', origin)
  response.headers.set('Access-Control-Allow-Credentials', 'true')
}
```

### Next.js CORS Configuration

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: 'https://app.example.com' },
          { key: 'Access-Control-Allow-Methods', value: 'GET, POST, PUT, DELETE' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ]
  },
}
```

---

## Authentication in SPAs

### Token Storage

```typescript
// ❌ VULNERABLE — JWT in localStorage (accessible to XSS)
localStorage.setItem('token', jwt)
fetch('/api/data', {
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
})

// ❌ VULNERABLE — JWT in sessionStorage (still accessible to XSS)
sessionStorage.setItem('token', jwt)

// ✅ SAFE — httpOnly cookie (not accessible to JavaScript)
// Server sets:
Set-Cookie: token=jwt; HttpOnly; Secure; SameSite=Lax; Path=/

// Client sends automatically (no JS needed):
fetch('/api/data', { credentials: 'include' })
```

| Storage | XSS Risk | CSRF Risk | Recommendation |
|---------|----------|-----------|----------------|
| `localStorage` | ❌ Vulnerable | ✅ Safe | **Avoid** |
| `sessionStorage` | ❌ Vulnerable | ✅ Safe | **Avoid** |
| `httpOnly` cookie | ✅ Safe | ⚠️ Needs SameSite | **Preferred** |

### Environment Variables

```typescript
// ❌ VULNERABLE — secret in client-visible env var
// .env
NEXT_PUBLIC_API_SECRET=sk-1234567890
// This is bundled into client JavaScript!

// ✅ SAFE — secret in server-only env var
// .env
API_SECRET=sk-1234567890

// ✅ SAFE — only public values use NEXT_PUBLIC_ prefix
NEXT_PUBLIC_API_URL=https://api.example.com
```

**Rule:** `NEXT_PUBLIC_` env vars are embedded in the client bundle. Never put secrets there.

### Auth State and SSR

```typescript
// ❌ RISKY — client-only auth check (flashy, bypassable)
function ProtectedPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) return <Spinner />
  if (!user) redirect('/login')
  return <Dashboard />
}

// ✅ PREFERRED — server-side auth check (Next.js middleware)
// middleware.ts
export function middleware(request: NextRequest) {
  const token = request.cookies.get('session')
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}
```

---

## Iframe Security

### Clickjacking Prevention

```typescript
// Prevent your page from being embedded in malicious iframes

// HTTP header approach
X-Frame-Options: DENY
// Or:
X-Frame-Options: SAMEORIGIN

// CSP approach (preferred — more flexible)
Content-Security-Policy: frame-ancestors 'self'
// Or allow specific origins:
Content-Security-Policy: frame-ancestors 'self' https://trusted.example.com
```

### Embedding Untrusted Content

```typescript
// ❌ VULNERABLE — no sandbox on untrusted iframe
<iframe src={userProvidedUrl} />

// ✅ SAFE — sandbox restricts iframe capabilities
<iframe
  src={userProvidedUrl}
  sandbox="allow-scripts allow-same-origin"
  referrerPolicy="no-referrer"
/>
```

| Sandbox Token | Allows |
|---------------|--------|
| (none — empty sandbox) | Nothing — fully restricted |
| `allow-scripts` | JavaScript execution |
| `allow-same-origin` | Access to origin's storage/cookies |
| `allow-forms` | Form submission |
| `allow-popups` | Opening new windows |

### postMessage Security

```typescript
// ❌ VULNERABLE — no origin check
window.addEventListener('message', (event) => {
  processData(event.data)  // Trusts any sender
})

// ✅ SAFE — validate origin
window.addEventListener('message', (event) => {
  if (event.origin !== 'https://trusted.example.com') return
  processData(event.data)
})

// ✅ SAFE — when sending, specify target origin
iframe.contentWindow?.postMessage(data, 'https://trusted.example.com')
// Never use '*' as target origin with sensitive data
```

---

## Open Redirect Prevention

```typescript
// ❌ VULNERABLE — redirect to user-controlled URL
function handleLogin(returnTo: string) {
  router.push(returnTo)  // Attacker sets returnTo = "https://evil.com"
}

// ❌ VULNERABLE — URL validation bypass
const url = new URL(returnTo)
if (url.hostname.endsWith('example.com')) {  // evil-example.com matches!
  router.push(returnTo)
}

// ✅ SAFE — allowlist of paths (not full URLs)
const SAFE_PATHS = ['/dashboard', '/settings', '/profile']

function handleLogin(returnTo: string) {
  const safePath = SAFE_PATHS.includes(returnTo) ? returnTo : '/dashboard'
  router.push(safePath)
}

// ✅ SAFE — validate against own origin only
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

## Frontend Security Checklist

### XSS
- [ ] No `dangerouslySetInnerHTML` with unsanitised user input
- [ ] DOMPurify used when rendering user-provided HTML
- [ ] URLs validated against `javascript:` protocol
- [ ] CSP headers configured (`script-src`, `default-src`)

### CSRF
- [ ] `SameSite` attribute set on cookies (`Lax` or `Strict`)
- [ ] State-changing API routes verify Origin header or custom header
- [ ] Forms use Server Actions (built-in CSRF protection) where possible

### Authentication
- [ ] JWT/session tokens in `httpOnly` cookies, not `localStorage`
- [ ] No secrets in `NEXT_PUBLIC_` environment variables
- [ ] Cookie attributes: `Secure`, `HttpOnly`, `SameSite`
- [ ] Server-side auth checks (middleware), not client-only

### Iframe / Embedding
- [ ] `frame-ancestors` CSP directive or `X-Frame-Options` set
- [ ] Untrusted iframes use `sandbox` attribute
- [ ] `postMessage` handlers validate `event.origin`

### Redirects
- [ ] Redirect URLs validated against allowlist or own origin
- [ ] No user-controlled full URLs passed to `router.push`

### CORS
- [ ] `Access-Control-Allow-Origin` uses allowlist, not `*` with credentials
- [ ] Origin header not blindly reflected
