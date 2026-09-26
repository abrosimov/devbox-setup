from __future__ import annotations

import json
from pathlib import Path

import pytest
from ai_config import (
    ChangeKind,
    ConfigurationFormat,
    FieldManifest,
    FieldScope,
    ManifestDefinitionError,
    PreferenceValueType,
    ReconciliationPlan,
    RepositoryDocument,
    SemanticScalar,
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

    def test_current_repository_settings_have_expected_scopes(
        self,
        manifest: FieldManifest,
    ) -> None:
        rendered = repository_document("personal").rendered

        scopes = {
            field.path: manifest.scope_for(field.path) for field in rendered.semantic_fields()
        }

        assert scopes
        assert {path for path, scope in scopes.items() if scope is FieldScope.PREFERENCE} == {
            ("cleanupPeriodDays",)
        }
        assert all(
            scope is FieldScope.SHARED
            for path, scope in scopes.items()
            if path != ("cleanupPeriodDays",)
        )

    def test_cleanup_period_default_is_ten_years(self, manifest: FieldManifest) -> None:
        rendered = repository_document("personal").rendered
        values = {field.path: to_plain_value(field.value) for field in rendered.semantic_fields()}

        assert values[("cleanupPeriodDays",)] == 3650
        rule = manifest.rule_for(("cleanupPeriodDays",))
        assert rule is not None
        assert rule.scope is FieldScope.PREFERENCE
        assert rule.preference is not None
        assert rule.preference.value_type is PreferenceValueType.INTEGER
        assert rule.preference.minimum == 1

    @pytest.mark.parametrize("local_value", [1, 30, 3650, 7300])
    def test_existing_cleanup_period_is_preserved(
        self,
        manifest: FieldManifest,
        local_value: int,
    ) -> None:
        plan = plan_reconciliation(
            base=SemanticSnapshot.from_value({}),
            repo=SemanticSnapshot.from_value({"cleanupPeriodDays": 3650}),
            live=SemanticSnapshot.from_value({"cleanupPeriodDays": local_value}),
            manifest=manifest,
        )

        change = next(change for change in plan.changes if change.path == ("cleanupPeriodDays",))
        assert change.kind is ChangeKind.PRESERVE_LOCAL
        assert change.scope is FieldScope.PREFERENCE

    def test_missing_cleanup_period_gets_repository_default(self, manifest: FieldManifest) -> None:
        plan = plan_reconciliation(
            base=None,
            repo=SemanticSnapshot.from_value({"cleanupPeriodDays": 3650}),
            live=SemanticSnapshot.from_value({}),
            manifest=manifest,
        )

        change = next(change for change in plan.changes if change.path == ("cleanupPeriodDays",))
        assert change.kind is ChangeKind.APPLY_REPO
        assert change.scope is FieldScope.PREFERENCE

    @pytest.mark.parametrize("value", [True, 1.5, None, [], {}, "", "30", 0, -1])
    @pytest.mark.parametrize("source", ["repository", "live"])
    def test_cleanup_period_rejects_invalid_preference_types(
        self,
        manifest: FieldManifest,
        value: object,
        source: str,
    ) -> None:
        repository_value = value if source == "repository" else 3650
        live_value = value if source == "live" else 3650

        with pytest.raises(ManifestDefinitionError):
            plan_reconciliation(
                base=SemanticSnapshot.from_value({}),
                repo=SemanticSnapshot.from_value({"cleanupPeriodDays": repository_value}),
                live=SemanticSnapshot.from_value({"cleanupPeriodDays": live_value}),
                manifest=manifest,
            )

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

    def test_dialog_expiry_is_a_local_preference(self, manifest: FieldManifest) -> None:
        plan = plan_reconciliation(
            base=SemanticSnapshot.from_value({}),
            repo=SemanticSnapshot.from_value({}),
            live=SemanticSnapshot.from_value({"dialogExpiry": "10m"}),
            manifest=manifest,
        )

        assert manifest.scope_for(("dialogExpiry",)) is FieldScope.PREFERENCE
        assert len(plan.changes) == 1
        change = plan.changes[0]
        assert change.path == ("dialogExpiry",)
        assert change.kind is ChangeKind.PRESERVE_LOCAL
        assert change.scope is FieldScope.PREFERENCE
        assert isinstance(change.live, SemanticScalar)
        assert change.live.value == "10m"

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
