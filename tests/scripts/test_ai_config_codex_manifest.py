from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from ai_config import (
    BindingProvider,
    Change,
    ChangeKind,
    FieldManifest,
    FieldScope,
    ReconciliationPlan,
    SemanticSnapshot,
    plan_reconciliation,
    to_plain_value,
)
from ai_config.cli import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_codex" / ("config.ai-config.json")
CONFIG_TEMPLATE_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_codex" / ("config.toml.j2")
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ai_config" / "codex"


class TestCodexManifestCoverage:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return load_manifest(MANIFEST_PATH)

    @pytest.fixture
    def repository(self) -> SemanticSnapshot:
        source = CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")
        return SemanticSnapshot.from_value(tomllib.loads(source))

    def test_current_template_parses_with_quoted_profile_placeholder(
        self,
        repository: SemanticSnapshot,
    ) -> None:
        values = {field.path: to_plain_value(field.value) for field in repository.semantic_fields()}

        assert values[("otel", "environment")] == "{{ devbox_active_profile }}"

    def test_environment_uses_explicit_profile_binding(self, manifest: FieldManifest) -> None:
        rule = manifest.rule_for(("otel", "environment"))

        assert rule is not None
        assert rule.binding is not None
        assert rule.binding.provider is BindingProvider.PROFILE
        assert rule.binding.key == "devbox_active_profile"

    def test_every_current_repository_field_is_classified(
        self,
        manifest: FieldManifest,
        repository: SemanticSnapshot,
    ) -> None:
        unclassified = [
            field.path
            for field in repository.semantic_fields()
            if manifest.scope_for(field.path) is None
        ]

        assert unclassified == []

    @pytest.mark.parametrize(
        ("path", "expected_scope"),
        [
            (("personality",), FieldScope.SHARED),
            (("model",), FieldScope.SHARED),
            (("model_reasoning_effort",), FieldScope.SHARED),
            (("service_tier",), FieldScope.SHARED),
            (("sandbox_mode",), FieldScope.SHARED),
            (("features", "memories"), FieldScope.SHARED),
            (("features", "hooks"), FieldScope.SHARED),
            (("hooks", "PreToolUse"), FieldScope.SHARED),
            (("sandbox_workspace_write", "network_access"), FieldScope.SHARED),
            (("otel", "log_user_prompt"), FieldScope.SHARED),
            (("otel", "exporter", "otlp-grpc", "endpoint"), FieldScope.SHARED),
            (("otel", "trace_exporter", "otlp-grpc", "endpoint"), FieldScope.SHARED),
            (("otel", "metrics_exporter", "otlp-grpc", "endpoint"), FieldScope.SHARED),
            (("otel", "environment"), FieldScope.ENVIRONMENT),
        ],
    )
    def test_current_repository_field_scope(
        self,
        manifest: FieldManifest,
        repository: SemanticSnapshot,
        path: tuple[str, ...],
        expected_scope: FieldScope,
    ) -> None:
        repository_paths = {field.path for field in repository.semantic_fields()}

        assert path in repository_paths
        assert manifest.scope_for(path) is expected_scope


class TestCodexManifestClassification:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return load_manifest(MANIFEST_PATH)

    @pytest.mark.parametrize(
        ("path", "expected_scope"),
        [
            (("features", "js_repl"), FieldScope.SHARED),
            (("hooks", "SessionStart"), FieldScope.SHARED),
            (("plugins", "example", "enabled"), FieldScope.SHARED),
            (("marketplaces", "example", "enabled"), FieldScope.SHARED),
            (("desktop", "analytics"), FieldScope.SHARED),
            (("tui", "notifications"), FieldScope.SHARED),
            (("tool_suggest", "enabled"), FieldScope.SHARED),
            (("skills", "config", "example-skill", "enabled"), FieldScope.SHARED),
            (("mcp_servers", "example", "command"), FieldScope.SHARED),
            (("projects", "/Users/example/project", "trust_level"), FieldScope.LOCAL_STATE),
            (("notify",), FieldScope.LOCAL_STATE),
            (("notice", "model_migrations", "gpt-example"), FieldScope.RUNTIME),
            (("notice", "unrecognised"), FieldScope.RUNTIME),
            (("state", "opaque"), None),
        ],
    )
    def test_classifies_only_supported_paths(
        self,
        manifest: FieldManifest,
        path: tuple[str, ...],
        expected_scope: FieldScope | None,
    ) -> None:
        assert manifest.scope_for(path) is expected_scope


class TestCodexManifestReconciliation:
    @pytest.fixture
    def plan(self) -> ReconciliationPlan:
        return plan_reconciliation(
            base=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "base.json"),
            repo=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "repo.json"),
            live=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "live.json"),
            manifest=load_manifest(MANIFEST_PATH),
        )

    @pytest.fixture
    def changes(self, plan: ReconciliationPlan) -> dict[tuple[str, ...], Change]:
        return {change.path: change for change in plan.changes}

    @pytest.mark.parametrize(
        "path",
        [
            ("model",),
            ("features", "memories"),
        ],
    )
    def test_repository_changes_are_apply_repo(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.APPLY_REPO
        assert changes[path].scope is FieldScope.SHARED

    @pytest.mark.parametrize(
        "path",
        [
            ("plugins", "example", "enabled"),
            ("marketplaces", "example", "enabled"),
            ("desktop", "analytics"),
            ("tui", "notifications"),
            ("tool_suggest", "enabled"),
            ("skills", "config", "example-skill", "enabled"),
            ("mcp_servers", "example", "command"),
        ],
    )
    def test_portable_live_changes_are_capture_live(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.CAPTURE_LIVE
        assert changes[path].scope is FieldScope.SHARED

    def test_bound_environment_change_applies_repository(
        self,
        changes: dict[tuple[str, ...], Change],
    ) -> None:
        path = ("otel", "environment")

        assert changes[path].kind is ChangeKind.APPLY_REPO
        assert changes[path].scope is FieldScope.ENVIRONMENT

    @pytest.mark.parametrize(
        "path",
        [
            ("projects", "/Users/example/Projects/machine-local", "trust_level"),
            ("notify",),
        ],
    )
    def test_local_project_paths_are_preserved(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
    ) -> None:
        assert changes[path].kind is ChangeKind.PRESERVE_LOCAL
        assert changes[path].scope is FieldScope.LOCAL_STATE

    @pytest.mark.parametrize(
        ("path", "expected_kind", "expected_scope"),
        [
            (
                ("notice", "model_migrations", "gpt-example-old"),
                ChangeKind.PRESERVE_LOCAL,
                FieldScope.RUNTIME,
            ),
            (("futureVendorSetting", "enabled"), ChangeKind.UNKNOWN, None),
        ],
    )
    def test_runtime_and_unknown_fields_remain_non_portable(
        self,
        changes: dict[tuple[str, ...], Change],
        path: tuple[str, ...],
        expected_kind: ChangeKind,
        expected_scope: FieldScope | None,
    ) -> None:
        assert changes[path].kind is expected_kind
        assert changes[path].scope is expected_scope
