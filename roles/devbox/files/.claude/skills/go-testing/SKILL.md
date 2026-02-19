---
name: go-testing
description: >
  Go testing patterns with testify suites, table-driven tests, mocking with mockery.
  Triggers on: test, testing, testify, mock, table-driven, suite, fixture, assertion.
---

# Go Testing Patterns

Idiomatic Go testing with testify suites, table-driven tests, and mockery mocks.

## Test File Structure

```go
package mypackage_test  // Use _test suffix for black-box testing

import (
    "context"
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "github.com/stretchr/testify/suite"
)
```

## Testify Suite Pattern

**Preferred structure for all test files:**

```go
type UserServiceSuite struct {
    suite.Suite

    // Dependencies
    mockRepo *mocks.MockUserRepository
    service  *UserService
}

func TestUserServiceSuite(t *testing.T) {
    suite.Run(t, new(UserServiceSuite))
}

func (s *UserServiceSuite) SetupTest() {
    s.mockRepo = mocks.NewMockUserRepository(s.T())
    s.service = NewUserService(s.mockRepo)
}

func (s *UserServiceSuite) TearDownTest() {
    // Cleanup if needed
}

func (s *UserServiceSuite) TestGetUser_Success() {
    // Arrange
    expected := &User{ID: "123", Name: "John"}
    s.mockRepo.EXPECT().FindByID(mock.Anything, "123").Return(expected, nil)

    // Act
    result, err := s.service.GetUser(context.Background(), "123")

    // Assert
    s.Require().NoError(err)
    s.Assert().Equal(expected, result)
}
```

## Table-Driven Tests

**Always prefer table-driven tests over separate test functions:**

```go
func (s *ValidatorSuite) TestValidateEmail() {
    tests := []struct {
        name    string
        email   string
        wantErr bool
    }{
        {
            name:    "valid email",
            email:   "user@example.com",
            wantErr: false,
        },
        {
            name:    "missing @",
            email:   "userexample.com",
            wantErr: true,
        },
        {
            name:    "empty string",
            email:   "",
            wantErr: true,
        },
        {
            name:    "multiple @",
            email:   "user@@example.com",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        s.Run(tt.name, func() {
            err := s.validator.ValidateEmail(tt.email)
            if tt.wantErr {
                s.Assert().Error(err)
            } else {
                s.Assert().NoError(err)
            }
        })
    }
}
```

### Table Test Naming

| Pattern | Example |
|---------|---------|
| Happy path | `"valid email"`, `"success"`, `"returns user"` |
| Error condition | `"missing @"`, `"empty string"`, `"not found"` |
| Edge case | `"max length"`, `"unicode chars"`, `"zero value"` |
| Boundary | `"exactly at limit"`, `"one over limit"` |

## Assert vs Require

| Use | When |
|-----|------|
| `s.Assert()` | Test can continue if assertion fails |
| `s.Require()` | Test must stop if assertion fails (e.g., nil check before access) |
| `require.NoError()` | Error would make subsequent assertions meaningless |

```go
func (s *ServiceSuite) TestGetUser() {
    result, err := s.service.GetUser(ctx, "123")

    // Use Require — if error, result is nil and next line panics
    s.Require().NoError(err)
    s.Require().NotNil(result)

    // Use Assert — these can fail independently
    s.Assert().Equal("123", result.ID)
    s.Assert().Equal("John", result.Name)
}
```

## Mocking with Mockery

### Generate Mocks

```bash
# Install mockery
go install github.com/vektra/mockery/v2@latest

# Generate mock for interface
mockery --name=UserRepository --output=mocks --outpkg=mocks

# Generate all mocks from interfaces in package
mockery --all --output=mocks --outpkg=mocks
```

### Mock Expectations

