---
name: code-comments
description: >
  Rules for code comments and documentation. Covers narration comments (forbidden),
  acceptable WHY comments, and docstring policies.
triggers:
  - comment
  - comments
  - docstring
  - narration
  - "//"
  - "#"
  - '"""'
  - "/* */"
  - "# type:"
  - documentation
problem: "Narration and stale docstrings accumulate in code without a strict WHY-only rule and enforceable verbosity ceiling."
related: [code-writing-protocols, lint-discipline]
---

# Code Comments Policy

**Default stance: NO comments.** Code should be self-documenting through clear names, types, and structure.

## Zero Tolerance: Narration Comments

NEVER write comments that describe what code does. Forbidden: `# Get user from database`, `// Create new connection`, `# Check if valid`, `// Initialize the service`.

### The Four-Way Deletion Test

**Before writing ANY comment, check all four sources of meaning.** A comment earns its place only if NONE of them already convey what the comment would say:

1. **The function or test name** — does the name already say it?
2. **The code body** — do function calls, variable names, and fixture names already say it?
3. **The assertions or return values** — does what the code DOES already say it?
4. **The file or module context** — does the file naming, neighbouring code, or module docstring already say it?

If ANY one source carries the content, the comment is duplication. **Cut.**

Default lean: **drop**. The longer you have to justify keeping a comment, the more likely it should be dropped. Only keep when you can name in one phrase the unique signal the comment carries that all four sources miss.

## Acceptable Comments

Comments are justified ONLY when explaining something **non-obvious**: WHY something is done, import/init ordering constraints, non-obvious side effects, thread safety caveats, complex protocols.

```python
self.__repo.save(order)  # Must save before notification -- order ID required
```

**NEVER** use section dividers or markers: `# --- Configuration ---`, `// === Tests ===`, `// Private methods`.

## Verbosity Ceiling

The deletion test decides *whether* a comment exists. The **compression test** decides how long it gets.

- **1 line is the default.** A WHY comment fits on one line ~80% of the time.
- **2-3 lines** are allowed only when documenting a genuinely subtle invariant where one line would lose load-bearing context. Each extra line must earn its place.
- **4+ lines = NOT a comment.** It is documentation. Move it to one of:
  - A docstring (only when justified by the Docstring Policy below)
  - An ADR (for architecture decisions)
  - The PR description (for change-specific context)
  - A module-level `# WARNING:` block (for non-obvious module-wide invariants)

For every comment ≥2 lines, ask: *"What's the minimum that prevents misuse?"* Then cut everything else.

## What's NOT WHY (Common Drift)

These look like WHY but are filler. Cut them.

| Drift | Example | Why it's drift | Fix |
|---|---|---|---|
| **Speculative / futurist** | `# if someone later adds an admin rotation endpoint that re-encrypts within a request, include encrypted_value in the key` | Speculation is not a constraint. The hypothetical doesn't exist. | Cut entirely. Document when the actual code is added. |
| **Mechanism over-explanation** | `# A single HTTP request can touch the same blueprint multiple times; without this cache each touch issues a Vault round-trip` | Code shows the mechanism. Repeating it adds no information. | Keep only the WHY: `# Per-request cache to avoid repeat Vault decrypts.` |
| **Restating the code** | `# Pop both alias ("type") and python-attr name ("secrets_type"): request bodies serialise with by_alias=True...` | The pop calls are visible. The serialisation is one line of context, not three. | `# pop both alias and attr name to keep the immutability guard` |
| **Recursive WHY** | `# We do X because Y, because Z, because W...` | Each "because" drifts further from the load-bearing reason. | One level deep: `# We do X because Y.` |
| **Branch-label narration** | `if not self.__vault.is_encryption_enabled():` `    # FF off — alias holds plaintext as-is` | The branch condition is self-labelling. The `if not is_encryption_enabled()` already says "FF off". Repeating the label inside the branch is narration in disguise. | Cut the in-branch label. If a WHY exists (e.g. about stale ciphers), place it *above* the `if`, not inside it. |

## Before / After Examples

