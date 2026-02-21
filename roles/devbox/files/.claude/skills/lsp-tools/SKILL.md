---
name: lsp-tools
description: >
  LSP code intelligence for semantic navigation, refactoring, and diagnostics.
  Teaches agents when and how to use Claude Code's built-in LSP tools instead of
  grep-based text search. Covers the coordinate bridge pattern, decision tree,
  mandatory constraints, and workflow recipes.
  Triggers on: refactor, rename, find references, find callers, find implementations,
  go to definition, type info, call hierarchy, impact analysis, LSP, language server.
---

# LSP Code Intelligence

Claude Code has built-in LSP support via plugins. When available, LSP provides **semantic** code understanding — exact references, type info, call graphs — not text matching.

## Tool Reference

### Navigation

| Operation | Parameters | Returns | Use When |
|-----------|-----------|---------|----------|
| `goToDefinition` | `filePath`, `line`, `character` | Location(s) of definition | Understanding what a symbol IS |
| `goToImplementation` | `filePath`, `line`, `character` | Implementation locations | Finding concrete types behind interfaces |
| `findReferences` | `filePath`, `line`, `character` | All reference locations | Impact analysis before changes |

### Inspection

| Operation | Parameters | Returns | Use When |
|-----------|-----------|---------|----------|
| `hover` | `filePath`, `line`, `character` | Type signature, docs | Quick type check without navigating |
| `documentSymbol` | `filePath` | Hierarchical symbol tree | Understanding file structure (NO line/char needed) |
| `workspaceSymbol` | `query` (string) | Matching symbols across project | Finding a symbol when you don't know which file |

### Call Graph

| Operation | Parameters | Returns | Use When |
|-----------|-----------|---------|----------|
| `prepareCallHierarchy` | `filePath`, `line`, `character` | Call hierarchy item | Setup for incoming/outgoing calls |
| `incomingCalls` | `filePath`, `line`, `character` | All callers | "Who calls this function?" |
| `outgoingCalls` | `filePath`, `line`, `character` | All callees | "What does this function depend on?" |

### Passive: Automatic Diagnostics

After every file edit, language servers emit diagnostics (type errors, missing imports, unused variables). Check these after editing — they appear automatically.

**All coordinates are 1-based** (matching editor display). `documentSymbol` and `workspaceSymbol` do not require line/character.

---

## The Coordinate Bridge

LSP operations need `file:line:character`. Agents think in symbol names. Bridge the gap:

### Path 1: Known file, unknown position

```
documentSymbol(filePath) → scan symbol tree → extract line:character → feed to LSP operation
```

Use `documentSymbol` first. It returns every function, class, method, variable with positions. Find your target in the tree, use its coordinates.

### Path 2: Unknown file, known symbol name

```
workspaceSymbol(query) → get filePath:line:character → feed to LSP operation
```

Use `workspaceSymbol` with a partial name. It returns matches across the entire project with locations. Pick the right match, use its coordinates.

### Path 3: Approximate from prior grep

If you already grepped and found `file.go:42: func ProcessOrder(`, use line 42, character at the symbol start.

**Rule**: Always resolve coordinates BEFORE calling navigation/call-graph operations. Calling them with wrong coordinates wastes tokens on errors.

---

## Decision Tree: LSP vs Grep vs Read

| Task | Best Tool | Why |
|------|-----------|-----|
| All semantic references to a symbol | `findReferences` | No false positives from comments/strings/similar names |
| Interface/abstract implementations | `goToImplementation` | Semantic — finds all concrete types |
| Type signature or docs | `hover` | Targeted, no file read needed |
| File structure overview | `documentSymbol` | Hierarchical, saves tokens vs reading whole file |
| Call graph / blast radius | `incomingCalls` / `outgoingCalls` | Complete caller/callee chain |
| Find symbol across project | `workspaceSymbol` | Semantic, grouped by kind |
| Literal text in comments or strings | Grep | LSP indexes code structure, not text content |
| Config / non-code files (YAML, JSON, env) | Grep / Read | LSP only works on source code |
| File discovery by name pattern | Glob | LSP does not search file names |
| Log messages, error strings | Grep | These are string literals, not symbols |
| Security pattern scanning | Grep | Regex-based, not semantic |

### The Hybrid Pattern

For maximum accuracy, combine both:

1. **Grep** to find approximate location (file + line)
2. **LSP** to get semantic info at that location (type, references, callers)

This is especially useful when `workspaceSymbol` returns too many results or the symbol name is ambiguous.

---

## Three Mandatory Constraints

### 1. No modifying unfamiliar code without `goToDefinition` first

Before changing a function, type, or method you haven't read — navigate to its definition. Understand what it is, what it returns, what it depends on.

