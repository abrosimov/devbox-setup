from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml
from jinja2 import StrictUndefined, Template

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/claude.yml"
CLAUDE_SETTINGS = REPO_ROOT / "roles/devbox/files/dot_claude/settings.json"
CLAUDE_HOOKS = REPO_ROOT / "roles/devbox/files/dot_claude/hooks.json"
CLAUDE_BIN = REPO_ROOT / "roles/devbox/files/dot_claude/bin"
VENDORED_HOOK = CLAUDE_BIN / "vendor/langfuse_hook.py"
CLAUDE_TASKS = REPO_ROOT / "roles/devbox/tasks/apply_configs.yml"
CODEX_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/codex.yml"
CODEX_CONFIG = REPO_ROOT / "roles/devbox/files/dot_codex/config.toml.j2"
CODEX_LANGFUSE = REPO_ROOT / "roles/devbox/files/dot_codex/langfuse.json.j2"
CODEX_TASKS = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"
AGY_BIN = REPO_ROOT / "roles/devbox/files/dot_agy/bin"
AGY_VENDORED_HOOK = AGY_BIN / "vendor/langfuse_hook.py"
AGY_HOOKS = REPO_ROOT / "roles/devbox/files/dot_agy/config/hooks.json.j2"
AGY_FISH = REPO_ROOT / "roles/devbox/files/.config/fish/functions/agy.fish"

FULL_SHA = re.compile(r"[0-9a-f]{40}")
LOOPBACK_URL = "http://127.0.0.1:14318"


def _tasks_by_name(path: Path) -> dict[str, dict[str, object]]:
    tasks = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {task["name"]: task for task in tasks}


def test_claude_langfuse_hook_is_vendored_rather_than_installed_as_a_plugin() -> None:
    """Upstream ships the hook as `uv run --script` with PEP 723 inline metadata.

    That resolves dependencies at invocation time into an environment under
    UV_CACHE_DIR, which points into /tmp so uv stays writable inside the Bash
    sandbox — where macOS tmp_cleaner erodes it after three days. The hook is
    vendored instead; see roles/devbox/files/dot_claude/bin/vendor/README.md.
    """
    defaults = yaml.safe_load(CLAUDE_DEFAULTS.read_text(encoding="utf-8"))
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    assert VENDORED_HOOK.is_file()
    assert all(
        entry["name"] != "langfuse-observability"
        for entry in defaults["devbox_claude_plugin_marketplaces"]
    )
    assert all(
        entry["name"] != "langfuse-observability" for entry in defaults["devbox_claude_plugins"]
    )
    assert "langfuse-observability@langfuse-observability" not in settings["enabledPlugins"]
    assert "langfuse-observability" not in settings["extraKnownMarketplaces"]


def test_claude_langfuse_hook_runs_from_the_pinned_bin_venv() -> None:
    hooks = json.loads(CLAUDE_HOOKS.read_text(encoding="utf-8"))
    project = tomllib.loads((CLAUDE_BIN / "pyproject.toml").read_text(encoding="utf-8"))
    lock = (CLAUDE_BIN / "uv.lock").read_text(encoding="utf-8")

    assert any(dep.startswith("langfuse") for dep in project["project"]["dependencies"])
    assert 'name = "langfuse"' in lock

    expected = "~/.claude/bin/.venv/bin/python ~/.claude/bin/vendor/langfuse_hook.py"
    for event in ("Stop", "SessionEnd"):
        commands = [hook["command"] for group in hooks["hooks"][event] for hook in group["hooks"]]
        assert expected in commands


def test_claude_provisioning_is_idempotent_and_fail_closed() -> None:
    tasks = _tasks_by_name(CLAUDE_TASKS)
    add = tasks["Add Claude Code plugin marketplaces"]
    install = tasks["Install Claude Code plugins (user scope)"]
    verify = tasks["Assert required Claude Code plugins are installed and enabled"]

    assert add["changed_when"] is True
    assert install["changed_when"] is True
    assert "failed_when" not in add
    assert "failed_when" not in install
    assert "not ansible_check_mode" in add["when"]
    assert "not ansible_check_mode" in install["when"]
    assert "--scope" in add["ansible.builtin.command"]["argv"]
    assert "--scope" in install["ansible.builtin.command"]["argv"]
    assert "not ansible_check_mode" in verify["when"]