```go
func (s *ServiceSuite) TestCreateUser_Success() {
    user := &User{Name: "John", Email: "john@example.com"}

    // Expect call with any context, specific user
    s.mockRepo.EXPECT().
        Save(mock.Anything, user).
        Return(nil).
        Once()

    err := s.service.CreateUser(context.Background(), user)

    s.Require().NoError(err)
}

func (s *ServiceSuite) TestCreateUser_RepoError() {
    user := &User{Name: "John"}

    s.mockRepo.EXPECT().
        Save(mock.Anything, user).
        Return(errors.New("db connection failed")).
        Once()

    err := s.service.CreateUser(context.Background(), user)

    s.Require().Error(err)
    s.Assert().Contains(err.Error(), "db connection failed")
}
```

### Mock Matchers

```go
// Any value
mock.Anything

// Specific type
mock.AnythingOfType("*User")

// Custom matcher
mock.MatchedBy(func(u *User) bool {
    return u.Email != ""
})
```

## Testing Error Paths

**Every error return path needs a test:**

```go
func (s *ServiceSuite) TestGetUser_NotFound() {
    s.mockRepo.EXPECT().
        FindByID(mock.Anything, "unknown").
        Return(nil, ErrNotFound)

    _, err := s.service.GetUser(context.Background(), "unknown")

    s.Require().Error(err)
    s.Assert().ErrorIs(err, ErrNotFound)
}

func (s *ServiceSuite) TestGetUser_RepoError() {
    s.mockRepo.EXPECT().
        FindByID(mock.Anything, "123").
        Return(nil, errors.New("connection refused"))

    _, err := s.service.GetUser(context.Background(), "123")

    s.Require().Error(err)
    s.Assert().Contains(err.Error(), "connection refused")
}
```

## Testing HTTP Handlers

```go
func (s *HandlerSuite) TestGetUser_Success() {
    user := &User{ID: "123", Name: "John"}
    s.mockService.EXPECT().GetUser(mock.Anything, "123").Return(user, nil)

    req := httptest.NewRequest(http.MethodGet, "/users/123", nil)
    rec := httptest.NewRecorder()

    s.handler.GetUser(rec, req)

    s.Assert().Equal(http.StatusOK, rec.Code)

    var response User
    err := json.NewDecoder(rec.Body).Decode(&response)
    s.Require().NoError(err)
    s.Assert().Equal(user.ID, response.ID)
}

func (s *HandlerSuite) TestGetUser_NotFound() {
    s.mockService.EXPECT().GetUser(mock.Anything, "unknown").Return(nil, ErrNotFound)

    req := httptest.NewRequest(http.MethodGet, "/users/unknown", nil)
    rec := httptest.NewRecorder()

    s.handler.GetUser(rec, req)

    s.Assert().Equal(http.StatusNotFound, rec.Code)
}
```

## Testing Context Cancellation

```go
func (s *ServiceSuite) TestGetUser_ContextCancelled() {
    ctx, cancel := context.WithCancel(context.Background())
    cancel() // Cancel immediately

    _, err := s.service.GetUser(ctx, "123")

    s.Require().Error(err)
    s.Assert().ErrorIs(err, context.Canceled)
}

func (s *ServiceSuite) TestGetUser_ContextTimeout() {
    ctx, cancel := context.WithTimeout(context.Background(), 1*time.Nanosecond)
    defer cancel()
    time.Sleep(1 * time.Millisecond) // Ensure timeout

    _, err := s.service.GetUser(ctx, "123")

    s.Require().Error(err)
    s.Assert().ErrorIs(err, context.DeadlineExceeded)
}
```

## Bug-Hunting Scenarios

For EVERY function, systematically test:

### Input Boundaries

| Category | Test Cases |
|----------|-----------|
| Empty | `""`, `nil`, empty slice, zero struct |
| Single | One element, one character |
| Boundary | Max int, exactly at limit |
| Beyond | Limit+1, negative when positive expected |

### Type-Specific Edge Cases

| Type | Edge Cases |
|------|-----------|
| Strings | `""`, whitespace-only, unicode, very long |
| Integers | `0`, `-1`, `math.MaxInt64`, `math.MinInt64` |
| Slices | `nil` vs `[]T{}`, single element, duplicates |
| Maps | `nil` vs `map[K]V{}`, missing key |
| Time | `time.Time{}`, far past, far future |
| Pointers | `nil`, valid pointer |

### Concurrency (if applicable)

