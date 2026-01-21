---
name: security-patterns
description: >
  Security patterns for input validation, secrets handling, and common vulnerability prevention.
  Triggers on: security, injection, SQL, XSS, CSRF, secrets, validation, sanitize, authentication.
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