def test_claude_langfuse_runtime_is_loopback_only_and_media_free() -> None:
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    environment = settings["env"]

    assert environment["CC_LANGFUSE_BASE_URL"] == LOOPBACK_URL
    assert environment["CC_LANGFUSE_PUBLIC_KEY"] == "otelbox-local-public"
    assert environment["CC_LANGFUSE_SECRET_KEY"] == environment["CC_LANGFUSE_PUBLIC_KEY"].replace(
        "public", "secret"
    )
    assert environment["CC_LANGFUSE_CAPTURE_IMAGES"] == "false"
    assert environment["LANGFUSE_TRACING_ENVIRONMENT"] == "{{ devbox_active_profile }}"
    assert not environment["CC_LANGFUSE_PUBLIC_KEY"].startswith("pk-lf-")
    assert not environment["CC_LANGFUSE_SECRET_KEY"].startswith("sk-lf-")


def test_codex_marketplace_and_plugin_are_pinned_and_enabled() -> None:
    defaults = yaml.safe_load(CODEX_DEFAULTS.read_text(encoding="utf-8"))
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    marketplace = defaults["devbox_codex_plugin_marketplaces"][0]
    plugin = defaults["devbox_codex_plugins"][0]

    assert marketplace["name"] == "codex-observability-plugin"
    assert marketplace["repo"] == "langfuse/codex-observability-plugin"
    assert FULL_SHA.fullmatch(marketplace["ref"])
    assert plugin == {
        "name": "tracing",
        "marketplace": "codex-observability-plugin",
        "version": "0.1.0",
    }
    assert config["features"]["hooks"] is True
    assert config["plugins"]["tracing@codex-observability-plugin"]["enabled"] is True


def test_codex_native_trace_export_is_disabled_without_disabling_logs_or_metrics() -> None:
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    telemetry = config["otel"]

    assert telemetry["trace_exporter"] == "none"
    assert telemetry["exporter"]["otlp-grpc"]["endpoint"] == "http://127.0.0.1:4317"
    assert telemetry["metrics_exporter"]["otlp-grpc"]["endpoint"] == ("http://127.0.0.1:4317")
    assert telemetry["log_user_prompt"] is True


def test_codex_provisioning_installs_the_pin_without_bypassing_hook_trust() -> None:
    tasks = _tasks_by_name(CODEX_TASKS)
    runtime = tasks["Install Codex Langfuse runtime configuration"]
    add = tasks["Add pinned Codex plugin marketplaces"]
    inspect_revision = tasks["Inspect pinned Codex marketplace revisions"]
    install = tasks["Install Codex plugins"]

    assert runtime["ansible.builtin.template"]["mode"] == "0600"
    assert "--ref" in add["ansible.builtin.command"]["argv"]
    assert "{{ item.ref }}" in add["ansible.builtin.command"]["argv"]
    assert "not ansible_check_mode" in add["when"]
    assert "rev-parse" in inspect_revision["ansible.builtin.command"]["argv"]
    assert "not ansible_check_mode" in install["when"]
    assert "hook trust" not in CODEX_TASKS.read_text(encoding="utf-8").lower()


