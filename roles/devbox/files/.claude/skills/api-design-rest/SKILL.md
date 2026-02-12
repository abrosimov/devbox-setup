---
name: api-design-rest
description: >
  REST API and OpenAPI 3.1 design knowledge. Covers resource naming, HTTP method semantics,
  error formats (RFC 9457), pagination, filtering, versioning, authentication, and Spectral linting.
  Triggers on: REST, OpenAPI, API design, resource, endpoint, pagination, error format, Spectral.
---

# REST / OpenAPI 3.1 Design Knowledge

Reference knowledge for API Designer agent when working with REST APIs and OpenAPI specifications.

---

## Resource Naming Conventions

| Rule | Example | Anti-Pattern |
|------|---------|-------------|
| Plural nouns | `/orders`, `/users` | `/order`, `/getUsers` |
| Hierarchy via nesting | `/users/{id}/orders` | `/getUserOrders` |
| Lowercase with hyphens | `/order-items` | `/orderItems`, `/order_items` |
| No verbs in paths | `/orders` + POST | `/createOrder` |
| No trailing slashes | `/orders` | `/orders/` |
| Collection → item | `/orders` → `/orders/{id}` | `/order/{id}` |

### Nesting Depth

Maximum **2 levels** of nesting. Beyond that, use top-level resources with filters:

```
# Good — 2 levels
GET /users/{userId}/orders

# Bad — 3+ levels
GET /users/{userId}/orders/{orderId}/items/{itemId}/variants

# Better — top-level with filter
GET /order-items/{itemId}/variants
GET /variants?orderId={orderId}
```

---

## HTTP Method Semantics

| Method | Semantics | Idempotent | Safe | Request Body |
|--------|-----------|------------|------|--------------|
| `GET` | Retrieve resource(s) | Yes | Yes | No |
| `POST` | Create resource / trigger action | No | No | Yes |
| `PUT` | Full replacement of resource | Yes | No | Yes |
| `PATCH` | Partial update (JSON Merge Patch or JSON Patch) | No* | No | Yes |
| `DELETE` | Remove resource | Yes | No | Optional |

*PATCH can be made idempotent with `If-Match` + ETag.

### Method Selection Guide

| Intent | Method | Status Code |
|--------|--------|-------------|
| Create new resource | POST | `201 Created` + `Location` header |
| Full replace | PUT | `200 OK` or `204 No Content` |
| Partial update | PATCH | `200 OK` |
| Delete | DELETE | `204 No Content` |
| Retrieve one | GET | `200 OK` |
| Retrieve list | GET | `200 OK` |
| Action (non-CRUD) | POST to sub-resource | `200 OK` or `202 Accepted` |

### Non-CRUD Actions

When an operation isn't a simple CRUD, model it as a sub-resource:

```
POST /orders/{id}/cancel      # Cancel an order
POST /orders/{id}/ship        # Ship an order
POST /payments/{id}/refund    # Refund a payment
```

---

## Error Response Format — RFC 9457 (Problem Details)

**Always use RFC 9457** (`application/problem+json`) for error responses:

```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance is 30.00, but transfer requires 50.00.",
  "instance": "/transfers/abc123"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | URI | Problem type identifier (stable, bookmarkable) |
| `title` | string | Short, human-readable summary (same for all instances of this type) |
| `status` | integer | HTTP status code |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `detail` | string | Human-readable explanation specific to this occurrence |
| `instance` | URI | Identifies the specific occurrence (request path or unique ID) |

### Extension Fields

Add domain-specific fields as needed:

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "errors": [
    { "field": "email", "message": "must be a valid email address" },
    { "field": "age", "message": "must be at least 18" }
  ]
}
```

### HTTP Status Code Guide

| Range | Meaning | When to Use |
|-------|---------|-------------|
| `200` | OK | Successful GET, PUT, PATCH |
| `201` | Created | Successful POST creating resource |
| `202` | Accepted | Async operation started |
| `204` | No Content | Successful DELETE or PUT with no body |
| `400` | Bad Request | Malformed syntax, invalid JSON |
| `401` | Unauthorised | Missing or invalid authentication |
| `403` | Forbidden | Authenticated but not authorised |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | State conflict (duplicate, version mismatch) |
| `422` | Unprocessable Entity | Valid syntax but semantic errors (validation) |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server failure |
| `503` | Service Unavailable | Temporary downtime |

---

## Pagination

### Cursor-Based (Preferred)