```go
func (s *ServiceSuite) TestConcurrentAccess() {
    var wg sync.WaitGroup
    errors := make(chan error, 100)

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            _, err := s.service.GetUser(context.Background(), fmt.Sprintf("%d", id))
            if err != nil {
                errors <- err
            }
        }(i)
    }

    wg.Wait()
    close(errors)

    for err := range errors {
        s.Fail("concurrent access failed", err)
    }
}
```

## What NOT to Test

### Type System Guarantees

```go
// ❌ FORBIDDEN — tests Go's type system
func TestUserStruct(t *testing.T) {
    u := User{ID: "123"}
    assert.Equal(t, "123", u.ID) // Go guarantees this
}

// ❌ FORBIDDEN — tests slice behaviour
func TestSliceAppend(t *testing.T) {
    items := []string{"a"}
    items = append(items, "b")
    assert.Len(t, items, 2) // Go guarantees this
}
```

### Testing Private Functions

Test through public API. If private logic is complex enough to need direct testing, extract to separate package.

```go
// ❌ BAD — testing private method
func TestValidateInternal(t *testing.T) {
    svc := &UserService{}
    result := svc.validateEmail("test@example.com") // Don't test private
}

// ✅ GOOD — test through public API
func (s *ServiceSuite) TestCreateUser_ValidatesEmail() {
    user := &User{Email: "invalid"}

    err := s.service.CreateUser(context.Background(), user)

    s.Require().Error(err)
    s.Assert().Contains(err.Error(), "invalid email")
}
```

## Test Execution Commands

```bash
# Run all tests
go test ./...

# Run specific package
go test ./internal/service/...

# Run specific test
go test -run TestUserServiceSuite/TestGetUser_Success ./internal/service/

# Run with verbose output
go test -v ./...

# Run with coverage
go test -cover ./...

# Generate coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Run with race detector
go test -race ./...
```

## Checklist Before Completion

- [ ] All public functions have tests
- [ ] All error paths are tested (every `return err`)
- [ ] Table-driven tests used where appropriate
- [ ] Mocks verify call expectations
- [ ] Edge cases covered (nil, empty, boundary)
- [ ] Context cancellation tested (if context used)
- [ ] No tests for type system guarantees
- [ ] Tests pass: `go test ./...`
- [ ] Race detector passes: `go test -race ./...`

---

## Advanced Bug-Hunting Scenarios

The sections below extend the basic Bug-Hunting Scenarios above with additional categories.

### Nil Receivers — Test Design, Not Checks

**DO NOT write tests for nil receiver handling inside methods.** Instead:
- Test that constructors reject nil dependencies
- Test that constructors never return nil without error
- DO NOT test nil receiver scenarios — code should exclude this by design

```go
// BAD — testing nil receiver handling (anti-pattern)
func (s *ServiceTestSuite) TestProcess_NilReceiver() {
    var svc *Service = nil
    err := svc.Process()  // DON'T TEST THIS
    s.Require().Error(err)
}

// GOOD — test that constructor validates dependencies
func (s *ServiceTestSuite) TestNewService_NilClient() {
    svc, err := NewService(nil)
    s.Require().Error(err)
    s.Require().Nil(svc)
    s.Require().Contains(err.Error(), "client is required")
}

// GOOD — test that constructor returns non-nil on success
func (s *ServiceTestSuite) TestNewService_Success() {
    client := mocks.NewClient(s.T())
    svc, err := NewService(client)
    s.Require().NoError(err)
    s.Require().NotNil(svc)  // guarantees receiver is never nil
}
```

### Security Testing

> Reference: `security-patterns` skill for CRITICAL/GUARDED/CONTEXT tiers.

