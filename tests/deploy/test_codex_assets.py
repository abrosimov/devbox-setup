from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CODEX_ROOT = REPO_ROOT / "roles/devbox/files/dot_codex"
AI_ROOT = REPO_ROOT / "roles/devbox/files/dot_ai"
CODEX_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/codex.yml"
CODEX_TASKS = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"
SHARED_TASKS = REPO_ROOT / "roles/devbox/tasks/install_configs.yml"
CORE_AUTHORITY = AI_ROOT / "USER_AUTHORITY_PROTOCOL.md"
CORE_LOOKUP = "/dot_ai/USER_AUTHORITY_PROTOCOL.md"

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
    "formal-model-writer",
    "freshness-auditor",
    "fuzzing-tests-writer",
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
VALIDATION_AGENTS = {
    "build-resolver-go",
    "code-reviewer",
    "formal-model-writer",
    "integration-tests-writer-go",
    "integration-tests-writer-python",
    "observability-engineer",
    "refactor-cleaner",
    "software-engineer-frontend",
    "software-engineer-go",
    "software-engineer-python",
    "unit-test-writer",
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


def copy_content(tasks_path: Path, name: str) -> str:
    tasks: object = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    assert isinstance(tasks, list)
    task = next(task for task in tasks if isinstance(task, dict) and task.get("name") == name)
    content = task["ansible.builtin.copy"]["content"]
    assert isinstance(content, str)
    return content


def test_global_agents_file_fits_codex_instruction_budget() -> None:
    authority = b"\n".join((CORE_AUTHORITY.read_bytes(), (CODEX_ROOT / "AGENTS.md").read_bytes()))
    assert len(authority) < 32 * 1024
    text = authority.decode()
    assert "For explanation, review, research" in text
    assert "**diagnose** request" in text
    assert "For change, fix, build" in text
    assert "explicit confirmation" in text
    assert "`fpf-thinking` and `narrative-thinking` skills only when the user names them" in text
    assert "Consult the registry before you change anything yourself." in text
    assert "Apply the core's §6 registry check before the first edit" in text
    assert "the `software-engineer-*` agents own the code of their stack" in text
    assert "Pre-authorised local validation" in text
    assert "the stack skills name the exact commands and flags" in text
    assert "without asking the user whether to proceed" in text
    assert "diagnose-and-repair" in text


def test_validation_agents_do_not_ask_before_local_checks() -> None:
    for name in VALIDATION_AGENTS:
        agent = " ".join((CODEX_ROOT / f"agents/{name}.toml").read_text(encoding="utf-8").split())
        assert "repository-local validation is pre-authorised" in agent
        assert "without asking the user whether to proceed" in agent


def test_fpf_bundle_is_self_contained_and_vendor_neutral() -> None:
    fpf_root = AI_ROOT / "skills/fpf-thinking"
    narrative_skill = AI_ROOT / "skills/narrative-thinking/SKILL.md"
    references = fpf_root / "references"

    assert (references / "FPF-Spec.md").is_file()
    narrative = "Narrativization-and-Narrative-Studies-Principles-Framework.md"
    assert (references / "DPFs" / narrative).is_file()

    skill_text = "\n".join(
        [
            (fpf_root / "SKILL.md").read_text(encoding="utf-8"),
            narrative_skill.read_text(encoding="utf-8"),
        ]
    )
    assert "~/.claude" not in skill_text
    assert "/techne-" not in skill_text
    assert "mcp__sequentialthinking" not in skill_text
    assert "private chain-of-thought" not in skill_text


def test_thinking_skills_are_explicit_invocation_only() -> None:
    for skill in ("fpf-thinking", "narrative-thinking"):
        skill_root = AI_ROOT / "skills" / skill
        frontmatter_text = (skill_root / "SKILL.md").read_text(encoding="utf-8").split("---\n")[1]
        frontmatter: object = yaml.safe_load(frontmatter_text)
        assert isinstance(frontmatter, dict)
        assert frontmatter["disable-model-invocation"] is True

        openai: object = yaml.safe_load(
            (skill_root / "agents/openai.yaml").read_text(encoding="utf-8")
        )
        assert isinstance(openai, dict)
        assert openai["policy"]["allow_implicit_invocation"] is False


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
    assert "goimports -local <module-path>" in agent
    assert "goimports -local <module-path>" in skill_text
    assert "standard fallback" not in skill_text
    for marker in ("Claude", "/techne-", "~/.claude", "OPUS", "SONNET"):
        assert marker not in skill_text


def test_diagnostic_repair_loop_is_shared_and_vendor_neutral() -> None:
    defaults = CODEX_DEFAULTS.read_text(encoding="utf-8")
    shared_authority = (AI_ROOT / "USER_AUTHORITY_PROTOCOL.md").read_text(encoding="utf-8")
    skill = (AI_ROOT / "skills/diagnose-and-repair/SKILL.md").read_text(encoding="utf-8")

    assert "  - diagnose-and-repair\n" in defaults
    assert "`diagnose-and-repair` skill" in shared_authority
    assert "inventory -> plan -> repair batch -> rebaseline" in skill
    assert "two materially different evidence-based repair attempts" in skill
    for marker in ("Claude", "Codex", "Antigravity", "/techne-", "~/.claude", "~/.codex"):
        assert marker not in skill


def test_codex_deploy_selects_fpf_skills_authority_and_agents() -> None:
    defaults = CODEX_DEFAULTS.read_text(encoding="utf-8")
    tasks = CODEX_TASKS.read_text(encoding="utf-8")

    assert "  - fpf-thinking\n" in defaults
    assert "  - narrative-thinking\n" in defaults
    for agent in EXPECTED_AGENTS:
        assert f"  - {agent}\n" in defaults

    authority = copy_content(CODEX_TASKS, "Install Codex global authority protocol")
    assert authority.index(CORE_LOOKUP) < authority.index("/dot_codex/AGENTS.md")
    assert "files/dot_codex/agents/{{ item }}.toml" in tasks


def test_claude_and_agy_root_rules_assemble_core_and_adapter() -> None:
    claude = copy_content(
        SHARED_TASKS, "Deploy shared AI root rules (USER_AUTHORITY_PROTOCOL) to Claude"
    )
    agy = copy_content(
        SHARED_TASKS, "Deploy shared AI root rules (USER_AUTHORITY_PROTOCOL) to Antigravity"
    )

    assert claude.index(CORE_LOOKUP) < claude.index("/files/dot_claude/CLAUDE_ADAPTER.md")
    assert agy.index(CORE_LOOKUP) < agy.index("/files/dot_agy/GEMINI_ADAPTER.md")
    assert agy.startswith("---\ntrigger: always_on\n---\n")
