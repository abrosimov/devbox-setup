from __future__ import annotations

from pathlib import Path

import pytest
from ai_config import (
    Change,
    ChangeKind,
    FieldManifest,
    FieldScope,
    ReconciliationPlan,
    SemanticSnapshot,
    plan_reconciliation,
)
from ai_config.cli import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT / "roles" / "devbox" / "files" / "dot_agy" / "cli" / ("settings.ai-config.json")
)
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ai_config" / "agy"


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
