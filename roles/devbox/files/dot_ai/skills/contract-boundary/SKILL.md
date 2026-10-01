---
name: contract-boundary
description: Frontend and backend synchronise only through the API contract (OpenAPI spec, proto files, or types generated from them). Use when implementing, designing, or reviewing code on either side of an API, when a design depends on how the other side behaves (caching, pagination, limits, rate limits, ordering, rounding), when no contract file exists yet, or when writing a contract-gap report. Not for designing the contract from scratch; that is the API designer's job.
version: 1
triggers:
  - api contract
  - openapi
  - api_spec.yaml
  - proto
  - frontend and backend
  - fullstack
  - contract gap
  - backend caches
  - generated types
problem: "Engineers justify designs from the other side's implementation (its caches, query plans, rounding) instead of the API contract, so the design silently breaks when that implementation changes."
related: [diverge-synthesize-select, code-comments]
---

# Contract Boundary

The API contract is the only thing frontend and backend share. The contract is the OpenAPI spec, the
proto files, or the types generated from them. Everything else about the other side is its private
implementation.

## Why

- **Information hiding (Parnas, 1972).** A module boundary exists so that each side can change its
  internals without telling the other. A design that relies on the other side's cache, query shape, or
  rounding couples you to a secret that its owners are free to change tomorrow, and nobody will tell you.
- **Consumer-driven contracts.** When the consumer needs a property, the durable way to get it is to have
  it written into the contract, where the provider can see it, test it, and keep it. A property that
  lives only in the provider's code is an accident, not a guarantee.
- **Parallel work.** Once the contract is fixed, both sides can be built at the same time by people (or
  agents) who never read each other's code. That only works if nobody reaches across.

## Rules

1. **Reason only from contract guarantees.** Each design decision that involves the other side cites the
   contract: an endpoint, a schema, a header, a documented limit. If you cannot cite it, it is not
   guaranteed.
2. **Leave the other side's code out of the basis for decisions.** Handlers, caches, SQL, config, and
   comments on the other side can explain a bug you are debugging, but they cannot justify a design.
3. **Non-functional properties belong in the contract.** When one side relies on any of these, the
   contract states it:
   - caching (whether, how long, by whom; `Cache-Control`, `ETag`)
   - pagination (page size limits, cursor stability)
   - maximum request or response payload, maximum items per request
   - rate limits and the response when exceeded
   - ordering and its stability
   - rounding of numbers, timestamps, and time windows
   - idempotency and read consistency
4. **Missing guarantee: raise a contract gap.** If you need a property the contract does not state,
   write a contract-gap report (template below) and handle the case locally until the contract is
   changed. Reading the other side to find out "what it really does" is the thing this skill replaces.
5. **No contract file yet: derive it once.** Read the backend's public surface only (route
   registrations, handler signatures, request and response types) and write it down as an explicit
   spec file (`api_spec.yaml` or `.proto`). Get the user or the API owner to confirm it. From then on,
   both sides work only against that file.
6. **Allowed reading of the other side:** its published contract artefacts. That means spec files,
   proto files, generated clients and types, and API documentation that ships with the contract.

## Example

The incident that motivated this skill, rewritten.

**Before (reasoning across the boundary):**

> The frontend fires one metrics request per panel without de-duplication. That is fine: the backend
> has a shared result cache (`internal/reading/prom/cache.go`, 5 min, window rounded), so Prometheus
> computes once.

This depends on a file, a TTL, and a rounding rule that the contract never mentions. Any backend
refactor removes the protection without warning.

**After (reasoning from the contract):**

> The contract promises no caching for `GET /metrics/query`, so the frontend de-duplicates identical
> in-flight requests itself (one request per unique query and window). If caching has to be a
> guarantee, for example to protect Prometheus, we add `Cache-Control: max-age=300` and the window
> rounding rule to the spec, and the backend owns keeping that promise.

## Contract-gap report

Use this when you need a guarantee the contract does not give. Send it to the user or the API owner;
keep working with local handling meanwhile.

```markdown
### Contract gap: <short name>

- **Contract**: <path to spec or proto>, <endpoint / RPC / schema>
- **Missing**: <the property that is unstated, e.g. "no caching or freshness statement">
- **Why needed**: <the decision on this side that depends on it, and what goes wrong without it>
- **Proposed contract text**: <the exact addition, e.g. response header
  `Cache-Control: max-age=300`; description "time windows are aligned to 1-minute boundaries">
- **Interim handling**: <what this side does until the contract changes>
```

## In review

Reliance on the other side's internals is a finding, whether it appears in code, in a comment, or in
the engineer's written justification. Examples: citing a file path from the other side, assuming a
cache, assuming a query returns sorted rows, assuming a limit that the spec does not state. The fix is
one of two: handle it locally, or change the contract through a contract-gap report.
