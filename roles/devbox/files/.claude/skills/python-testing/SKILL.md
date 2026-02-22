---
name: python-testing
description: >
  Python testing patterns with pytest, fixtures, mocking, parametrized tests.
  Triggers on: test, testing, pytest, mock, fixture, parametrize, assertion.
---

# Python Testing Patterns

Idiomatic Python testing with pytest, fixtures, and mocking.

## Test File Structure

```python
"""Tests for user service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from mypackage.service import UserService
from mypackage.models import User
from mypackage.exceptions import UserNotFoundError


class TestUserService:
    """Test suite for UserService."""

    @pytest.fixture
    def mock_repo(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_repo):
        return UserService(repository=mock_repo)
```

## Pytest Class-Based Suites

**Preferred structure for organised tests:**

```python
class TestUserService:

    @pytest.fixture
    def mock_repo(self):
        repo = Mock()
        repo.find_by_id.return_value = None
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        return UserService(repository=mock_repo)

    def test_get_user_success(self, service, mock_repo):
        expected = User(id="123", name="John")
        mock_repo.find_by_id.return_value = expected

        result = service.get_user("123")

        assert result == expected
        mock_repo.find_by_id.assert_called_once_with("123")

    def test_get_user_not_found(self, service, mock_repo):
        mock_repo.find_by_id.return_value = None

        with pytest.raises(UserNotFoundError):
            service.get_user("unknown")
```

## Parametrized Tests

**Always prefer parametrized tests over separate test methods:**

```python
@pytest.mark.parametrize("email,should_raise", [
    ("user@example.com", False),
    ("name@domain.org", False),
    ("invalid", True),
    ("", True),
    ("@nodomain", True),
    ("user@", True),
    ("user@@example.com", True),
])
def test_validate_email(self, service, email, should_raise):
    if should_raise:
        with pytest.raises(ValidationError):
            service.validate_email(email)
    else:
        assert service.validate_email(email) is True
```

### Parametrize with IDs

```python
@pytest.mark.parametrize("input_val,expected", [
    pytest.param("hello", "HELLO", id="lowercase"),
    pytest.param("HELLO", "HELLO", id="already_upper"),
    pytest.param("", "", id="empty_string"),
    pytest.param("Hello World", "HELLO WORLD", id="mixed_case_with_space"),
])
def test_uppercase(input_val, expected):
    assert uppercase(input_val) == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("x,y,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, -100, 0),
])
def test_add(x, y, expected):
    assert add(x, y) == expected
```

## Fixtures

### Basic Fixtures

```python
@pytest.fixture
def sample_user():
    return User(id="123", name="John", email="john@example.com")


@pytest.fixture
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()


def test_save_user(db_connection, sample_user):
    db_connection.save(sample_user)
    assert db_connection.get("123") == sample_user
```

### Fixture Scopes

```python
@pytest.fixture(scope="function")  # Default — fresh for each test
def mock_repo():
    return Mock()


@pytest.fixture(scope="class")  # Shared across class
def expensive_resource():
    return create_expensive_resource()


@pytest.fixture(scope="module")  # Shared across module
def db_connection():
    return create_connection()


@pytest.fixture(scope="session")  # Shared across entire test session
def app_config():
    return load_config()
```

### conftest.py for Shared Fixtures

```python
# tests/conftest.py
import pytest

@pytest.fixture
def mock_http_client():
    return Mock()

@pytest.fixture
def api_client(mock_http_client):
    return APIClient(http_client=mock_http_client)
```

## Mocking

### Basic Mocking

```python
def test_create_user_success(self, service, mock_repo):
    mock_repo.insert.return_value = None

    service.create_user(User(name="John"))

    mock_repo.insert.assert_called_once()
    saved_user = mock_repo.insert.call_args[0][0]
    assert saved_user.name == "John"
```

### Mock Side Effects

```python
def test_retry_on_failure(self, service, mock_repo):
    mock_repo.find_by_id.side_effect = [
        ConnectionError("failed"),
        ConnectionError("failed"),
        User(id="123", name="John"),
    ]

    result = service.get_user_with_retry("123")

    assert result.name == "John"
    assert mock_repo.find_by_id.call_count == 3
```

### Patching

```python
@patch("mypackage.service.external_api")
def test_external_call(mock_api, service):
    mock_api.fetch.return_value = {"data": "value"}

    result = service.get_external_data()

    assert result == {"data": "value"}
    mock_api.fetch.assert_called_once()


def test_external_call_context(self, service):
    with patch("mypackage.service.external_api") as mock_api:
        mock_api.fetch.return_value = {"data": "value"}

        result = service.get_external_data()

        assert result == {"data": "value"}
```

### pytest-mock (mocker fixture)

```python
def test_with_mocker(self, service, mocker):
    mock_client = mocker.patch("mypackage.service.http_client")
    mock_client.get.return_value = {"id": "123"}

    result = service.fetch_data("http://example.com")

    assert result == {"id": "123"}
    mock_client.get.assert_called_once_with("http://example.com")
```

## Async Testing

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_fetch(self, service, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = {"data": "value"}
    service._client = mock_client

    result = await service.fetch_async("http://example.com")

    assert result == {"data": "value"}
    mock_client.get.assert_awaited_once_with("http://example.com")


@pytest.mark.asyncio
async def test_async_timeout(self, service):
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            service.slow_operation(),
            timeout=0.001
        )


