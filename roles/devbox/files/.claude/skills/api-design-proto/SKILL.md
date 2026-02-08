---
name: api-design-proto
description: >
  Protobuf and gRPC API design knowledge. Covers proto3 syntax, Google style guide, gRPC service
  patterns, buf linting and breaking change detection, well-known types, and gRPC-gateway annotations.
  Triggers on: protobuf, proto, gRPC, buf, proto3, service definition, streaming, breaking change.
---

# Protobuf / gRPC Design Knowledge

Reference knowledge for API Designer agent when working with Protocol Buffers and gRPC services.

---

## Proto3 Syntax Best Practices

### File Structure

```protobuf
// Standard file layout
syntax = "proto3";

package mycompany.myservice.v1;

import "google/protobuf/timestamp.proto";
import "google/api/annotations.proto";

option go_package = "github.com/mycompany/myservice/gen/myservice/v1;myservicev1";

// Service definition
service OrderService {
  rpc CreateOrder(CreateOrderRequest) returns (CreateOrderResponse);
  rpc GetOrder(GetOrderRequest) returns (Order);
  rpc ListOrders(ListOrdersRequest) returns (ListOrdersResponse);
}

// Messages
message Order {
  string id = 1;
  // ...
}
```

### Package Naming

| Rule | Example |
|------|---------|
| Lowercase, dot-separated | `mycompany.orders.v1` |
| Include company/org prefix | `acme.billing.v1` |
| Include version suffix | `*.v1`, `*.v2` |
| Match directory structure | `mycompany/orders/v1/orders.proto` |

---

## Message Design — Google Protobuf Style Guide

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Message | PascalCase | `OrderItem`, `CreateOrderRequest` |
| Field | snake_case | `order_id`, `created_at` |
| Enum type | PascalCase | `OrderStatus` |
| Enum value | SCREAMING_SNAKE_CASE | `ORDER_STATUS_PENDING` |
| Service | PascalCase + "Service" | `OrderService` |
| RPC | PascalCase, verb + noun | `CreateOrder`, `ListOrders` |

### Enum Conventions

```protobuf
enum OrderStatus {
  // First value MUST be 0 and act as default/unknown
  ORDER_STATUS_UNSPECIFIED = 0;
  ORDER_STATUS_DRAFT = 1;
  ORDER_STATUS_SUBMITTED = 2;
  ORDER_STATUS_PAID = 3;
  ORDER_STATUS_SHIPPED = 4;
  ORDER_STATUS_DELIVERED = 5;
  ORDER_STATUS_CANCELLED = 6;
}
```

**Rules:**
- First value is always `*_UNSPECIFIED = 0`
- Prefix all values with enum type name in SCREAMING_SNAKE_CASE
- Never reuse numbers (even after deprecation — use `reserved`)

### Request/Response Pattern

```protobuf
// Every RPC gets its own request and response messages
// Even if the request is empty or response is a single entity

rpc CreateOrder(CreateOrderRequest) returns (CreateOrderResponse);
rpc GetOrder(GetOrderRequest) returns (Order);  // OK to return entity directly for Get
rpc ListOrders(ListOrdersRequest) returns (ListOrdersResponse);
rpc DeleteOrder(DeleteOrderRequest) returns (google.protobuf.Empty);
```

**Naming convention:** `{Method}{Resource}Request` / `{Method}{Resource}Response`

---

## Field Numbering and Backward Compatibility

### Field Number Ranges

| Range | Purpose |
|-------|---------|
| 1–15 | Frequently used fields (1-byte encoding) |
| 16–2047 | Less frequent fields (2-byte encoding) |
| 19000–19999 | Reserved by protobuf (do NOT use) |

### Reserved Fields

When removing fields, **reserve** the number and name to prevent accidental reuse:

```protobuf
message Order {
  reserved 4, 8 to 10;
  reserved "legacy_status", "old_total";

  string id = 1;
  string customer_id = 2;
  // field 4 was legacy_status — removed in v1.3
}
```

### Backward Compatibility Rules

| Safe (Non-Breaking) | Unsafe (Breaking) |
|---------------------|-------------------|
| Add new field | Remove field without `reserved` |
| Add new enum value | Change field number |
| Add new RPC | Change field type |
| Deprecate field | Rename field (wire format OK, but code breaks) |
| Add new message | Remove enum value without `reserved` |

