# LSP Integration — Future Approaches

Research date: 2026-03-10. This file tracks future options and deferred work.

## Implemented

- **Approach 1**: Native LSP plugins (gopls, pyright, typescript) — installed via playbook, `enabledPlugins` in settings.json
- **Approach 5**: ast-grep — brew package + Claude skill
- **LSP enforcement (P0-P2)**: `ENABLE_LSP_TOOL` env, `enabledPlugins`, workflow CLAUDE.md instructions, `lsp-navigation` alwaysApply skill, LSP tool added to 8 agents, navigation protocol in 3 SE agents

## Deferred (P3): PreToolUse Grep Blocker

A PreToolUse hook that inspects Grep patterns and blocks symbol lookups (e.g., `func ProcessOrder`, `class UserService`, `def handle_`), returning `{"decision": "block", "reason": "Use LSP workspaceSymbol instead of Grep for symbol lookups"}`. Strongest enforcement but high false-positive risk. Start in advisory mode before graduating to blocking. See research notes below.

## Deferred: LSP Startup Reliability (.lsp.json)

Official plugins don't expose `startupTimeout` configuration. Race condition ([#31468](https://github.com/anthropics/claude-code/issues/31468)) can cause "No server available" on first call. If LSP fails on cold start, Claude falls back to Grep for the entire session. Workarounds:
- Create a custom plugin wrapping gopls/pyright with `startupTimeout: 10000` and `restartOnCrash: true`
- Or wait for official plugins to add these settings (tracked upstream)

---

---

## Approach 2: Community LSP Plugin Marketplace (Piebald-AI)

**Effort: Low | Impact: High**

[Piebald-AI/claude-code-lsps](https://github.com/Piebald-AI/claude-code-lsps) provides additional LSP plugins beyond the official Anthropic marketplace. Covers more languages and sometimes has better defaults.

Install: `/plugin install gopls@claude-code-lsps`

**When to adopt**: If official plugins don't cover a language we need (e.g., Kotlin, Ruby, PHP). The playbook already handles `claude plugin install` generically — just add the marketplace to `claude_plugin_marketplaces` and entries to `claude_plugins`.

---

## Approach 3: MCP-LSP Bridge Servers

**Effort: Medium | Impact: High**

For environments where the native plugin system doesn't work, or for languages without official plugins, MCP-LSP bridges expose LSP capabilities as MCP tools.

Key projects:
- **[mcp-language-server](https://github.com/isaacphi/mcp-language-server)** (Go) — supports gopls, pyright, typescript-language-server, rust-analyzer, clangd
- **[mcpls](https://github.com/bug-ops/mcpls)** (Rust) — universal bridge, any LSP server
- **[lsp-mcp](https://github.com/jonrad/lsp-mcp)** — Docker-based, easy deployment

**Integration path**: Register via `claude mcp add` using existing `mcp_docker_servers` or `mcp_script_servers` patterns in `defaults/main/claude.yml`.

**When to adopt**: If native plugins break in devcontainers or sandboxed environments where the plugin system can't start LSP servers directly.

---

## Approach 4: Project-Level `.lsp.json` Configuration

**Effort: Low | Impact: Medium**

Claude Code reads `.lsp.json` from the project root to configure language servers per-project. Fine-grained control over which LSP servers start, their args, extension mappings, and restart behavior.

**Integration path**: Template `.lsp.json` files for common project types (Go, Python, TypeScript) and deploy via local overlay or project scaffolding.

**When to adopt**: When different projects need different LSP configurations (e.g., monorepo with multiple languages, project-specific pyright settings).

---

## Approach 6: cclsp (Claude Code LSP Bridge)

**Effort: Medium | Impact: Medium**

[cclsp](https://github.com/ktnyt/cclsp) is purpose-built for Claude Code. It bridges LSP capabilities into MCP, providing:
- Instant symbol navigation
- Complete reference finding
- Safe symbol renaming
- Universal language support via single MCP server

**When to adopt**: When managing many languages and want a single MCP server wrapping all language servers instead of per-language plugins.

---

## Approach 7: Probe (Hybrid ripgrep + Tree-sitter + Ranking)

**Effort: Medium | Impact: High (for large codebases)**

[Probe](https://github.com/probelabs/probe) combines ripgrep speed with Tree-sitter AST parsing and smart ranking (BM25, TF-IDF). Zero-setup, no embeddings needed.

Key differentiator: Token-aware budgeting — knows how much context window you have and returns results that fit. Built-in agent and MCP server integration.

Install: `cargo install probe-ai` or brew. Register as MCP server.

**When to adopt**: When working on large monorepos where grep returns too much noise and LSP alone isn't enough for discovery-type queries.

Also see: **[RAGex](https://github.com/jbenshetler/mcp-ragex)** — MCP server with semantic (RAG), symbolic (tree-sitter), and regex (ripgrep) search modes. Air-gapped, local processing.

---

## Approach 8: LSAP (Language Server Agent Protocol)

**Effort: High | Impact: High (architectural)**

[LSAP](https://github.com/lsp-client/LSAP) wraps LSP's coordinate-based API into semantic queries designed for agents. Instead of "give me hover at file:line:col", you say "find all references to function X" and LSAP orchestrates the multi-step LSP dance internally, returning a consolidated Markdown report.

Addresses José Valim's critique that LSP APIs are awkward for agents (designed for humans clicking on line 47, not for semantic queries). Still early-stage.

**When to adopt**: When it matures past experimental stage. Watch for stable releases and adoption by other agent frameworks.

---

## Comparison Matrix

| # | Approach | Effort | RAM | Languages | Query Type | Best For |
|---|----------|--------|-----|-----------|------------|----------|
| 2 | Community Marketplace | Low | 200-500MB/lang | More | Semantic | Gap-filling |
| 3 | MCP-LSP Bridge | Medium | Same | Any LSP | Semantic | Non-plugin envs |
| 4 | .lsp.json per-project | Low | Same | Any | Semantic | Per-project tuning |
| 6 | cclsp | Medium | Moderate | Universal | Semantic | Multi-lang projects |
| 7 | Probe | Medium | Low | Any | Hybrid (text+AST+rank) | Large codebases |
| 8 | LSAP | High | TBD | Any LSP | Agent-native semantic | Future architecture |

---

## Related Tools

- **[Code-Graph-RAG](https://github.com/vitali87/code-graph-rag)** — Knowledge graph over codebases using Tree-sitter, MCP server for Claude Code
- **[Codemogger](https://github.com/glommer/codemogger)** — SQLite-based code index with vector + full-text search, no server needed
- **[vscode-mcp](https://github.com/tjx666/vscode-mcp)** — VSCode MCP Bridge for real-time LSP diagnostics from editor

## Sources

- [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [LSP: Secret Weapon for AI Coding Tools](https://amirteymoori.com/lsp-language-server-protocol-ai-coding-tools/)
- [How LSP Integrations Transform Coding Agents](https://tech-talk.the-experts.nl/give-your-ai-coding-agent-eyes-how-lsp-integration-transform-coding-agents-4ccae8444929)
- [ast-grep + AI Tools Guide](https://ast-grep.github.io/advanced/prompting.html)
- [Probe - AI-friendly Code Search](https://probeai.dev)
