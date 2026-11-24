from __future__ import annotations

import json
from pathlib import Path

import pytest
from ai_config import (
    Change,
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
    snapshot_mapping,
)
from ai_config.cli import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT / "roles" / "devbox" / "files" / "dot_agy" / "cli" / ("settings.ai-config.json")
)
SETTINGS_PATH = REPO_ROOT / "roles" / "devbox" / "files" / "dot_agy" / "cli" / "settings.json.j2"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ai_config" / "agy"
PINNED_MODEL = "Gemini 3.1 Pro (High)"


def repository_document(profile: str) -> RepositoryDocument:
    return build_repository_document(
        SETTINGS_PATH.read_bytes(),
        ConfigurationFormat.JSON,
        load_template_variables(REPO_ROOT, profile),
    )


class TestAgyManifest:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return load_manifest(MANIFEST_PATH)

    @pytest.mark.parametrize(
        ("path", "expected_scope"),
        [
            (("allowNonWorkspaceAccess",), FieldScope.SHARED),
            (("colorScheme",), FieldScope.SHARED),
            (("model",), FieldScope.SHARED),
            (("permissions", "allow"), FieldScope.SHARED),
            (("trustedWorkspaces",), FieldScope.LOCAL_STATE),
            (("experimentalSetting",), None),
        ],
    )
    def test_classifies_current_fields(
        self,
        manifest: FieldManifest,
        path: tuple[str, ...],
        expected_scope: FieldScope | None,
    ) -> None:
        assert manifest.scope_for(path) is expected_scope


class TestAgyManifestReconciliation:
    @pytest.fixture
    def plan(self) -> ReconciliationPlan:
        return plan_reconciliation(
            base=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "base.json"),
            repo=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "repo.json"),
            live=SemanticSnapshot.from_json_file(FIXTURE_ROOT / "live.json"),
            manifest=load_manifest(MANIFEST_PATH),
        )

    @pytest.mark.parametrize(
        ("path", "expected_kind"),
        [
            (("allowNonWorkspaceAccess",), ChangeKind.APPLY_REPO),
            (("permissions", "allow"), ChangeKind.APPLY_REPO),
            (("colorScheme",), ChangeKind.CAPTURE_LIVE),
            (("trustedWorkspaces",), ChangeKind.PRESERVE_LOCAL),
            (("experimentalSetting",), ChangeKind.UNKNOWN),
            (("model",), ChangeKind.UNCHANGED),
        ],
    )
    def test_plans_fixture_field(
        self,
        plan: ReconciliationPlan,
        path: tuple[str, ...],
        expected_kind: ChangeKind,
    ) -> None:
        changes_by_path: dict[tuple[str, ...], Change] = {
            change.path: change for change in plan.changes
        }

        assert changes_by_path[path].kind is expected_kind


class TestAgyPinnedModel:
    @pytest.fixture
    def manifest(self) -> FieldManifest:
        return load_manifest(MANIFEST_PATH)

    @pytest.mark.parametrize("profile", ["personal", "work"])
    def test_model_renders_the_pinned_display_name_in_every_profile(self, profile: str) -> None:
        document = repository_document(profile)

        assert snapshot_mapping(document.rendered)["model"] == PINNED_MODEL
        assert ("model",) in document.templated_paths

    def test_model_is_the_only_templated_path(self) -> None:
        assert repository_document("personal").templated_paths == {("model",)}

    def test_unrendered_template_keeps_the_model_inside_a_quoted_placeholder(self) -> None:
        template = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

        assert template["model"] == "{{ devbox_ai_models.agy }}"

    @pytest.mark.parametrize("base_state", ["recorded", "absent"])
    @pytest.mark.parametrize(
        "live_model", ["Claude Sonnet 4.6", "Gemini 3.1 Pro (Low)", PINNED_MODEL]
    )
    @pytest.mark.parametrize("profile", ["personal", "work"])
    def test_pinned_model_is_applied_over_any_live_model_without_a_decision(
        self,
        manifest: FieldManifest,
        profile: str,
        live_model: str,
        base_state: str,
    ) -> None:
        path = ("model",)
        document = repository_document(profile)
        pinned = SemanticSnapshot.from_value({"model": PINNED_MODEL})

        plan = plan_reconciliation(
            base=pinned if base_state == "recorded" else None,
            repo=document.rendered,
            live=SemanticSnapshot.from_value({"model": live_model}),
            manifest=manifest,
            templated_paths=document.templated_paths,
        )

        change = next(change for change in plan.changes if change.path == path)
        assert change.templated is True
        assert change.scope is FieldScope.SHARED
        if live_model == PINNED_MODEL:
            assert change.kind is ChangeKind.UNCHANGED
        else:
            assert change.kind is ChangeKind.APPLY_REPO
        assert change.kind not in {
            ChangeKind.CAPTURE_LIVE,
            ChangeKind.CONFLICT,
            ChangeKind.INITIALISATION_REQUIRED,
        }