def test_codex_langfuse_runtime_uses_only_dummy_loopback_credentials() -> None:
    rendered = Template(
        CODEX_LANGFUSE.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(devbox_active_profile="personal")
    config = json.loads(rendered)

    assert config["enabled"] is True
    assert config["public_key"] == "otelbox-local-public"
    assert config["secret_key"] == config["public_key"].replace("public", "secret")
    assert config["base_url"] == LOOPBACK_URL
    assert config["environment"] == "personal"
    assert config["debug"] is False
    assert config["fail_on_error"] is False
    assert not config["public_key"].startswith("pk-lf-")
    assert not config["secret_key"].startswith("sk-lf-")


def test_repo_owned_langfuse_configuration_has_no_remote_ingestion_url() -> None:
    sources = (
        CLAUDE_SETTINGS.read_text(encoding="utf-8"),
        CODEX_LANGFUSE.read_text(encoding="utf-8"),
        AGY_FISH.read_text(encoding="utf-8"),
    )

    assert all("cloud.langfuse.com" not in source for source in sources)
    assert all("/api/public/otel" not in source for source in sources)


def test_all_engines_stamp_otelbox_telemetry_class_llm() -> None:
    """Every engine must tag its OTLP telemetry with otelbox.telemetry.class=llm
    so the gateway can route LLM traces to Langfuse."""
    claude_settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    assert claude_settings["env"]["OTEL_RESOURCE_ATTRIBUTES"] == "otelbox.telemetry.class=llm"

    agy_fish = AGY_FISH.read_text(encoding="utf-8")
    assert "OTEL_RESOURCE_ATTRIBUTES=otelbox.telemetry.class=llm" in agy_fish


def test_codex_otel_resource_attributes_are_forward_declared() -> None:
    """Codex does not yet honour [otel] resource_attributes (openai/codex#30987).

    The key is declared in config.toml so it activates automatically once the
    feature lands.  Until then the edge collector's resource/langfuse_plugins
    processor stamps the attribute on Langfuse-bound traces.
    """
    codex_config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    assert codex_config["otel"]["resource_attributes"]["otelbox.telemetry.class"] == "llm"


def test_codex_hooks_run_from_a_pinned_venv_rather_than_ambient_python() -> None:
    """`/usr/bin/env python3` hands the hook to whatever PATH resolves first."""
    config = tomllib.loads(CODEX_CONFIG.read_text(encoding="utf-8"))
    project = tomllib.loads(
        (REPO_ROOT / "roles/devbox/files/dot_codex/bin/pyproject.toml").read_text(encoding="utf-8")
    )

    assert project["project"]["requires-python"] == ">=3.11"
    assert (REPO_ROOT / "roles/devbox/files/dot_codex/bin/uv.lock").is_file()

    commands = [
        hook["command"]
        for groups in config["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]
    assert commands
    assert all(command.startswith("~/.codex/bin/.venv/bin/python ") for command in commands)


def test_codex_bin_sync_preserves_the_venv_it_bootstraps() -> None:
    tasks = _tasks_by_name(CODEX_TASKS)
    sync = tasks["Sync Codex bin directory"]
    bootstrap = tasks["Bootstrap Codex hooks venv via uv sync"]

    assert "--exclude=.venv" in sync["ansible.posix.synchronize"]["rsync_opts"]
    assert sync["ansible.posix.synchronize"]["delete"] is True
    assert "sync --frozen --no-dev" in bootstrap["ansible.builtin.command"]["cmd"]
    assert bootstrap["ansible.builtin.command"]["chdir"].endswith("/bin")


# ── Antigravity CLI (agy) ──────────────────────────────────────────────


def test_agy_langfuse_hook_is_vendored_and_identical_to_claude() -> None:
    """Agy uses an unmodified copy of the Claude langfuse hook."""
    assert AGY_VENDORED_HOOK.is_file()
    assert AGY_VENDORED_HOOK.read_bytes() == VENDORED_HOOK.read_bytes()


def test_agy_langfuse_hook_runs_from_the_pinned_bin_venv() -> None:
    rendered = Template(
        AGY_HOOKS.read_text(encoding="utf-8"),
        undefined=StrictUndefined,
    ).render(lookup=lambda _plugin, _key: "/home/testuser")
    hooks = json.loads(rendered)

    project = tomllib.loads((AGY_BIN / "pyproject.toml").read_text(encoding="utf-8"))
    lock = (AGY_BIN / "uv.lock").read_text(encoding="utf-8")

    assert any(dep.startswith("langfuse") for dep in project["project"]["dependencies"])
    assert 'name = "langfuse"' in lock

    expected_suffix = "bin/.venv/bin/python"
    expected_script = "bin/vendor/langfuse_hook.py"
    hook_entry = hooks["langfuse_hook"]
    assert hook_entry["event"] == "Stop"
    assert hook_entry["enabled"] is True
    assert expected_suffix in hook_entry["handler"]["command"]
    assert expected_script in hook_entry["handler"]["command"]


def test_agy_langfuse_env_vars_are_loopback_only() -> None:
    fish = AGY_FISH.read_text(encoding="utf-8")

    assert "CC_LANGFUSE_BASE_URL=http://127.0.0.1:14318" in fish
    assert "CC_LANGFUSE_PUBLIC_KEY=otelbox-local-public" in fish
    assert "CC_LANGFUSE_SECRET_KEY=otelbox-local-secret" in fish
    assert "CC_LANGFUSE_CAPTURE_IMAGES=false" in fish
    assert "CC_LANGFUSE_STATE_DIR=" in fish
    assert ".gemini/antigravity-cli/state" in fish
    assert "pk-lf-" not in fish
    assert "sk-lf-" not in fish


def test_agy_langfuse_state_dir_is_isolated_from_claude() -> None:
    """Agy must not share state with Claude's ~/.claude/state/."""
    fish = AGY_FISH.read_text(encoding="utf-8")
    assert "CC_LANGFUSE_STATE_DIR=" in fish
    assert ".claude/state" not in fish.split("CC_LANGFUSE_STATE_DIR=")[1].split()[0]
