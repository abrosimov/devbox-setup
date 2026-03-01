---
name: python-testing
description: >
  Python testing patterns with pytest, fixtures, mocking, parametrized tests.
  Triggers on: test, testing, pytest, mock, fixture, parametrize, assertion.
---

# Python Testing Patterns

Idiomatic Python testing with pytest, fixtures, and mocking.

## Structural Rules

- Use class-based test suites (`class TestXxxService`) with fixtures as methods
- Parametrize instead of duplicating test methods
- Check exception types, not string messages (`pytest.raises(SpecificError)`)
- Test through public API — never test private methods directly

## What NOT to Test

Do not write tests for type system guarantees:
- Verifying a TypedDict is a dict
- Verifying a dataclass field returns what was set
- Verifying Pydantic accepts valid data

## Bug-Hunting Checklist

For EVERY function, systematically test:

| Category | Test Cases |
|----------|-----------|
| Empty | `""`, `None`, `[]`, `{}` |
| Single | One element, one character |
| Boundary | Max value, exactly at limit |
| Beyond | Limit+1, negative when positive expected |

## Project Tooling

Detect and use correct runner:

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
