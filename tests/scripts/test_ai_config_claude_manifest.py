from __future__ import annotations

import json
from pathlib import Path

import pytest
from ai_config import (
    BindingProvider,
    BindingProviders,
    ChangeKind,
    FieldManifest,
    FieldScope,
    ReconciliationPlan,
    SemanticSnapshot,
    plan_reconciliation,
    resolve_snapshot_bindings,
    to_plain_value,
)
from ai_config.cli import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_claude" / "settings.ai-config.json"
SETTINGS_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_claude" / "settings.json"
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "ai_config" / "claude"


class TestClaudeFieldManifest:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return load_manifest(MANIFEST_PATH)

    @pytest.fixture
    def plan(self, manifest: FieldManifest) -> ReconciliationPlan:
        return plan_reconciliation(
            base=SemanticSnapshot.from_json_file(FIXTURES_PATH / "base.json"),
            repo=SemanticSnapshot.from_json_file(FIXTURES_PATH / "repo.json"),
            live=SemanticSnapshot.from_json_file(FIXTURES_PATH / "live.json"),
            manifest=manifest,
        )

    def test_current_repository_settings_are_explicitly_classified(
        self,
        manifest: FieldManifest,
    ) -> None:
        repository = SemanticSnapshot.from_json_file(SETTINGS_PATH)

        scopes = {
            field.path: manifest.scope_for(field.path) for field in repository.semantic_fields()
        }

        assert scopes.pop(("env", "LANGFUSE_TRACING_ENVIRONMENT")) is FieldScope.ENVIRONMENT
        assert scopes
        assert all(scope is FieldScope.SHARED for scope in scopes.values())

    def test_langfuse_environment_uses_explicit_profile_binding(
        self,
        manifest: FieldManifest,
    ) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        rule = manifest.rule_for(("env", "LANGFUSE_TRACING_ENVIRONMENT"))

        assert settings["env"]["LANGFUSE_TRACING_ENVIRONMENT"] == "{{ devbox_active_profile }}"
        assert rule is not None
        assert rule.binding is not None
        assert rule.binding.provider is BindingProvider.PROFILE
        assert rule.binding.key == "devbox_active_profile"

    def test_langfuse_environment_resolves_active_profile(
        self,
        manifest: FieldManifest,
    ) -> None:
        repository = SemanticSnapshot.from_json_file(SETTINGS_PATH)

        resolved = resolve_snapshot_bindings(
            repository,
            manifest,
            BindingProviders(profile="personal", environment={}),
        )
        values = {field.path: to_plain_value(field.value) for field in resolved.semantic_fields()}

        assert values[("env", "LANGFUSE_TRACING_ENVIRONMENT")] == "personal"

    def test_otel_resource_classification_is_shared(
        self,
        manifest: FieldManifest,
    ) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

        assert settings["env"]["OTEL_RESOURCE_ATTRIBUTES"] == ("otelbox.telemetry.class=llm")
        assert manifest.scope_for(("env", "OTEL_RESOURCE_ATTRIBUTES")) is FieldScope.SHARED

    @pytest.mark.parametrize(
        "path",
        [
            ("model",),
            ("extraKnownMarketplaces", "example-marketplace", "source"),
            ("enabledPlugins", "example-skills@example-marketplace"),
            ("permissions", "allow"),
        ],
    )
    def test_known_portable_live_fields_are_explicitly_shared(
        self,
        manifest: FieldManifest,
        path: tuple[str, ...],
    ) -> None:
        assert manifest.scope_for(path) is FieldScope.SHARED

    @pytest.mark.parametrize(
        "path",
        [
            ("model",),
            ("extraKnownMarketplaces", "example-marketplace", "source"),
            ("enabledPlugins", "example-skills@example-marketplace"),
            ("permissions", "allow"),
        ],
    )
    def test_live_portable_changes_are_capture_live(
        self,
        plan: ReconciliationPlan,
        path: tuple[str, ...],
    ) -> None:
        changes = {change.path: change.kind for change in plan.changes}

        assert changes[path] is ChangeKind.CAPTURE_LIVE

    def test_repository_only_change_is_apply_repo(self, plan: ReconciliationPlan) -> None:
        changes = {change.path: change.kind for change in plan.changes}

        assert changes[("autoMemoryEnabled",)] is ChangeKind.APPLY_REPO

    def test_unclassified_live_field_remains_unknown(self, plan: ReconciliationPlan) -> None:
        changes = {change.path: change.kind for change in plan.changes}

        assert changes[("vendorSessionState", "state")] is ChangeKind.UNKNOWN