@pytest.mark.asyncio
async def test_concurrent_operations(self, service, mocker):
    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = {"status": "ok"}
    service._client = mock_client

    results = await asyncio.gather(
        service.fetch("/a"),
        service.fetch("/b"),
        service.fetch("/c"),
    )

    assert len(results) == 3
    assert mock_client.get.await_count == 3
```

## Error Assertions

**Use exception types, not strings:**

```python
# ❌ BAD — fragile string comparison
def test_user_not_found():
    with pytest.raises(Exception) as exc_info:
        get_user("unknown")
    assert "not found" in str(exc_info.value)

# ✅ GOOD — check exception type
def test_user_not_found():
    with pytest.raises(UserNotFoundError):
        get_user("unknown")

# ✅ GOOD — check type with match pattern
def test_validation_error():
    with pytest.raises(ValidationError, match="email"):
        validate({"email": "invalid"})
```

## Bug-Hunting Scenarios

For EVERY function, systematically test:

### Input Boundaries

| Category | Test Cases |
|----------|-----------|
| Empty | `""`, `None`, `[]`, `{}` |
| Single | One element, one character |
| Boundary | Max value, exactly at limit |
| Beyond | Limit+1, negative when positive expected |

### Type-Specific Edge Cases

| Type | Edge Cases |
|------|-----------|
| Strings | `""`, whitespace-only, unicode, very long, `\n`, `\t` |
| Numbers | `0`, `-1`, `sys.maxsize`, `float('inf')`, `float('nan')` |
| Lists | `None` vs `[]`, single element, duplicates |
| Dicts | `None` vs `{}`, missing key |
| Datetime | `datetime.min`, `datetime.max`, timezone-naive vs aware |
| Optional | `None`, valid value, default value |

### Error Paths

```python
def test_error_chaining(self, service, mock_repo):
    mock_repo.find_by_id.side_effect = DatabaseError("connection failed")

    with pytest.raises(ServiceError) as exc_info:
        service.get_user("123")

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, DatabaseError)
```

## Testing HTTP/Retry Behaviour

```python
class TestHTTPClientRetry:

    def test_retries_on_connection_error(self, mocker):
        mock_get = mocker.patch("mymodule.client.session.get")
        mock_get.side_effect = [
            ConnectionError(),
            ConnectionError(),
            Mock(status_code=200, json=lambda: {"id": "123"}),
        ]

        result = fetch_user("123")

        assert result == {"id": "123"}
        assert mock_get.call_count == 3

    def test_raises_after_max_retries(self, mocker):
        mock_get = mocker.patch("mymodule.client.session.get")
        mock_get.side_effect = ConnectionError()

        with pytest.raises(ConnectionError):
            fetch_user("123")

        assert mock_get.call_count == 5  # max retries
```

## Testing Deprecation Warnings

```python
import warnings

def test_deprecated_function_emits_warning(self):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        result = deprecated_get_user("123")

    assert len(w) == 1
    assert issubclass(w[0].category, DeprecationWarning)
    assert "get_user_by_id" in str(w[0].message)


def test_deprecated_and_new_produce_same_result(self):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old_result = deprecated_get_user("123")

    new_result = get_user_by_id("123")

    assert old_result.id == new_result.id
```

## What NOT to Test

### Type System Guarantees

```python
# ❌ FORBIDDEN — tests Python's dict
def test_typed_dict():
    filters: LabelFilters = {"namespace": "mlops"}
    assert isinstance(filters, dict)

# ❌ FORBIDDEN — tests dataclass field access
def test_user_dto_fields():
    user = UserDTO(name="test", email="test@example.com")
    assert user.name == "test"

# ❌ FORBIDDEN — tests Pydantic accepts valid data
def test_config_model_valid():
    config = Config(port=8080, host="localhost")
    assert config.port == 8080
```

### Private Methods

Test through public API:

```python
# ❌ BAD — testing private method directly
def test_validate_internal():
    svc = UserService(repo)
    result = svc._validate_email("test@example.com")

# ✅ GOOD — test through public API
def test_create_user_validates_email(self, service):
    with pytest.raises(ValidationError, match="invalid email"):
        service.create_user(name="John", email="invalid")
```

## Test Execution Commands

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific file
uv run pytest tests/test_service.py

# Run specific test
uv run pytest tests/test_service.py::TestUserService::test_get_user_success

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run only marked tests
uv run pytest -m slow
uv run pytest -m "not slow"

# Run with parallel execution
uv run pytest -n auto

# Stop on first failure
uv run pytest -x

# Show local variables in tracebacks
uv run pytest -l
```

## Project Tooling

Detect and use correct runner:

```bash
# Check project type
ls uv.lock poetry.lock requirements.txt 2>/dev/null
```

| Files Found | Run Tests With |
|-------------|----------------|
| `uv.lock` | `uv run pytest` |
| `poetry.lock` | `poetry run pytest` |
| `requirements.txt` only | `pytest` |

## Checklist Before Completion

- [ ] All public functions have tests
- [ ] All error paths are tested (every `raise`)
- [ ] Parametrized tests used where appropriate
- [ ] Mocks verify call expectations
- [ ] Edge cases covered (None, empty, boundary)
- [ ] Async code tested with `@pytest.mark.asyncio`
- [ ] No tests for type system guarantees
- [ ] Exception types tested, not string messages
- [ ] Tests pass: `[uv run] pytest`
- [ ] Coverage checked: `[uv run] pytest --cov=src`
