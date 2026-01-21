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
