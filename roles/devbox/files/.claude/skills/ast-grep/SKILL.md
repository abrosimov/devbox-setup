---
name: ast-grep
description: >
  Structural AST code search and rewriting using ast-grep (Tree-sitter based).
  Use instead of grep when you need language-aware pattern matching — finding code
  by structure, not text. Complements LSP (which answers "where is X?") with
  pattern queries ("find all X that lack Y"). Use when performing structural search,
  code audits, or pattern-based refactoring across a codebase.
---

# ast-grep — Structural Code Search

ast-grep uses Tree-sitter to parse code into ASTs, then matches patterns against the tree structure. Unlike grep (text) or LSP (symbols), it finds **code shapes** — "all if-blocks missing an else", "all functions over 50 lines", "all error returns without wrapping".

## When to Use ast-grep vs Grep vs LSP

| Task | Tool | Why |
|------|------|-----|
| Find all callers of `ProcessOrder` | LSP `findReferences` | Semantic, zero false positives |
| Find "ProcessOrder" in comments/strings | Grep | Text content, not code structure |
| Find all functions returning `error` without wrapping | **ast-grep** | Structural pattern, not a symbol query |
| Find all `defer` statements not paired with a Close | **ast-grep** | Pattern across siblings in AST |
| Rename a symbol across the project | LSP | Semantic rename |
| Replace `fmt.Sprintf` with `log.Printf` in specific patterns | **ast-grep** | Structural find-and-replace |

## Core Commands

### Search for a pattern

```bash
ast-grep --pattern 'PATTERN' [--lang LANG] [PATH]
```

The pattern uses **metavariables** (`$VAR`, `$$$ARGS`) as wildcards:
- `$NAME` — matches any single AST node
- `$$$ARGS` — matches zero or more nodes (variadic)

### Examples

```bash
# Find all functions that call fmt.Errorf
ast-grep --pattern 'fmt.Errorf($$$ARGS)' --lang go .

# Find all if-statements with empty bodies
ast-grep --pattern 'if $COND { }' --lang go .

# Find React components with useEffect but no dependency array
ast-grep --pattern 'useEffect($FN)' --lang tsx .

# Find Python functions with bare except
ast-grep --pattern 'except:' --lang python .

# Find all async functions in TypeScript
ast-grep --pattern 'async function $NAME($$$PARAMS) { $$$BODY }' --lang ts .
```

### Structured output for parsing

```bash
ast-grep --pattern 'PATTERN' --lang LANG --json .
```

Returns JSON with file path, line/column, matched text, and metavariable bindings.

## YAML Rules (Advanced)

For complex queries combining multiple conditions, use YAML rules:

```bash
ast-grep scan --rule rule.yml [PATH]
```

Rule structure:

```yaml
id: descriptive-name
language: go
rule:
  pattern: if err != nil { return $ERR }
  not:
    inside:
      kind: function_declaration
      has:
        pattern: defer $$$
```

Key rule combinators: `all`, `any`, `not`, `inside`, `has`, `follows`, `precedes`.

Add `stopBy: end` to relational rules (`inside`, `has`) to search the entire subtree, not just direct children.

## Inspecting AST Structure

When a pattern doesn't match, inspect the actual AST:

```bash
ast-grep --pattern '$ROOT' --lang go FILE --json | head -50
```

Or for a specific snippet, use the parse subcommand to see the tree structure and identify the correct node kinds.

## Rewriting

```bash
ast-grep --pattern 'OLD_PATTERN' --rewrite 'NEW_PATTERN' --lang LANG [PATH]
```

Metavariables captured in the pattern are available in the rewrite:

```bash
# Replace fmt.Errorf with fmt.Errorf wrapped in a custom wrapper
ast-grep --pattern 'fmt.Errorf($$$ARGS)' --rewrite 'errors.Wrapf(fmt.Errorf($$$ARGS))' --lang go .
```

Add `--update-all` to apply changes in-place. Without it, prints a diff preview.

## Language Support

ast-grep supports 20+ languages via Tree-sitter: Go, Python, TypeScript, JavaScript, Rust, Java, C, C++, C#, Kotlin, Ruby, Swift, Lua, HTML, CSS, and more. Use `--lang` to specify (lowercase).

## Anti-Patterns

**Using ast-grep for simple text search**: If you're looking for a literal string or variable name, grep is faster and simpler. ast-grep adds value only when structure matters.

**Overly broad patterns**: `$NAME($$$ARGS)` matches every function call. Be specific about the structure you're targeting.

**Forgetting `--lang`**: Without it, ast-grep may misparse or skip files. Always specify the language.

**Not using `stopBy: end` in rules**: Relational matchers (`inside`, `has`) only check direct children by default. Add `stopBy: end` to traverse the full subtree.