| Pattern | What to Test |
|---------|-------------|
| SQL queries | Verify parameterised queries used, not string concat — pass `'; DROP TABLE users--` in input |
| Command execution | Verify arguments passed as list, not shell string — pass `; rm -rf /` in input |
| Token/secret comparison | Verify `crypto/subtle.ConstantTimeCompare` used, not `==` — test that comparison is constant-time (timing oracle) |
| Random values for security | Verify `crypto/rand` used, not `math/rand` — check import |
| Path traversal | Pass `../../../etc/passwd` as path input, verify rejection |
| Input sanitisation | Verify HTML/XSS payloads are sanitised before storage |
| Password hashing | Verify argon2id or bcrypt, not md5/sha1 — test that hash output changes per call (salt) |
| Error leakage | Verify error responses don't contain internal details (DB errors, stack traces, file paths) |
| GUARDED patterns | If code uses `InsecureSkipVerify`, `grpc.WithInsecure`, `reflection.Register` — verify guard (build tag, config, env) |

**How to test (examples):**
```go
// Path traversal — verify rejection
{
    name:    "path traversal rejected",
    input:   "../../../etc/passwd",
    wantErr: ErrInvalidPath,
},

// Error leakage — verify sanitised response
{
    name:      "db error returns generic message",
    mockSetup: func() { s.mockDB.EXPECT().Get(mock.Anything).Return(nil, errors.New("pq: connection refused")) },
    wantErr:   ErrInternal,  // NOT the raw DB error
},

// Token comparison — verify constant-time
{
    name:    "rejects invalid token",
    token:   "wrong-token",
    wantErr: ErrUnauthorized,
},
```

### Error Paths

- What errors can the function return?
- Is each error path tested?
- What happens on partial failure?
- Are wrapped errors testable with `errors.Is`/`errors.As`?

### State Transitions

- Does calling the method twice behave correctly?
- What's the behaviour after error recovery?
- Are resources properly cleaned up on failure?

### Distributed Systems

- Are HTTP calls retried on transient failures?
- Do retries use exponential backoff?
- Are timeouts respected and tested?
- Is context cancellation handled during retries?
- Is the correct transaction pattern used?
  - Fetch before transaction (need external data for logic)
  - Call after commit (failure OK)
  - Transactional outbox (must be reliable)
  - Durable workflow (saga/compensation needed)

---

## Advanced Implementation Patterns

### Table-Driven Tests with Helper Methods

Combine table-driven tests with helper methods for complex object construction:

```go
// suite_test.go — helper methods for complex objects
type ResourceTestSuite struct {
    suite.Suite
}

func (s *ResourceTestSuite) createValidResource(name string) *Resource {
    s.T().Helper()
    return &Resource{
        Name:     name,
        Endpoint: "https://api.example.com",
        Status:   StatusReady,
        // ... other required fields
    }
}

func (s *ResourceTestSuite) createResourceWithStatus(name string, status Status) *Resource {
    s.T().Helper()
    r := s.createValidResource(name)
    r.Status = status
    return r
}

// resource_test.go — table-driven test using helpers
func (s *ResourceServiceTestSuite) TestProcessResource() {
    tests := []struct {
        name      string
        resource  *Resource  // use helper to create
        mockSetup func()
        wantErr   error
    }{
        {
            name:     "ready resource succeeds",
            resource: s.createValidResource("res-1"),
            mockSetup: func() {
                s.mockClient.EXPECT().Process(mock.Anything).Return(nil)
            },
        },
        {
            name:     "not ready resource fails",
            resource: s.createResourceWithStatus("res-2", StatusPending),
            wantErr:  ErrNotReady,
        },
    }

    for _, tt := range tests {
        s.Run(tt.name, func() {
            if tt.mockSetup != nil {
                tt.mockSetup()
            }
            err := s.service.Process(context.Background(), tt.resource)
            if tt.wantErr != nil {
                s.Require().ErrorIs(err, tt.wantErr)
                return
            }
            s.Require().NoError(err)
        })
    }
}
```

### Complete Suite Hierarchy Example

