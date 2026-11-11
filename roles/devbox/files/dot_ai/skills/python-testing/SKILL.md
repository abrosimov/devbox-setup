---
name: python-testing
description: >
  Python testing patterns with pytest, fixtures, mocking, and parametrised tests.
  Use when writing or reviewing Python tests, creating fixtures, setting up mocks,
  or structuring parametrised test cases.
problem: "Python tests target private methods, string-match exceptions, or duplicate cases instead of parametrising through public API."
related: [python-engineer]
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

## Time: One Clock Per Test

**Every instant in a test derives from one clock.** Either all time is frozen — `time_machine.travel(..., tick=False)` (or `freezegun.freeze_time`) around the test and its fixtures, or a clock injected into the code under test — and literal dates are then safe; or every instant is an offset from one anchor read once (`now = datetime.now(UTC)` in a fixture). The defect is the mix: a literal `datetime(2026, 11, 2, ...)` next to a fixture, TTL, expiry or "last N days" window that reads the real clock passes until the calendar moves the literal outside that window.

- Freeze or anchor in the fixture, not only in the test body, so fixtures and test share the clock.
- Instants on a boundary (minute, bucket, day) are the anchor truncated and offset, not a copied wall-clock time.
- Time-relative behaviour gets a boundary case: just inside and just outside the window or TTL.
- Use aware datetimes in UTC; never compare against naive `datetime.now()` or strings formatted in the local zone.

Ask of every test: would it pass unchanged in a month, at 23:59:59, on 31 December, under `TZ=Asia/Tokyo`?

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
- [ ] One clock per test: no literal date next to fixtures, TTLs or windows that read the real clock; time-relative behaviour has a boundary case
- [ ] Tests pass: `[uv run] pytest`
- [ ] Coverage checked: `[uv run] pytest --cov=src`
