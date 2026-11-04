---
note_id: "20261103150910"
created: 2026-11-03
language: en
type: research
subtype: annex
note_role: artifact
artifact_kind: research-report
publication_status: draft
authorship: agent
assistant: claude-code
project: fuzzing-tests-writer
aliases: ["R10"]
tags: [fuzzing, design/research]
topic: "claude plugin eval, skill-creator scripts, headless mode"
addresses: []
related: ["[[research-index]]", "[[research-corpus]]"]
---
# Eval tooling notes (from claude-code-guide agent; sources: code.claude.com/docs/en/plugin-evals.md, sub-agents.md, headless.md, cli-reference.md, skills.md, agent-sdk/subagents.md, anthropics/skills skill-creator)

- `claude plugin eval` targets a PLUGIN. A loose ~/.claude/agents/*.md is not a documented target -> package the fuzzing agent + skills as a plugin dir (agents/, skills/) for evals. Measures delegation: runs each prompt with/without plugin (WITH / W/OUT / delta); requires Claude Code >= 2.1.269.
- Case format: evals/<case>/prompt.md (frontmatter: name, description, tags, plugins, runs=3, expected_outcome (informational), model, max_turns=10, timeout_seconds=300, allowed_tools, append_system_prompt, env EVAL_*), evals/<case>/graders/<name>.md (type: regex | tool_used | tool_order | file_exists | llm | baseline; weight; arm; targets last_message|trace|files|{source:file,path}|mock_calls), optional case.yaml (schema_version "1.1"; context.scaffold_script, context.history_file, context.add_dirs; execution:).
- Fixture repos: context.scaffold_script writes the workspace (needs --scaffold, 120 s, minimal env). Running `go test` inside needs `--allow-tools "Bash(go test *)"`; granted Bash runs in OS sandbox (Linux: bubblewrap+socat), network limited -> vendor deps in fixtures. Alternative: ask the agent to write the test outcome to a file and grade that file.
- Report: aggregate-result.json (schemaVersion 1; aggregates.overallScore, casesPassed, meanDelta) + report.html. CI: `claude plugin eval . --trust-plugin --json results.json --threshold 0.8 --model M --judge-model M --no-publish --max-cost-usd N`; exit 0 pass / 1 fail / 2 partial.
- LLM judge noisy on long artefacts -> prefer deterministic graders (file_exists, regex on produced file, tool_used) for harness output; llm grader for the report/decision prose.
- Default 3 runs/case/arm; pin --model in CI; --ablation none halves cost when delta not needed; hold-out via --tag (not a documented feature) — e.g. tag `holdout`, run on release only.
- skill-creator scripts: trigger_evals.json ({query, should_trigger}, ~20 queries, near-miss negatives) + run_loop.py (60/40 train/test, 3 runs/query) for description trigger accuracy; evals.json (skill_name, evals[{id,prompt,expected_output,files}]) + grader/comparator for output quality; these are iteration tools, not CI gates. Repo already wires them: `make eval-skills`, `make improve-skills`, `make validate-skills`.
- Headless driving: `claude -p --bare --agents <file> --add-dir <skills dir> --allowedTools ... --output-format json --json-schema ... --max-turns --max-budget-usd`, run from inside the fixture repo. --bare ignores ~/.claude/agents and ~/.claude/skills unless passed explicitly; needs ANTHROPIC_API_KEY. `--agent` with -p not explicitly documented.
- Sub-agent frontmatter supports: tools, disallowedTools, model, permissionMode, skills, mcpServers, hooks, maxTurns, memory, effort, isolation, omitClaudeMd. Restrict spawnable subagents with tools: Agent(a, b).
- /skill-doctor = usage/cost report, not a behavioural check.
