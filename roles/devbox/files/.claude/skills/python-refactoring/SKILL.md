---
name: python-refactoring
description: >
  Code organization and refactoring patterns following PEP 20 (Zen of Python)
  principles. Use when discussing method extraction, abstraction levels, god
  methods, procedural code, or refactoring patterns. Triggers on: refactor,
  extract method, code organization, abstraction, god method, numbered comments,
  procedural code, SLAP, compose method.
---

# Python Refactoring & Code Organization

Refactoring patterns and code organization principles based on **[PEP 20 (Zen of Python)](https://peps.python.org/pep-0020/)** and **[Martin Fowler's Refactoring](https://python-patterns.guide/fowler-refactoring/)**.

---

## Guiding Principles (from PEP 20)

> **"Flat is better than nested."**
> **"Readability counts."**
> **"If the implementation is hard to explain, it's a bad idea."**

These principles guide us toward **code that explains itself** through structure, not comments.

---

## Anti-Pattern: Numbered Comments

### Recognition

Numbered comments (`# 1.`, `# 2.`, `# 3.`) violate **PEP 20's "Flat is better than nested"** and **"Readability counts"** principles. They indicate **missing method extractions**.

```python
# ❌ ANTI-PATTERN — violates "Flat is better than nested"
def process(self) -> None:
    # 1. Load configuration
    config = self.loader.load_config()

    # 2. Validate configuration
    if not config:
        raise ValueError("Invalid config")

    # 3. Transform data
    data = self.transformer.transform(config.data)

    # 4. Save results
    self.storage.save(data)
```

**Why this is wrong:**
- Comments explain WHAT (obvious from code)
- Each numbered step is a hidden abstraction
- Hard to test individual steps
- Violates **"If the implementation is hard to explain, it's a bad idea"**

### Refactoring: Extract Method

**Apply Martin Fowler's "Extract Method" refactoring:**

```python
# ✅ GOOD — self-documenting through method names
def process(self) -> None:
    config = self._load_and_validate_config()
    data = self._transform_data(config.data)
    self._save_results(data)

def _load_and_validate_config(self) -> Config:
    config = self.loader.load_config()
    if not config:
        raise ValueError("Invalid config")
    return config

def _transform_data(self, data: Data) -> ProcessedData:
    return self.transformer.transform(data)

def _save_results(self, data: ProcessedData) -> None:
    self.storage.save(data)
```

**Benefits:**
- No comments needed — method names explain intent (**"Readability counts"**)
- Each method has single responsibility
- Easy to test each step independently
- Follows **"Explicit is better than implicit"**

---

## Pattern: Single Level of Abstraction (SLAP)

**Principle:** Each function should operate at ONE level of abstraction.

From **PEP 20**: *"Flat is better than nested"* applies to abstraction levels too.

```python
# ❌ BAD — mixed abstraction levels
def execute_workflow(self, request_id: str) -> None:
    # High-level: load request
    request = self.repo.get(request_id)
    if not request:
        raise ValueError(f"Request not found: {request_id}")

    # Low-level: validate individual fields
    if not request.data.get("email"):
        raise ValueError("Email required")
    if "@" not in request.data["email"]:
        raise ValueError("Invalid email")

    # High-level: process
    result = self.processor.process(request)

    # Low-level: format and save
    formatted = {
        "id": result.id,
        "status": result.status.value,
        "timestamp": result.timestamp.isoformat(),
    }
    self.db.execute(
        "INSERT INTO results VALUES (%(id)s, %(status)s, %(timestamp)s)",
        formatted,
    )

# ✅ GOOD — single abstraction level (high-level orchestration)
def execute_workflow(self, request_id: str) -> None:
    request = self._load_request(request_id)
    self._validate_request(request)
    result = self._process_request(request)
    self._save_result(result)

def _load_request(self, request_id: str) -> Request:
    request = self.repo.get(request_id)
    if not request:
        raise ValueError(f"Request not found: {request_id}")
    return request

def _validate_request(self, request: Request) -> None:
    if not request.data.get("email"):
        raise ValueError("Email required")
    if "@" not in request.data["email"]:
        raise ValueError("Invalid email")

def _process_request(self, request: Request) -> Result:
    return self.processor.process(request)

def _save_result(self, result: Result) -> None:
    self.repo.save_result(result)
```

---

## Anti-Pattern: God Methods

### Recognition

**Signs of a god method:**
- \> 40-50 lines (rule of thumb from Clean Code)
- Multiple levels of nesting (> 3)
- Numbered comments
- Multiple unrelated responsibilities
- Hard to name without "and" in the name

```python
# ❌ ANTI-PATTERN — violates "If the implementation is hard to explain, it's a bad idea"
def process_and_sync_and_notify(self, data: dict[str, Any]) -> None:
    # ... 100+ lines of mixed concerns
    pass
```

### Refactoring: Compose Method

**From PEP 20:** *"There should be one-- and preferably only one --obvious way to do it."*

Break into methods with single, obvious purposes:

```python
# ✅ GOOD — each method has one obvious purpose
def process_data(self, data: dict[str, Any]) -> ProcessedData:
    validated = self._validate_input(data)
    return self._transform_to_domain(validated)

def sync_to_storage(self, processed: ProcessedData) -> SyncResult:
    return self.storage.save(processed)

def notify_completion(self, result: SyncResult) -> None:
    self.notifier.send(result)
```

---

## Refactoring Pattern: Extract Nested Block

**From PEP 20:** *"Flat is better than nested."*

```python
# ❌ BAD — deeply nested (violates "Flat is better than nested")
def sync_records(self, records: list[Record]) -> SyncResult:
    synced = []
    errors = []

    for record in records:
        if record.is_valid():
            try:
                if record.needs_transformation():
                    record = self._transform(record)

                if self.storage.exists(record.id):
                    self.storage.update(record)
                else:
                    self.storage.insert(record)
                synced.append(record.id)
            except StorageError as e:
                errors.append((record.id, str(e)))
        else:
            errors.append((record.id, "Invalid record"))

    return SyncResult(synced=synced, errors=errors)

# ✅ GOOD — flat structure through extraction
def sync_records(self, records: list[Record]) -> SyncResult:
    synced = []
    errors = []

    for record in records:
        result = self._sync_single_record(record)
        if result.success:
            synced.append(record.id)
        else:
            errors.append((record.id, result.error))

    return SyncResult(synced=synced, errors=errors)

def _sync_single_record(self, record: Record) -> SyncRecordResult:
    if not record.is_valid():
        return SyncRecordResult.failure("Invalid record")

    try:
        prepared = self._prepare_record(record)
        self._save_record(prepared)
        return SyncRecordResult.success()
    except StorageError as e:
        return SyncRecordResult.failure(str(e))

def _prepare_record(self, record: Record) -> Record:
    if record.needs_transformation():
        return self._transform(record)
    return record

def _save_record(self, record: Record) -> None:
    if self.storage.exists(record.id):
        self.storage.update(record)
    else:
        self.storage.insert(record)
```

---

## Refactoring Pattern: Extract Variable

**From PEP 20:** *"Explicit is better than implicit."*

Give complex expressions meaningful names:

```python
# ❌ IMPLICIT — what does this condition mean?
if item.created_at > datetime.now() - timedelta(days=7) and item.count == 0:
    self._send_reminder(item)

# ✅ EXPLICIT — named for clarity
is_recent = item.created_at > datetime.now() - timedelta(days=7)
has_no_activity = item.count == 0

if is_recent and has_no_activity:
    self._send_reminder(item)
```

---

## Compose Method Pattern

**Pattern:** High-level methods orchestrate, low-level methods implement.

Follows **PEP 8** guidance that functions should be small and focused.

```python
# ✅ GOOD — high-level orchestration (reads like a story)
class Processor:
    def execute(self, request_id: str) -> ProcessResult:
        request = self._load_request(request_id)
        self._validate_request(request)
        data = self._extract_data(request)
        result = self._process_data(data)
        self._persist_result(result)
        return ProcessResult(request_id=request_id, result=result)

    # Each method is 5-15 lines of focused logic
    def _load_request(self, request_id: str) -> Request:
        request = self.repo.get(request_id)
        if not request:
            raise RequestNotFoundError(request_id)
        return request

    def _validate_request(self, request: Request) -> None:
        if not request.payload:
            raise InvalidRequestError("Empty payload")
        if request.status != Status.PENDING:
            raise InvalidRequestError(f"Invalid status: {request.status}")

    # ... other focused methods
```

**Characteristics:**
- Main method reads like a table of contents
- Each submethod has single clear purpose
- Methods are 5-20 lines (rarely more)
- No numbered comments needed (**"Readability counts"**)

---

## Quick Reference: Refactoring Triggers

| Code Smell | Refactoring | PEP 20 Principle |
|-------------|-------------|------------------|
| Numbered comments | Extract each step to method | "Readability counts" |
| Comment explaining block | Extract block to named method | "Explicit > implicit" |
| Deep nesting (> 3) | Extract inner blocks | "Flat > nested" |
| Long method (> 40 lines) | Apply Compose Method | "Simple > complex" |
| Repeated code | Extract to shared method | "Don't repeat yourself" |
| Complex expression | Extract to named variable | "Explicit > implicit" |
| Method name has "and" | Split into multiple methods | One responsibility |
| Hard to test | Extract dependencies, reduce scope | Testability |

---

## Checklist: Well-Organized Code

Before submitting code, verify against **PEP 20** principles:

- [ ] No numbered comments (# 1., # 2., # 3.)
- [ ] Each method has single responsibility
- [ ] Method names clearly describe what they do
- [ ] No inline comments explaining WHAT (only WHY)
- [ ] No methods > 40 lines (rare exceptions for switch/match statements)
- [ ] No nesting > 3 levels deep ("Flat is better than nested")
- [ ] High-level methods orchestrate, low-level implement
- [ ] Code reads like well-written prose ("Readability counts")
- [ ] Implementation is easy to explain ("If hard to explain, it's a bad idea")

---

## Sources

- [PEP 20 - The Zen of Python](https://peps.python.org/pep-0020/)
- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Martin Fowler's Refactoring](https://python-patterns.guide/fowler-refactoring/)
