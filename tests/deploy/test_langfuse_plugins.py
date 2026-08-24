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
CLAUDE_MARKETPLACE = (
    REPO_ROOT
    / "roles/devbox/files/dot_claude/marketplaces/langfuse-observability"
    / ".claude-plugin/marketplace.json"
)
CLAUDE_TASKS = REPO_ROOT / "roles/devbox/tasks/apply_configs.yml"
CODEX_DEFAULTS = REPO_ROOT / "roles/devbox/defaults/main/codex.yml"
CODEX_CONFIG = REPO_ROOT / "roles/devbox/files/dot_codex/config.toml.j2"
CODEX_LANGFUSE = REPO_ROOT / "roles/devbox/files/dot_codex/langfuse.json.j2"
CODEX_TASKS = REPO_ROOT / "roles/devbox/tasks/install_codex_configs.yml"

FULL_SHA = re.compile(r"[0-9a-f]{40}")
LOOPBACK_URL = "http://127.0.0.1:14318"


def _tasks_by_name(path: Path) -> dict[str, dict[str, object]]:
    tasks = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {task["name"]: task for task in tasks}


def test_claude_lock_marketplace_uses_an_immutable_upstream_revision() -> None:
    marketplace = json.loads(CLAUDE_MARKETPLACE.read_text(encoding="utf-8"))
    plugin = marketplace["plugins"][0]
    source = plugin["source"]

    assert marketplace["name"] == "langfuse-observability"
    assert plugin["name"] == "langfuse-observability"
    assert source["source"] == "github"
    assert source["repo"] == "langfuse/claude-observability-plugin"
    assert source["ref"] == "main"
    assert FULL_SHA.fullmatch(source["sha"])


def test_claude_deploys_and_enables_the_locked_marketplace() -> None:
    defaults = yaml.safe_load(CLAUDE_DEFAULTS.read_text(encoding="utf-8"))
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))

    assert "marketplaces" in defaults["devbox_claude_managed_dirs"]
    assert {
        "path": "marketplaces/langfuse-observability",
        "name": "langfuse-observability",
        "declare_in_settings": False,
    } in defaults["devbox_claude_plugin_marketplaces"]
    assert {
        "name": "langfuse-observability",
        "marketplace": "langfuse-observability",
    } in defaults["devbox_claude_plugins"]
    assert settings["enabledPlugins"]["langfuse-observability@langfuse-observability"] is True


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
    )

    assert all("cloud.langfuse.com" not in source for source in sources)
    assert all("/api/public/otel" not in source for source in sources)