### 2. No refactoring without `findReferences` impact analysis

Before renaming, moving, or changing a public API — find all references. Know the blast radius. Every caller site is a potential breakage point.

### 3. No claiming success without checking diagnostics

After making changes, check the automatic diagnostics output. Type errors, missing imports, unused variables — fix them before reporting completion.

---

## Workflow Recipes

### Understanding Unfamiliar Code

```
1. documentSymbol(file)          → get the structure without reading implementation
2. hover(file, line, char)       → understand types and signatures
3. goToDefinition(file, line, char) → follow dependency chains
4. findReferences(file, line, char) → see where it's used
```

### Safe Refactoring

```
1. findReferences(target)        → blast radius — every caller/user
2. incomingCalls(target)         → who calls this?
3. Make the change
4. Check diagnostics             → verify no errors introduced
5. Re-run findReferences         → confirm all call sites still valid
```

### Tracing Data Flow

```
1. workspaceSymbol("UserDTO")    → find the type definition
2. goToDefinition(result)        → read the type
3. findReferences(type)          → see where it's created/consumed
4. outgoingCalls(transformer)    → what does the transformation depend on?
```

### Pre-Edit Type Check

```
1. hover(file, line, char)       → verify the type before changing it
2. goToImplementation(interface)  → find all concrete types to update
3. Make changes across all implementations
4. Check diagnostics
```

---

## Anti-Patterns

**Calling LSP without coordinates**: Attempting `goToDefinition` or `findReferences` without first resolving the target's position. Always use `documentSymbol`, `workspaceSymbol`, or grep to get coordinates first.

**Unbounded reference searches**: Using `findReferences` on ubiquitous symbols like `ctx`, `err`, `self`, `this`, `i`. This floods context with hundreds of results. Scope by targeting the specific method or type instead.

**Ignoring auto-diagnostics**: After editing, language servers report errors automatically. Ignoring these and reporting "done" leads to broken code. Always check and fix diagnostics after edits.

**Reading entire files for structure**: Using `Read` on a 500-line file to understand its structure. Use `documentSymbol` instead — it returns the symbol tree in a fraction of the tokens.

**Grep for semantic queries**: Using `grep -r "ProcessOrder"` to find all callers when `findReferences` gives exact results with zero false positives. This is especially wasteful in large codebases where grep returns matches from comments, strings, and similarly-named symbols.

**Defaulting to grep out of habit**: Agents naturally prefer grep because it always works. When LSP is available, prefer it for semantic queries. Reserve grep for literal text, comments, and config files.

---

## Error Handling & Fallback

```
LSP operation fails
  → "No LSP server available": server not started or language not supported
    → Retry once after brief pause (cold start)
    → If still fails: fall back to Grep (flag reduced accuracy)
  → Wrong coordinates: symbol not at expected position
    → Use documentSymbol to re-resolve coordinates
    → Try workspaceSymbol as alternative
  → Empty result: symbol has no references/implementations
    → This may be correct (dead code, leaf node)
    → Verify with grep as cross-check
```

**Cold start**: Language servers need startup time (seconds to tens of seconds depending on project size). If the first LSP call fails, `documentSymbol` is a good warmup operation — it exercises the server with lower cost than other operations.

---

## Language-Specific Notes

### Go (gopls)

- Best LSP CLI support of any language server
- Needs `go.work` for multi-module workspaces
- Slow to start on large GOPATH directories
- `goToImplementation` is excellent for finding interface implementors
- Does not work in files with `import "C"` under cross-platform constraints

### Python (pyright)

- Strong type analysis but NO CLI navigation (diagnostics only via CLI)
- May need `PYRIGHT_MEMORY_LIMIT=4096` for large projects
- Slow with huge `TypedDict` classes (combinatorial overload synthesis)
- `hover` provides detailed type signatures including inferred types

### TypeScript (vtsls)

- Can crash on malformed files (EPIPE/SIGTRAP)
- Memory issues on very large projects
- Excellent `documentSymbol` for React component structure
- `goToDefinition` follows through type aliases and re-exports

### Rust (rust-analyzer)

- Requires `Cargo.toml` at workspace root
- Slow on very large workspaces
- Rich `hover` output including trait bounds and lifetimes

---

## Performance

| Metric | Grep | LSP |
|--------|------|-----|
| Reference search (100 files) | ~2000+ tokens, many false positives | ~500 tokens, exact matches |
| Speed | ~45 seconds | ~50ms |
| False positive rate | High (comments, strings, similar names) | Zero (semantic) |
| Memory overhead | None | 200-500MB per language server |

LSP is **900x faster** and **75% more token-efficient** for semantic queries. Use it.