```go
package config_test

import (
    "testing"

    "github.com/stretchr/testify/suite"
    "myproject/pkg/config"
)

// ConfigTestSuite is the package-level suite
type ConfigTestSuite struct {
    suite.Suite
}

// ParserTestSuite is the file-level suite for parser.go
type ParserTestSuite struct {
    ConfigTestSuite  // embed package suite
}

func TestParserTestSuite(t *testing.T) {
    suite.Run(t, new(ParserTestSuite))
}

func (s *ParserTestSuite) TestParseConfig() {
    tests := []struct {
        name    string
        input   string
        want    *config.Config
        wantErr bool
    }{
        {
            name:  "valid config",
            input: `{"port": 8080}`,
            want:  &config.Config{Port: 8080},
        },
        {
            name:    "invalid json",
            input:   `{invalid}`,
            wantErr: true,
        },
        {
            name:  "empty input",
            input: "",
            want:  &config.Config{},
        },
    }

    for _, tt := range tests {
        s.Run(tt.name, func() {
            got, err := config.ParseConfig(tt.input)

            if tt.wantErr {
                s.Require().Error(err)
                return
            }

            s.Require().NoError(err)
            s.Require().Equal(tt.want, got)
        })
    }
}
```

### Assertions Reference

Always use `s.Require()` for assertions:

```go
s.Require().NoError(err)
s.Require().Error(err)
s.Require().Equal(expected, actual)
s.Require().NotEqual(unexpected, actual)
s.Require().Nil(value)
s.Require().NotNil(value)
s.Require().True(condition)
s.Require().False(condition)
s.Require().Contains(slice, element)
s.Require().Len(collection, expectedLen)
s.Require().Empty(collection)
s.Require().ErrorIs(err, targetErr)
s.Require().ErrorContains(err, "substring")
```

#### Comparing Defined Types with Literals

Use `EqualValues` when comparing defined types with expected literals (performs type conversion before comparison):

```go
type ResourceName string

// VERBOSE — explicit conversion in test
s.Require().Equal(ResourceName("expected"), result.Name)

// CLEAN — EqualValues handles conversion
s.Require().EqualValues("expected", result.Name)
```

**When to use `Equal` vs `EqualValues`:**
- `Equal` — when type match is part of what you're testing
- `EqualValues` — when you only care about the underlying value

### Error Assertions — Use ErrorIs, Not String Comparison

**Always use `ErrorIs` or `ErrorAs` for error checking.** Never compare error messages as strings.

```go
// BAD — fragile, breaks if message changes, doesn't handle wrapped errors
s.Require().Error(err)
s.Require().Contains(err.Error(), "not found")
s.Require().Equal("user not found", err.Error())
s.Require().True(strings.Contains(err.Error(), "failed"))

// GOOD — robust, handles wrapped errors, type-safe
s.Require().ErrorIs(err, ErrNotFound)
s.Require().ErrorIs(err, context.DeadlineExceeded)
s.Require().ErrorIs(err, sql.ErrNoRows)
```

**Why string comparison is wrong:**
| Problem | Consequence |
|---------|-------------|
| Message changes break tests | Refactoring error messages causes false failures |
| Doesn't handle wrapping | `fmt.Errorf("failed: %w", ErrNotFound)` won't match string |
| Not type-safe | Typos in expected string silently pass |
| Tests implementation, not behaviour | Error type is the contract, message is detail |

**Error assertion decision tree:**