---

## Well-Known Types

### Commonly Used

| Type | Import | Use For |
|------|--------|---------|
| `Timestamp` | `google/protobuf/timestamp.proto` | Date/time values |
| `Duration` | `google/protobuf/duration.proto` | Time spans |
| `Empty` | `google/protobuf/empty.proto` | Requests/responses with no data |
| `FieldMask` | `google/protobuf/field_mask.proto` | Partial updates |
| `Struct` | `google/protobuf/struct.proto` | Dynamic JSON-like data |
| `Any` | `google/protobuf/any.proto` | Polymorphic messages |
| `StringValue` / `Int32Value` etc. | `google/protobuf/wrappers.proto` | Nullable scalars |

### Usage Examples

```protobuf
import "google/protobuf/timestamp.proto";
import "google/protobuf/field_mask.proto";

message Order {
  string id = 1;
  google.protobuf.Timestamp created_at = 2;
  google.protobuf.Timestamp updated_at = 3;
}

// Partial update with FieldMask
message UpdateOrderRequest {
  Order order = 1;
  google.protobuf.FieldMask update_mask = 2;
}
```

---

## gRPC Service Design Patterns

### RPC Types

| Type | When to Use |
|------|-------------|
| **Unary** | Standard request-response (most RPCs) |
| **Server streaming** | Large result sets, real-time updates, event feeds |
| **Client streaming** | File uploads, batch operations |
| **Bidirectional streaming** | Chat, real-time collaboration, multiplexed channels |

```protobuf
service OrderService {
  // Unary
  rpc CreateOrder(CreateOrderRequest) returns (CreateOrderResponse);

  // Server streaming — stream order updates
  rpc WatchOrders(WatchOrdersRequest) returns (stream OrderEvent);

  // Client streaming — batch import
  rpc ImportOrders(stream ImportOrderRequest) returns (ImportOrdersResponse);

  // Bidirectional — real-time sync
  rpc SyncOrders(stream SyncRequest) returns (stream SyncResponse);
}
```

### Pagination (List RPCs)

```protobuf
message ListOrdersRequest {
  int32 page_size = 1;       // Max items per page (default 25, max 100)
  string page_token = 2;     // Opaque cursor from previous response
  string filter = 3;         // Optional filter expression
  string order_by = 4;       // Sort order: "created_at desc"
}

message ListOrdersResponse {
  repeated Order orders = 1;
  string next_page_token = 2;  // Empty if no more pages
  int32 total_size = 3;        // Optional: total count
}
```

---

## gRPC Status Codes

| Code | Name | HTTP Equivalent | When to Use |
|------|------|-----------------|-------------|
| `0` | OK | 200 | Success |
| `1` | CANCELLED | 499 | Client cancelled |
| `2` | UNKNOWN | 500 | Unknown error |
| `3` | INVALID_ARGUMENT | 400 | Bad input |
| `4` | DEADLINE_EXCEEDED | 504 | Timeout |
| `5` | NOT_FOUND | 404 | Resource not found |
| `6` | ALREADY_EXISTS | 409 | Duplicate resource |
| `7` | PERMISSION_DENIED | 403 | Not authorised |
| `8` | RESOURCE_EXHAUSTED | 429 | Rate limit / quota |
| `9` | FAILED_PRECONDITION | 400 | State-dependent precondition failed |
| `10` | ABORTED | 409 | Concurrency conflict |
| `11` | OUT_OF_RANGE | 400 | Value outside valid range |
| `12` | UNIMPLEMENTED | 501 | RPC not implemented |
| `13` | INTERNAL | 500 | Internal server error |
| `14` | UNAVAILABLE | 503 | Temporarily unavailable (retryable) |
| `16` | UNAUTHENTICATED | 401 | Not authenticated |

### Error Details

Use `google.rpc.Status` with detail messages for rich errors:

```protobuf
import "google/rpc/status.proto";
import "google/rpc/error_details.proto";

// Server returns status with details:
// code: INVALID_ARGUMENT
// message: "Validation failed"
// details: [BadRequest { field_violations: [...] }]
```

---

## gRPC-Gateway Annotations

