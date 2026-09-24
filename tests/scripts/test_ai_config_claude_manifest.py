from __future__ import annotations

import json
from pathlib import Path

import pytest
from ai_config import (
    ChangeKind,
    ConfigurationFormat,
    FieldManifest,
    FieldScope,
    ReconciliationPlan,
    RepositoryDocument,
    SemanticSnapshot,
    build_repository_document,
    load_template_variables,
    plan_reconciliation,
    to_plain_value,
)
from ai_config.cli import load_manifest
from ai_config_fixtures import REPO_ROOT

MANIFEST_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_claude" / "settings.ai-config.json"
SETTINGS_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_claude" / "settings.json.j2"
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "ai_config" / "claude"

PROFILE_TEMPLATED_PATHS = {
    ("env", "LANGFUSE_TRACING_ENVIRONMENT"),
    ("env", "LANGFUSE_USER_ID"),
}


def repository_document(profile: str) -> RepositoryDocument:
    return build_repository_document(
        SETTINGS_PATH.read_bytes(),
        ConfigurationFormat.JSON,
        load_template_variables(REPO_ROOT, profile),
    )


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
        rendered = repository_document("personal").rendered

        scopes = {
            field.path: manifest.scope_for(field.path) for field in rendered.semantic_fields()
        }

        assert scopes
        assert all(scope is FieldScope.SHARED for scope in scopes.values())

    @pytest.mark.parametrize(
        ("profile", "expected_environment", "expected_user"),
        [
            ("personal", "personal", "abrosimov.k.a@gmail.com"),
            ("work", "work", "kirill@work"),
        ],
    )
    def test_langfuse_identity_renders_from_the_selected_profile(
        self,
        profile: str,
        expected_environment: str,
        expected_user: str,
    ) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        rendered = repository_document(profile).rendered
        values = {field.path: to_plain_value(field.value) for field in rendered.semantic_fields()}

        assert settings["env"]["LANGFUSE_TRACING_ENVIRONMENT"] == "{{ devbox_active_profile }}"
        assert settings["env"]["LANGFUSE_USER_ID"] == "{{ devbox_langfuse_user_id }}"
        assert values[("env", "LANGFUSE_TRACING_ENVIRONMENT")] == expected_environment
        assert values[("env", "LANGFUSE_USER_ID")] == expected_user

    def test_only_the_profile_dependent_settings_are_templated(self) -> None:
        document = repository_document("personal")

        assert document.templated_paths == PROFILE_TEMPLATED_PATHS

    def test_otel_resource_classification_is_shared(
        self,
        manifest: FieldManifest,
    ) -> None:
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

        assert settings["env"]["OTEL_RESOURCE_ATTRIBUTES"] == ("otelbox.telemetry.class=llm")
        assert manifest.scope_for(("env", "OTEL_RESOURCE_ATTRIBUTES")) is FieldScope.SHARED

    def test_no_manifest_rule_resolves_a_profile_value_through_a_binding(
        self,
        manifest: FieldManifest,
    ) -> None:
        """Profile values reach the live file by rendering, never by binding.

        A binding materialises its value at apply time and is deliberately not
        written back, so a reintroduced one would make a profile value portable
        again without the templated-path guard noticing.
        """
        assert [rule.path for rule in manifest.rules if rule.binding is not None] == []

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
