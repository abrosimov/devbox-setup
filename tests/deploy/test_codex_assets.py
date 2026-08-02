from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_ROOT = REPO_ROOT / "roles/devbox/files/dot_codex"
AI_ROOT = REPO_ROOT / "roles/devbox/files/dot_ai"
CODEX_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/codex.yml"
CODEX_TASKS = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"

EXPECTED_AGENTS = {
    "agent-builder",
    "api-designer",
    "architect",
    "build-resolver-go",
    "code-reviewer",
    "consistency-checker",
    "content-reviewer",
    "database-designer",
    "database-reviewer",
    "designer",
    "doc-updater",
    "domain-expert",
    "domain-modeller",
    "focus-coach",
    "freshness-auditor",
    "implementation-planner",
    "integration-tests-writer-go",
    "integration-tests-writer-python",
    "meta-reviewer",
    "observability-engineer",
    "refactor-cleaner",
    "skill-builder",
    "software-engineer-frontend",
    "software-engineer-go",
    "software-engineer-python",
    "tdd-guide",
    "technical-product-manager",
    "unit-test-writer",
}
READ_ONLY_AGENTS = {
    "architect",
    "code-reviewer",
    "consistency-checker",
    "content-reviewer",
    "database-reviewer",
    "focus-coach",
    "freshness-auditor",
    "meta-reviewer",
}
CLIENT_SPECIFIC_MARKERS = (
    "Anthropic",
    "AskUserQuestion",
    "/techne-",
    "~/.claude",
    "permissionMode",
    'model = "opus"',
    'model = "sonnet"',
)


def test_codex_agents_use_native_toml_contract() -> None:
    agent_files = sorted((CODEX_ROOT / "agents").glob("*.toml"))
    assert {path.stem for path in agent_files} == EXPECTED_AGENTS

    for path in agent_files:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
        assert parsed["name"] == path.stem
        assert parsed["description"].strip()
        assert parsed["developer_instructions"].strip()
        assert "model" not in parsed
        if path.stem in READ_ONLY_AGENTS:
            assert parsed["sandbox_mode"] == "read-only"
        else:
            assert "sandbox_mode" not in parsed


def test_codex_agent_set_covers_every_shared_role() -> None:
    source_files = sorted((AI_ROOT / "agents").glob("*.md"))
    source_names = set()
    for path in source_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        name_line = next(line for line in lines[1:] if line.startswith("name: "))
        source_names.add(name_line.removeprefix("name: "))

    assert source_names == EXPECTED_AGENTS


def test_codex_prompts_do_not_leak_claude_protocol() -> None:
    prompt_files = [CODEX_ROOT / "AGENTS.md", *(CODEX_ROOT / "agents").glob("*.toml")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in prompt_files)

    for marker in CLIENT_SPECIFIC_MARKERS:
        assert marker not in combined


def test_global_agents_file_fits_codex_instruction_budget() -> None:
    authority = (CODEX_ROOT / "AGENTS.md").read_bytes()
    assert len(authority) < 32 * 1024
    text = authority.decode()
    assert "For explanation, review, diagnosis" in text
    assert "For change, fix, build" in text
    assert "explicit confirmation" in text
    assert "fpf-thinking" in text


def test_fpf_bundle_is_self_contained_and_vendor_neutral() -> None:
    fpf_root = AI_ROOT / "skills/fpf-thinking"
    narrative_skill = AI_ROOT / "skills/narrative-thinking/SKILL.md"
    references = fpf_root / "references"

    assert (references / "FPF-Spec.md").is_file()
    assert (references / "Narrativization-and-Narrative-Studies-Principles-Framework.md").is_file()

    skill_text = "\n".join(
        [
            (fpf_root / "SKILL.md").read_text(encoding="utf-8"),
            narrative_skill.read_text(encoding="utf-8"),
        ]
    )
    assert "~/.claude" not in skill_text
    assert "/techne-" not in skill_text
    assert "mcp__sequentialthinking" not in skill_text
    assert "private chain-of-thought" in skill_text


def test_go_engineer_is_deployed_and_vendor_neutral() -> None:
    defaults = CODEX_DEFAULTS.read_text(encoding="utf-8")
    agent = (CODEX_ROOT / "agents/software-engineer-go.toml").read_text(encoding="utf-8")
    skill_root = AI_ROOT / "skills/go-engineer"
    skill_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (skill_root / "SKILL.md", skill_root / "scripts/complexity_check.sh")
    )

    assert "  - go-engineer\n" in defaults
    assert "Use go-engineer as the primary Go implementation workflow" in agent
    for marker in ("Claude", "/techne-", "~/.claude", "OPUS", "SONNET"):
        assert marker not in skill_text


def test_codex_deploy_selects_fpf_skills_authority_and_agents() -> None:
    defaults = CODEX_DEFAULTS.read_text(encoding="utf-8")
    tasks = CODEX_TASKS.read_text(encoding="utf-8")

    assert "  - fpf-thinking\n" in defaults
    assert "  - narrative-thinking\n" in defaults
    for agent in EXPECTED_AGENTS:
        assert f"  - {agent}\n" in defaults

    assert "files/dot_codex/AGENTS.md" in tasks
    assert "files/dot_codex/agents/{{ item }}.toml" in tasks
