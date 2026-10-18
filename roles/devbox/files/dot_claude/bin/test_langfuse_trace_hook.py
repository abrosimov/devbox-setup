from __future__ import annotations

import importlib.util
import os
import sys
from typing import TYPE_CHECKING

import langfuse_trace_hook
import pytest

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

LOOPBACK_URL = "http://127.0.0.1:14318"
OPERATOR_ENVIRONMENT = {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-operator",
    "LANGFUSE_SECRET_KEY": "sk-lf-operator",
    "LANGFUSE_HOST": "https://langfuse.example.test",
    "LANGFUSE_BASE_URL": "https://langfuse.example.test",
}
EDGE_ENVIRONMENT = {
    "CC_LANGFUSE_PUBLIC_KEY": "otelbox-local-public",
    "CC_LANGFUSE_SECRET_KEY": "otelbox-local-secret",
    "CC_LANGFUSE_BASE_URL": LOOPBACK_URL,
    "LANGFUSE_USER_ID": "someone@example.com",
    "LANGFUSE_TRACING_ENVIRONMENT": "personal",
}


def _load_vendored_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "vendored_langfuse_hook_under_test", langfuse_trace_hook.VENDORED_HOOK
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def claude_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name, value in {**OPERATOR_ENVIRONMENT, **EDGE_ENVIRONMENT}.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(tmp_path))


def test_scrub_removes_only_the_names_that_shadow_the_edge_configuration() -> None:
    environment = {**OPERATOR_ENVIRONMENT, **EDGE_ENVIRONMENT}

    langfuse_trace_hook.scrub_shadowing_credentials(environment)

    assert environment == EDGE_ENVIRONMENT


@pytest.mark.usefixtures("claude_environment")
def test_main_hands_the_vendored_hook_a_scrubbed_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def record(path: str, run_name: str) -> None:
        seen["path"] = path
        seen["run_name"] = run_name
        seen["environment"] = dict(os.environ)
        seen["import_root"] = sys.path[0]

    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", record)

    langfuse_trace_hook.main()

    environment = seen["environment"]
    assert isinstance(environment, dict)
    assert seen["path"] == str(langfuse_trace_hook.VENDORED_HOOK)
    assert seen["run_name"] == "__main__"
    assert seen["import_root"] == str(langfuse_trace_hook.VENDORED_HOOK.parent)
    assert not set(OPERATOR_ENVIRONMENT) & set(environment)
    assert {name: environment[name] for name in EDGE_ENVIRONMENT} == EDGE_ENVIRONMENT


@pytest.mark.usefixtures("claude_environment")
def test_unscrubbed_vendored_hook_would_trace_with_the_operator_keys() -> None:
    pytest.importorskip("langfuse")

    config = _load_vendored_hook().get_langfuse_config()

    assert config.public_key == OPERATOR_ENVIRONMENT["LANGFUSE_PUBLIC_KEY"]


@pytest.mark.usefixtures("claude_environment")
def test_scrubbed_vendored_hook_traces_with_the_edge_keys_to_the_loopback() -> None:
    pytest.importorskip("langfuse")

    langfuse_trace_hook.scrub_shadowing_credentials(os.environ)
    config = _load_vendored_hook().get_langfuse_config()

    assert config.public_key == EDGE_ENVIRONMENT["CC_LANGFUSE_PUBLIC_KEY"]
    assert config.secret_key == EDGE_ENVIRONMENT["CC_LANGFUSE_SECRET_KEY"]
    assert config.host == LOOPBACK_URL
    assert "LANGFUSE_BASE_URL" not in os.environ
    assert "LANGFUSE_HOST" not in os.environ