For services that expose both gRPC and REST:

```protobuf
import "google/api/annotations.proto";

service OrderService {
  rpc CreateOrder(CreateOrderRequest) returns (Order) {
    option (google.api.http) = {
      post: "/v1/orders"
      body: "*"
    };
  }

  rpc GetOrder(GetOrderRequest) returns (Order) {
    option (google.api.http) = {
      get: "/v1/orders/{order_id}"
    };
  }

  rpc ListOrders(ListOrdersRequest) returns (ListOrdersResponse) {
    option (google.api.http) = {
      get: "/v1/orders"
    };
  }

  rpc UpdateOrder(UpdateOrderRequest) returns (Order) {
    option (google.api.http) = {
      patch: "/v1/orders/{order.id}"
      body: "order"
    };
  }

  rpc DeleteOrder(DeleteOrderRequest) returns (google.protobuf.Empty) {
    option (google.api.http) = {
      delete: "/v1/orders/{order_id}"
    };
  }
}
```

### Path Parameter Mapping

- Field in request message maps to path parameter: `{order_id}` → `GetOrderRequest.order_id`
- Nested fields: `{order.id}` → `UpdateOrderRequest.order.id`
- Remaining fields become query parameters (GET) or JSON body (POST/PUT/PATCH)

---

## buf Configuration

### `buf.yaml`

```yaml
version: v2
modules:
  - path: proto
    name: buf.build/mycompany/myservice
lint:
  use:
    - STANDARD
  except:
    - PACKAGE_VERSION_SUFFIX  # If not using version suffixes
breaking:
  use:
    - FILE
```

### buf lint Rules (Key Categories)

| Category | Rules | Description |
|----------|-------|-------------|
| `MINIMAL` | 6 rules | Bare minimum (message/enum naming) |
| `BASIC` | 25 rules | Good baseline (field naming, service naming) |
| `STANDARD` | 40 rules | Recommended (includes comments, package naming) |
| `COMMENTS` | 4 rules | Require comments on services, RPCs, messages, enums |

### Key lint Rules

| Rule | What It Checks |
|------|---------------|
| `ENUM_ZERO_VALUE_SUFFIX` | First enum value ends with `_UNSPECIFIED` |
| `ENUM_VALUE_PREFIX` | Enum values prefixed with enum name |
| `FIELD_LOWER_SNAKE_CASE` | Fields use snake_case |
| `MESSAGE_PASCAL_CASE` | Messages use PascalCase |
| `SERVICE_SUFFIX` | Services end with "Service" |
| `RPC_REQUEST_RESPONSE_UNIQUE` | Request/response types not reused |
| `RPC_REQUEST_STANDARD_NAME` | Request type matches `{Method}Request` |
| `RPC_RESPONSE_STANDARD_NAME` | Response type matches `{Method}Response` |
| `PACKAGE_DIRECTORY_MATCH` | Package matches directory structure |

### Running buf

```bash
# Lint
buf lint

# Check breaking changes against main branch
buf breaking --against '.git#branch=main'

# Check breaking changes against BSR
buf breaking --against 'buf.build/mycompany/myservice'

# Generate code
buf generate
```

### buf Breaking Change Detection

| Category | Rules | Use For |
|----------|-------|---------|
| `FILE` | 53 rules | Strictest — source compatibility |
| `PACKAGE` | 37 rules | Package-level compatibility |
| `WIRE` | 18 rules | Wire format only |
| `WIRE_JSON` | 24 rules | Wire + JSON compatibility |

**Recommended:** `FILE` for public APIs, `WIRE_JSON` for internal services.

---

## Proto File Organisation

### Directory Structure

```
proto/
├── mycompany/
│   └── myservice/
│       └── v1/
│           ├── orders.proto          # Order service and messages
│           ├── order_items.proto     # OrderItem messages (if large)
│           ├── common.proto          # Shared types (Money, Address)
│           └── events.proto          # Event messages (if using events)
├── buf.yaml
├── buf.gen.yaml
└── buf.lock
```

### File Splitting Rules

| When | How |
|------|-----|
| Single service, few messages | One file per service |
| Many shared types | Extract `common.proto` |
| Large message count (>20) | Split by domain concept |
| Events/notifications | Separate `events.proto` |