**Bloated WHY (avoid):**
```python
# Per-request memoisation cache attribute name on flask.g. A single HTTP
# request can touch the same blueprint multiple times (e.g. knowledge
# benchmark validate + RunFacade merge across datasets); without this cache
# each touch issues a fresh Vault transit_decrypt round-trip. Outside a
# Flask request context (Celery tasks, scripts) the cache is disabled and
# every call falls through to Vault.
#
# Cache key is (blueprint.id, secrets_type) — encrypted_value is NOT part of
# the key. This assumes a blueprint is not re-encrypted (key rotation, secret
# update) within a single request. No such flow exists today; if one is
# added (e.g. an admin rotation endpoint that reads → re-encrypts → reads),
# include encrypted_value in the key or invalidate on write.
_DECRYPTION_CACHE_ATTR = "_blueprint_decryption_cache"
```

**Compressed WHY (target):**
```python
# Per-request cache to avoid repeat Vault decrypts. Disabled outside Flask.
# Key omits encrypted_value — invalidate if you add in-request re-encryption.
_DECRYPTION_CACHE_ATTR = "_blueprint_decryption_cache"
```

Same load-bearing content (cache scope, key composition, invalidation trigger). 83% shorter. The future-speculation is gone — when the speculative flow is actually added, the comment can be updated then.

## Comments in Tests

Test names are first-class documentation. Tests follow the convention `test_<scenario>_<expected_behaviour>` (or equivalent per stack), so the name itself carries scenario + outcome. This makes test comments **redundant by default** — far more often than production comments are.

### Anti-patterns in tests (cut on sight)

| Pattern | Example | Why it's drift |
|---|---|---|
| **Bare AAA / GWT markers** | `# Arrange` / `# given` with no prose | Conveys zero information beyond a blank line — the blank line already separates phases. |
| **Given-prose paraphrasing the test name** | `# given — alias-type-change is sent` under `test_update_with_alias_type_change_raises_immutable_error` | Test name already encodes the scenario. The "given" comment is name duplication. |
| **Assertion paraphrase** | `# X must be Y` followed by `assert x == y` | The assertion IS the statement. Repeating it in prose adds nothing. |

### Test comments that earn their place

- **Regression markers** — one sentence with a ticket reference: `# Regression for MLOPS-7330: <bug summary>`. Prevents future contributors deleting the test as "testing an impossible edge case".
- **Test-infrastructure rationale** — non-obvious mock or fixture setup that the names don't make obvious (e.g. why a mock returns a specific shape rather than the default).
- **Invariant the test enforces but doesn't make textually obvious** — ordering constraints, race-condition setups, transaction boundaries.

### Project convention: given-when-then

If project conventions specify "tests follow given-when-then structure", honour the **intent** (chronological organisation) by ordering the test body chronologically — set-up, action, assertions — separated by blank lines. Do NOT honour the **mechanic** (literal `# given` / `# when` / `# then` labels) unless the prose attached carries content the test name doesn't.

Bare convention labels are a common drift. Cut them.

## Docstring Policy

**Default: NO docstrings.** Names, types, and structure ARE the documentation.

Rare exceptions requiring justification: import/init ordering, non-obvious side effects, thread safety, complex protocols, external library public APIs where users rely on `help()`.

Go doc comments: follow standard conventions but still avoid narration.

## Self-Review Checklist

Before completing any code task:

1. **Did I add ANY comments that describe WHAT the code does?** If YES → Remove them NOW
2. **For each comment I kept, name the unique signal it carries — what does it tell a reader that the function/test name, code body, assertions, AND file context do NOT already convey?** If I cannot name a unique signal in one phrase, the comment is duplication. **Delete it NOW.**
3. **For each surviving comment, can I cut it by ≥50% without losing the load-bearing part?** If YES → Cut it NOW
4. **Does any comment contain speculation ("if someone later adds X..."), mechanism over-explanation, or restate visible code?** If YES → Strip those parts NOW
5. **Are there any section markers or dividers?** If YES → Remove them NOW

Only proceed after all five checks pass.