Better for real-time data, infinite scroll, large datasets:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true
  }
}
```

Request: `GET /orders?cursor=eyJpZCI6MTAwfQ==&limit=25`

### Offset-Based (Simple)

Better for small datasets, page-numbered UIs:

```json
{
  "data": [...],
  "pagination": {
    "total": 142,
    "offset": 50,
    "limit": 25
  }
}
```

Request: `GET /orders?offset=50&limit=25`

### Decision Guide

| Factor | Cursor | Offset |
|--------|--------|--------|
| Consistency with real-time data | Better | Skips/duplicates possible |
| "Jump to page N" | Not possible | Easy |
| Performance at scale | O(1) | O(n) — degrades with offset |
| Total count needed | Separate query | Can include cheaply |

### Default Limits

- Default page size: **25**
- Maximum page size: **100**
- Always enforce server-side maximum

---

## Filtering and Sorting

### Filtering

Use query parameters with field names:

```
GET /orders?status=pending&customer_id=123
GET /orders?created_after=2025-01-01T00:00:00Z
GET /orders?total_min=100&total_max=500
```

**Conventions:**
- Exact match: `?field=value`
- Range: `?field_min=X&field_max=Y`
- Date range: `?field_after=X&field_before=Y`
- Multiple values: `?status=pending,shipped` (comma-separated)
- Search: `?q=search+term` (full-text)

### Sorting

```
GET /orders?sort=created_at        # Ascending (default)
GET /orders?sort=-created_at       # Descending (prefix -)
GET /orders?sort=-created_at,name  # Multi-field
```

---

## Versioning

### URL Path Versioning (Preferred)

```
/v1/orders
/v2/orders
```

**Pros:** Explicit, easy to route, cache-friendly, easy to deprecate.
**Cons:** URL changes between versions.

### Header Versioning (Alternative)

```
Accept: application/vnd.api.v2+json
```

**Pros:** Clean URLs.
**Cons:** Harder to test (curl), harder to cache, harder to route.

### Versioning Strategy

| Rule | Rationale |
|------|-----------|
| Only increment on breaking changes | Minor additions don't need new version |
| Support N-1 version minimum | Gives consumers time to migrate |
| Deprecation header on old versions | `Deprecation: true`, `Sunset: <date>` |
| Document migration path | Changelog + migration guide |

---

## Authentication in OpenAPI

### Security Schemes

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/authorize
          tokenUrl: https://auth.example.com/token
          scopes:
            read:orders: Read orders
            write:orders: Create and modify orders
```

### Applying Security

```yaml
# Global (applies to all operations)
security:
  - BearerAuth: []

# Per-operation override
paths:
  /public/health:
    get:
      security: []  # No auth required
```

---

## Rate Limiting

### Response Headers

```
X-RateLimit-Limit: 1000        # Requests per window
X-RateLimit-Remaining: 742     # Remaining in current window
X-RateLimit-Reset: 1620000000  # Unix timestamp when window resets
Retry-After: 30                # Seconds to wait (on 429)
```

### Idempotency Keys

For non-idempotent operations (POST), support client-provided idempotency:

```
POST /orders
Idempotency-Key: unique-client-generated-uuid
```

Server behaviour:
- First request: Process normally, store result keyed by idempotency key
- Duplicate request: Return stored result without re-processing
- Key expiry: 24 hours minimum

---

## OpenAPI 3.1 Best Practices

### Structure

```yaml
openapi: "3.1.0"
info:
  title: Order Service API
  version: "1.0.0"
  description: |
    API for managing customer orders.

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

paths:
  /orders:
    get:
      operationId: listOrders
      tags: [Orders]
      summary: List all orders
      # ...
```

### Key Conventions

| Element | Convention |
|---------|-----------|
| `operationId` | camelCase, verb + noun: `listOrders`, `createOrder`, `getOrderById` |
| `tags` | Group by resource: `[Orders]`, `[Users]` |
| `summary` | Short (< 80 chars), no period |
| `description` | Detailed, can use Markdown |
| Path params | `{camelCase}`: `{orderId}`, `{userId}` |
| Query params | `snake_case`: `created_after`, `page_size` |

### Use `$ref` Extensively

```yaml
# Define once in components
components:
  schemas:
    Order:
      type: object
      properties:
        id:
          type: string
          format: uuid
        # ...
    OrderList:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/Order'
        pagination:
          $ref: '#/components/schemas/CursorPagination'

  responses:
    NotFound:
      description: Resource not found
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ProblemDetail'

# Reference everywhere
paths:
  /orders/{orderId}:
    get:
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        '404':
          $ref: '#/components/responses/NotFound'
```

### Examples

Always include examples for request/response bodies:

```yaml
components:
  schemas:
    Order:
      type: object
      properties:
        id:
          type: string
          format: uuid
          examples:
            - "550e8400-e29b-41d4-a716-446655440000"
        status:
          type: string
          enum: [draft, submitted, paid, shipped, delivered, cancelled]
          examples:
            - "submitted"
```

---

## Spectral Linting

### Running Spectral

```bash
# Install
npm install -g @stoplight/spectral-cli

# Lint
spectral lint openapi.yaml

# With custom ruleset
spectral lint openapi.yaml --ruleset .spectral.yaml
```

### Common Rules

- **`oas3-api-servers`** — at least one server defined
- **`operation-operationId`** — every operation has operationId
- **`operation-description`** — every operation has description
- **`operation-tags`** — every operation has at least one tag
- **`path-params`** — path parameters are defined and used
- **`no-$ref-siblings`** — no sibling properties alongside `$ref`
- **`oas3-valid-schema-example`** — examples match schema

### Interpreting Results

- **Error** — Must fix (schema violation, missing required fields)
- **Warning** — Should fix (missing descriptions, inconsistent naming)
- **Information** — Consider (style suggestions)

---

## HATEOAS (Pragmatic Approach)

Include navigation links only when they add value (don't force it everywhere):

```json
{
  "id": "order-123",
  "status": "submitted",
  "_links": {
    "self": { "href": "/orders/order-123" },
    "cancel": { "href": "/orders/order-123/cancel", "method": "POST" },
    "items": { "href": "/orders/order-123/items" }
  }
}
```

**When to include links:**
- State-dependent actions (cancel only when cancellable)
- Related resource navigation
- Pagination (next/prev)

**When to skip:**
- Internal microservice APIs
- Simple CRUD with predictable URLs