| Scenario | Use |
|----------|-----|
| Checking for specific sentinel error | `s.Require().ErrorIs(err, ErrNotFound)` |
| Checking error type (custom error struct) | `s.Require().ErrorAs(err, &targetErr)` |
| Checking error occurred (don't care which) | `s.Require().Error(err)` |
| Checking NO error occurred | `s.Require().NoError(err)` |
| Checking error from stdlib/external pkg | `s.Require().ErrorIs(err, sql.ErrNoRows)` |

**When `ErrorContains` is acceptable** (rare cases only):
```go
// ACCEPTABLE — when error comes from external code you don't control
// and there's no sentinel error to check against
s.Require().ErrorContains(err, "connection refused")

// ACCEPTABLE — validation errors with dynamic content
s.Require().ErrorContains(err, "field 'email'")  // if no typed validation error exists
```

**Best practice — define sentinel errors for testability:**
```go
// In production code
var (
    ErrNotFound     = errors.New("not found")
    ErrInvalidInput = errors.New("invalid input")
    ErrUnauthorized = errors.New("unauthorized")
)

func GetUser(id string) (*User, error) {
    if id == "" {
        return nil, fmt.Errorf("user id required: %w", ErrInvalidInput)
    }
    // ...
    return nil, fmt.Errorf("user %s: %w", id, ErrNotFound)
}

// In tests — clean, robust assertions
s.Require().ErrorIs(err, ErrNotFound)
s.Require().ErrorIs(err, ErrInvalidInput)
```

### Full Mockery Example with Suite Hierarchy

```go
package service_test

import (
    "context"
    "testing"

    "github.com/rs/zerolog"
    "github.com/stretchr/testify/suite"
    "myproject/pkg/service"
    "myproject/pkg/storage/mocks"
)

// ServiceTestSuite is the package-level suite
type ServiceTestSuite struct {
    suite.Suite
}

func (s *ServiceTestSuite) getLogger() zerolog.Logger {
    return zerolog.Nop()
}

// UserServiceTestSuite is the file-level suite for user_service.go
type UserServiceTestSuite struct {
    ServiceTestSuite
    mockStore *mocks.Store
    svc       *service.UserService
}

func TestUserServiceTestSuite(t *testing.T) {
    suite.Run(t, new(UserServiceTestSuite))
}

func (s *UserServiceTestSuite) SetupTest() {
    s.mockStore = mocks.NewStore(s.T())
    s.svc = service.NewUserService(s.mockStore, s.getLogger())
}

func (s *UserServiceTestSuite) TestGetItem() {
    ctx := context.Background()
    expectedItem := &service.Item{ID: "123", Name: "test"}

    // Using expecter pattern (with-expecter: true in .mockery.yaml)
    s.mockStore.EXPECT().
        Get(ctx, "123").
        Return(expectedItem, nil)

    item, err := s.svc.Get(ctx, "123")

    s.Require().NoError(err)
    s.Require().Equal(expectedItem, item)
}

func (s *UserServiceTestSuite) TestGetItemNotFound() {
    ctx := context.Background()

    s.mockStore.EXPECT().
        Get(ctx, "unknown").
        Return(nil, storage.ErrNotFound)

    item, err := s.svc.Get(ctx, "unknown")

    s.Require().ErrorIs(err, storage.ErrNotFound)
    s.Require().Nil(item)
}
```

### Testing Concurrent Code with synctest

Use `testing/synctest` for deterministic concurrency testing:

```go
func (s *WorkerTestSuite) TestProcessesConcurrently() {
    synctest.Run(func() {
        w := worker.New()
        results := make(chan int, 3)

        go func() { results <- w.Process(1) }()
        go func() { results <- w.Process(2) }()
        go func() { results <- w.Process(3) }()

        synctest.Wait()

        s.Require().Len(results, 3)
    })
}

func (s *WorkerTestSuite) TestTimeoutBehaviour() {
    synctest.Run(func() {
        ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
        defer cancel()

        done := make(chan struct{})
        go func() {
            worker.DoWork(ctx)
            close(done)
        }()

        time.Sleep(6 * time.Second)
        synctest.Wait()

        select {
        case <-done:
            // expected: work cancelled due to timeout
        default:
            s.Require().Fail("expected work to be cancelled")
        }
    })
}
```

### Test Helpers

```go
func (s *UserServiceTestSuite) newTestServer() *httptest.Server {
    s.T().Helper()
    srv := httptest.NewServer(handler)
    s.T().Cleanup(func() {
        srv.Close()
    })
    return srv
}
```

---

## Backward Compatibility Testing

Verify that changes don't break existing consumers.

### Testing Deprecated Functions

```go
func (s *UserTestSuite) TestDeprecatedGetUserStillWorks() {
    user := GetUserWithoutError("123")
    s.Require().NotNil(user)
    s.Require().Equal("123", user.ID)
}

func (s *UserTestSuite) TestNewAndOldProduceSameResult() {
    oldResult := GetUserWithoutError("123")
    newResult, err := GetUser("123")

    s.Require().NoError(err)
    s.Require().Equal(oldResult.ID, newResult.ID)
    s.Require().Equal(oldResult.Name, newResult.Name)
}
```

### Testing API Contract Stability

```go
func (s *APITestSuite) TestResponseFormatUnchanged() {
    resp := s.client.Get("/api/users/123")

    s.Require().Contains(resp.Body, `"id"`)
    s.Require().Contains(resp.Body, `"name"`)
    s.Require().Contains(resp.Body, `"email"`)
}
```

### Testing Retry Behaviour

```go
func (s *ClientTestSuite) TestRetriesOnServerError() {
    attempts := 0
    srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        attempts++
        if attempts < 3 {
            w.WriteHeader(http.StatusServiceUnavailable)
            return
        }
        w.WriteHeader(http.StatusOK)
    }))
    defer srv.Close()

    client := NewClient(srv.URL)
    err := client.Fetch(context.Background(), "test")

    s.Require().NoError(err)
    s.Require().Equal(3, attempts) // retried twice before success
}

func (s *ClientTestSuite) TestRespectsContextTimeout() {
    srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        time.Sleep(100 * time.Millisecond)
        w.WriteHeader(http.StatusOK)
    }))
    defer srv.Close()

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
    defer cancel()

    client := NewClient(srv.URL)
    err := client.Fetch(ctx, "test")

    s.Require().ErrorIs(err, context.DeadlineExceeded)
}
```

---

## Testing Code with External Dependencies

**Always mock external dependencies.** The goal of unit tests is to verify YOUR code's logic, not the database driver or HTTP client.

### Mocking Database Operations

```go
// Code under test — service that uses a repository
type OrderService struct {
    repo   OrderRepository
    logger zerolog.Logger
}

type OrderRepository interface {
    FindByID(ctx context.Context, id OrderID) (*Order, error)
    Insert(ctx context.Context, order *Order) error
    Update(ctx context.Context, order *Order) error
}

// Tests — mock the repository, test the service logic
type OrderServiceTestSuite struct {
    ServiceTestSuite
    mockRepo *mocks.OrderRepository
    svc      *OrderService
}

func (s *OrderServiceTestSuite) SetupTest() {
    s.mockRepo = mocks.NewOrderRepository(s.T())
    s.svc = NewOrderService(s.mockRepo, s.getLogger())
}

func (s *OrderServiceTestSuite) TestCreateOrder_Success() {
    ctx := context.Background()
    order := &Order{Items: []Item{{ID: "item-1", Qty: 2}}}

    s.mockRepo.EXPECT().
        Insert(ctx, mock.MatchedBy(func(o *Order) bool {
            return len(o.Items) == 1 && o.Status == StatusPending
        })).
        Return(nil)

    err := s.svc.CreateOrder(ctx, order)

    s.Require().NoError(err)
}

func (s *OrderServiceTestSuite) TestCreateOrder_EmptyItems() {
    ctx := context.Background()
    order := &Order{Items: []Item{}}

    // Repository should NOT be called — validation fails first
    err := s.svc.CreateOrder(ctx, order)

    s.Require().ErrorIs(err, ErrInvalidOrder)  // use sentinel error, not string match
    s.mockRepo.AssertNotCalled(s.T(), "Insert")
}

func (s *OrderServiceTestSuite) TestCreateOrder_DBError() {
    ctx := context.Background()
    order := &Order{Items: []Item{{ID: "item-1", Qty: 2}}}

    s.mockRepo.EXPECT().
        Insert(ctx, mock.Anything).
        Return(repository.ErrConnectionFailed)

    err := s.svc.CreateOrder(ctx, order)

    s.Require().ErrorIs(err, repository.ErrConnectionFailed)  // check wrapped error
}
```

### Mocking MongoDB-style Operations

```go
// Interface for MongoDB collection operations
type MongoCollection interface {
    FindOne(ctx context.Context, filter any) SingleResult
    InsertOne(ctx context.Context, document any) (*InsertOneResult, error)
    UpdateOne(ctx context.Context, filter, update any) (*UpdateResult, error)
}

type SingleResult interface {
    Decode(v any) error
    Err() error
}

// Test with mocked collection
func (s *UserRepoTestSuite) TestFindByID_Success() {
    ctx := context.Background()
    expectedUser := &User{ID: "user-123", Name: "John"}

    mockResult := mocks.NewSingleResult(s.T())
    mockResult.EXPECT().Err().Return(nil)
    mockResult.EXPECT().Decode(mock.Anything).Run(func(v any) {
        *v.(*User) = *expectedUser
    }).Return(nil)

    s.mockCollection.EXPECT().
        FindOne(ctx, bson.M{"_id": "user-123"}).
        Return(mockResult)

    user, err := s.repo.FindByID(ctx, "user-123")

    s.Require().NoError(err)
    s.Require().Equal(expectedUser, user)
}

func (s *UserRepoTestSuite) TestFindByID_NotFound() {
    ctx := context.Background()

    mockResult := mocks.NewSingleResult(s.T())
    mockResult.EXPECT().Err().Return(mongo.ErrNoDocuments)

    s.mockCollection.EXPECT().
        FindOne(ctx, bson.M{"_id": "unknown"}).
        Return(mockResult)

    user, err := s.repo.FindByID(ctx, "unknown")

    s.Require().ErrorIs(err, ErrNotFound)
    s.Require().Nil(user)
}
```

### What to Test vs What to Skip

| Component | Test? | How |
|-----------|-------|-----|
| Service using repository | Yes | Mock repository interface |
| Repository implementation | Yes | Mock database driver/collection interface |
| Thin driver wrapper | Skip | No business logic, just delegation |
| Business logic with DB calls | Yes | Mock the DB interface at the boundary |
| Transaction coordination | Yes | Mock transaction interface, verify commit/rollback |

### Testing Transaction Patterns

#### Pattern 1: Fetch Before Transaction

```go
func (s *OrderTestSuite) TestFetchesUserBeforeTransaction() {
    s.mockUserService.EXPECT().
        Get(mock.Anything, "user-123").
        Return(&User{ID: "user-123", CanOrder: true}, nil)

    s.mockInventory.EXPECT().
        Check(mock.Anything, mock.Anything).
        Return(&Inventory{Available: true}, nil)

    err := s.svc.CreateOrder(context.Background(), "user-123", []Item{{ID: "item-1"}})
    s.Require().NoError(err)

    // Verify user was fetched BEFORE any DB operations
    s.mockUserService.AssertCalled(s.T(), "Get", mock.Anything, "user-123")
}

func (s *OrderTestSuite) TestFailsIfUserCheckFails() {
    s.mockUserService.EXPECT().
        Get(mock.Anything, "user-123").
        Return(nil, userservice.ErrServiceUnavailable)

    err := s.svc.CreateOrder(context.Background(), "user-123", []Item{})

    s.Require().ErrorIs(err, userservice.ErrServiceUnavailable)
    // DB should never be touched
}
```

#### Pattern 2: Call After Commit (Best Effort)

```go
func (s *OrderTestSuite) TestAnalyticsFailureDoesNotFailOrder() {
    s.mockAnalytics.EXPECT().
        Track(mock.Anything, "order.created", mock.Anything).
        Return(errors.New("analytics down"))

    err := s.svc.CreateOrder(context.Background(), validOrder)

    s.Require().NoError(err) // order succeeds despite analytics failure
}
```

#### Pattern 3: Transactional Outbox

```go
func (s *OrderTestSuite) TestWritesToOutboxInSameTransaction() {
    err := s.svc.CreateOrder(context.Background(), validOrder)
    s.Require().NoError(err)

    // Verify outbox message was created
    var outboxMsg OutboxMessage
    err = s.db.Get(&outboxMsg, "SELECT * FROM outbox WHERE topic = 'order.created'")
    s.Require().NoError(err)
    s.Require().Equal("order.created", outboxMsg.Topic)
}

func (s *OrderTestSuite) TestOutboxRollsBackWithOrder() {
    // Force order insert to fail
    s.mockDB.ForceError("orders", errors.New("constraint violation"))

    err := s.svc.CreateOrder(context.Background(), invalidOrder)
    s.Require().Error(err)

    // Verify NO outbox message exists (rolled back with order)
    count, _ := s.db.Count("SELECT COUNT(*) FROM outbox")
    s.Require().Equal(0, count)
}
```
