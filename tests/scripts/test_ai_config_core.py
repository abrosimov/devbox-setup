from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from ai_config import (
    BindingProvider,
    ChangeKind,
    FieldBinding,
    FieldManifest,
    FieldRule,
    FieldScope,
    FieldStrategy,
    ManifestDefinitionError,
    SemanticArray,
    SemanticSnapshot,
    SnapshotError,
    plan_reconciliation,
    to_plain_value,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ai-config"


def snapshot(value: object) -> SemanticSnapshot:
    return SemanticSnapshot.from_value(value)


def single_rule(scope: FieldScope = FieldScope.SHARED) -> FieldManifest:
    return FieldManifest(rules=(FieldRule(path=("value",), scope=scope),))


class TestSemanticSnapshot:
    def test_object_order_does_not_change_semantic_value(self) -> None:
        first = snapshot({"alpha": 1, "nested": {"enabled": True}})
        second = snapshot({"nested": {"enabled": True}, "alpha": 1})

        assert first == second

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, None),
            (True, True),
            (3, 3),
            (2.5, 2.5),
            ("text", "text"),
            ([1, {"enabled": False}], [1, {"enabled": False}]),
        ],
    )
    def test_json_like_values_round_trip(self, value: object, expected: object) -> None:
        parsed = snapshot({"value": value})
        field = parsed.semantic_fields()[0]

        assert to_plain_value(field.value) == expected

    @pytest.mark.parametrize(
        "source",
        ["[]", "null", '"value"', "1"],
    )
    def test_non_object_configuration_root_is_rejected(self, source: str) -> None:
        with pytest.raises(SnapshotError):
            SemanticSnapshot.from_json(source)

    @pytest.mark.parametrize(
        "value",
        [float("nan"), float("inf"), {"not", "json"}],
    )
    def test_unsupported_values_are_rejected(self, value: object) -> None:
        with pytest.raises(SnapshotError):
            snapshot({"value": value})

    def test_scalar_types_are_not_coerced_by_python_equality(self) -> None:
        boolean = snapshot({"value": True})
        integer = snapshot({"value": 1})
        number = snapshot({"value": 1.0})

        assert boolean != integer
        assert integer != number

    def test_nested_objects_flatten_to_field_paths_and_arrays_remain_atomic(self) -> None:
        parsed = snapshot({"permissions": {"allow": ["Read", "Write"]}, "empty": {}})

        assert [field.path for field in parsed.semantic_fields()] == [
            ("empty",),
            ("permissions", "allow"),
        ]


class TestFieldManifest:
    def test_most_specific_rule_controls_scope(self) -> None:
        manifest = FieldManifest(
            rules=(
                FieldRule(path=("permissions",), scope=FieldScope.SHARED),
                FieldRule(
                    path=("permissions", "session"),
                    scope=FieldScope.RUNTIME,
                ),
            ),
        )

        assert manifest.scope_for(("permissions", "allow")) is FieldScope.SHARED
        assert manifest.scope_for(("permissions", "session", "id")) is FieldScope.RUNTIME
        assert manifest.scope_for(("model",)) is None

    @pytest.mark.parametrize(
        "rules",
        [
            (FieldRule(path=("value",), scope=FieldScope.SHARED),) * 2,
            (
                FieldRule(path=("value",), scope=FieldScope.SHARED),
                FieldRule(path=("value",), scope=FieldScope.RUNTIME),
            ),
        ],
    )
    def test_duplicate_rule_paths_are_rejected(self, rules: tuple[FieldRule, ...]) -> None:
        with pytest.raises(ManifestDefinitionError):
            FieldManifest(rules=rules)

    @pytest.mark.parametrize("path", [(), ("",), ("permissions", "")])
    def test_empty_path_segments_are_rejected(self, path: tuple[str, ...]) -> None:
        with pytest.raises(ManifestDefinitionError):
            FieldRule(path=path, scope=FieldScope.SHARED)

    def test_bindings_are_limited_to_environment_fields(self) -> None:
        binding = FieldBinding(provider=BindingProvider.ENVIRONMENT, key="API_TOKEN")

        with pytest.raises(ManifestDefinitionError):
            FieldRule(path=("token",), scope=FieldScope.SHARED, binding=binding)

    def test_environment_fields_require_an_explicit_binding(self) -> None:
        with pytest.raises(ManifestDefinitionError):
            FieldRule(path=("token",), scope=FieldScope.ENVIRONMENT)

    @pytest.mark.parametrize(
        "key",
        [
            "",
            "/Users/someone/.claude/marketplaces/example",
            ".",
            "./",
            "..",
            "../.claude",
            ".claude/../../.codex",
        ],
    )
    def test_home_bindings_reject_keys_that_do_not_stay_below_the_home_directory(
        self,
        key: str,
    ) -> None:
        with pytest.raises(ManifestDefinitionError):
            FieldBinding(provider=BindingProvider.HOME, key=key)

    def test_ordered_set_strategy_requires_shared_scope(self) -> None:
        with pytest.raises(ManifestDefinitionError):
            FieldRule(
                path=("permissions",),
                scope=FieldScope.LOCAL_STATE,
                strategy=FieldStrategy.ORDERED_SET,
            )


class TestThreeWayPlanner:
    @pytest.mark.parametrize(
        ("base_value", "repo_value", "live_value", "expected"),
        [
            ("old", "old", "live", ChangeKind.CAPTURE_LIVE),
            ("old", "repo", "old", ChangeKind.APPLY_REPO),
            ("old", "same", "same", ChangeKind.UNCHANGED),
            ("old", "repo", "live", ChangeKind.CONFLICT),
            ("same", "same", "same", ChangeKind.UNCHANGED),
        ],
    )
    def test_scalar_three_way_table(
        self,
        base_value: str,
        repo_value: str,
        live_value: str,
        expected: ChangeKind,
    ) -> None:
        plan = plan_reconciliation(
            base=snapshot({"value": base_value}),
            repo=snapshot({"value": repo_value}),
            live=snapshot({"value": live_value}),
            manifest=single_rule(),
        )

        assert plan.changes[0].kind is expected

    @pytest.mark.parametrize(
        ("base_value", "repo_value", "live_value", "expected"),
        [
            ({}, {"value": "new"}, {}, ChangeKind.APPLY_REPO),
            ({}, {}, {"value": "new"}, ChangeKind.CAPTURE_LIVE),
            (
                {"value": "old"},
                {},
                {"value": "old"},
                ChangeKind.APPLY_REPO,
            ),
            (
                {"value": "old"},
                {"value": "old"},
                {},
                ChangeKind.CAPTURE_LIVE,
            ),
        ],
    )
    def test_additions_and_deletions_follow_three_way_table(
        self,
        base_value: dict[str, str],
        repo_value: dict[str, str],
        live_value: dict[str, str],
        expected: ChangeKind,
    ) -> None:
        plan = plan_reconciliation(
            base=snapshot(base_value),
            repo=snapshot(repo_value),
            live=snapshot(live_value),
            manifest=single_rule(),
        )

        assert plan.changes[0].kind is expected

    @pytest.mark.parametrize(
        ("repo_value", "live_value", "expected"),
        [
            ("same", "same", ChangeKind.UNCHANGED),
            ("repo", "live", ChangeKind.INITIALISATION_REQUIRED),
        ],
    )
    def test_missing_base_never_guesses_change_direction(
        self,
        repo_value: str,
        live_value: str,
        expected: ChangeKind,
    ) -> None:
        plan = plan_reconciliation(
            base=None,
            repo=snapshot({"value": repo_value}),
            live=snapshot({"value": live_value}),
            manifest=single_rule(),
        )

        assert plan.changes[0].kind is expected

    @pytest.mark.parametrize("scope", [FieldScope.LOCAL_STATE, FieldScope.RUNTIME])
    def test_local_and_runtime_fields_are_preserved(self, scope: FieldScope) -> None:
        plan = plan_reconciliation(
            base=snapshot({"value": "base"}),
            repo=snapshot({"value": "repo"}),
            live=snapshot({"value": "live"}),
            manifest=single_rule(scope),
        )

        assert plan.changes[0].kind is ChangeKind.PRESERVE_LOCAL
        assert plan.is_converged() is True

    def test_unknown_field_is_reported_even_when_all_values_match(self) -> None:
        plan = plan_reconciliation(
            base=snapshot({"value": "same"}),
            repo=snapshot({"value": "same"}),
            live=snapshot({"value": "same"}),
            manifest=FieldManifest(rules=()),
        )

        assert plan.changes[0].kind is ChangeKind.UNKNOWN
        assert plan.is_converged() is False

    def test_shared_scope_uses_three_way_semantics(self) -> None:
        plan = plan_reconciliation(
            base=snapshot({"value": "old"}),
            repo=snapshot({"value": "new"}),
            live=snapshot({"value": "old"}),
            manifest=single_rule(FieldScope.SHARED),
        )

        assert plan.changes[0].kind is ChangeKind.APPLY_REPO

    def test_bound_environment_field_is_always_applied_from_repository_intent(self) -> None:
        manifest = FieldManifest(
            rules=(
                FieldRule(
                    path=("environment",),
                    scope=FieldScope.ENVIRONMENT,
                    binding=FieldBinding(
                        provider=BindingProvider.PROFILE,
                        key="devbox_active_profile",
                    ),
                ),
            )
        )
        plan = plan_reconciliation(
            base=snapshot({"environment": "personal"}),
            repo=snapshot({"environment": "work"}),
            live=snapshot({"environment": "locally-edited"}),
            manifest=manifest,
        )

        assert plan.changes[0].kind is ChangeKind.APPLY_REPO

    def test_changes_are_sorted_and_counted_by_kind(self) -> None:
        plan = plan_reconciliation(
            base=snapshot({"alpha": 1, "beta": 1}),
            repo=snapshot({"alpha": 2, "beta": 1}),
            live=snapshot({"alpha": 1, "beta": 3}),
            manifest=FieldManifest(
                rules=(
                    FieldRule(path=("alpha",), scope=FieldScope.SHARED),
                    FieldRule(path=("beta",), scope=FieldScope.SHARED),
                ),
            ),
        )

        assert [change.path for change in plan.changes] == [("alpha",), ("beta",)]
        assert plan.count(ChangeKind.APPLY_REPO) == 1
        assert plan.count(ChangeKind.CAPTURE_LIVE) == 1

    def test_ordered_set_merges_independent_repository_and_live_additions(self) -> None:
        manifest = FieldManifest(
            rules=(
                FieldRule(
                    path=("permissions",),
                    scope=FieldScope.SHARED,
                    strategy=FieldStrategy.ORDERED_SET,
                ),
            )
        )

        plan = plan_reconciliation(
            base=snapshot({"permissions": ["Read"]}),
            repo=snapshot({"permissions": ["Read", "Write"]}),
            live=snapshot({"permissions": ["Read", "WebFetch"]}),
            manifest=manifest,
        )

        assert plan.changes[0].kind is ChangeKind.MERGE
        merged = plan.changes[0].merged
        assert isinstance(merged, SemanticArray)
        assert to_plain_value(merged) == ["Read", "Write", "WebFetch"]

    def test_ordered_set_applies_independent_deletion_and_preserves_live_addition(self) -> None:
        manifest = FieldManifest(
            rules=(
                FieldRule(
                    path=("permissions",),
                    scope=FieldScope.SHARED,
                    strategy=FieldStrategy.ORDERED_SET,
                ),
            )
        )

        plan = plan_reconciliation(
            base=snapshot({"permissions": ["Read", "Write"]}),
            repo=snapshot({"permissions": ["Read"]}),
            live=snapshot({"permissions": ["Read", "Write", "WebFetch"]}),
            manifest=manifest,
        )

        assert plan.changes[0].kind is ChangeKind.MERGE
        merged = plan.changes[0].merged
        assert isinstance(merged, SemanticArray)
        assert to_plain_value(merged) == ["Read", "WebFetch"]

    def test_ordered_set_rejects_duplicate_members(self) -> None:
        manifest = FieldManifest(
            rules=(
                FieldRule(
                    path=("permissions",),
                    scope=FieldScope.SHARED,
                    strategy=FieldStrategy.ORDERED_SET,
                ),
            )
        )

        with pytest.raises(ManifestDefinitionError):
            plan_reconciliation(
                base=snapshot({"permissions": ["Read"]}),
                repo=snapshot({"permissions": ["Read", "Read"]}),
                live=snapshot({"permissions": ["Read"]}),
                manifest=manifest,
            )


class TestReadOnlyCli:
    def test_status_outputs_machine_readable_counts_without_writing_files(
        self,
        tmp_path: Path,
    ) -> None:
        base = tmp_path / "base.json"
        repo = tmp_path / "repo.json"
        live = tmp_path / "live.json"
        manifest = tmp_path / "manifest.json"
        base.write_text('{"value": "old"}\n', encoding="utf-8")
        repo.write_text('{"value": "old"}\n', encoding="utf-8")
        live.write_text('{"value": "new"}\n', encoding="utf-8")
        manifest.write_text(
            '{"fields": [{"path": ["value"], "scope": "shared"}]}\n',
            encoding="utf-8",
        )
        original_sources = [path.read_bytes() for path in (base, repo, live, manifest)]

        result = subprocess.run(
            [
                SCRIPT,
                "status",
                "--base",
                base,
                "--repo",
                repo,
                "--live",
                live,
                "--manifest",
                manifest,
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        output = json.loads(result.stdout)
        assert result.returncode == 1
        assert output["schema_version"] == 1
        assert output["engine"] is None
        assert output["converged"] is False
        assert output["counts"]["capture-live"] == 1
        assert [path.read_bytes() for path in (base, repo, live, manifest)] == original_sources

    def test_diff_accepts_dotted_manifest_paths(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo.json"
        live = tmp_path / "live.json"
        manifest = tmp_path / "manifest.json"
        repo.write_text('{"permissions": {"allow": ["Read"]}}', encoding="utf-8")
        live.write_text('{"permissions": {"allow": ["Write"]}}', encoding="utf-8")
        manifest.write_text(
            '{"fields": [{"path": "permissions.allow", "scope": "shared"}]}',
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                SCRIPT,
                "diff",
                "--repo",
                repo,
                "--live",
                live,
                "--manifest",
                manifest,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert result.stdout == "initialisation-required\tpermissions.allow\n"

    def test_status_accepts_an_engine_as_the_single_user_facing_handle(
        self,
        tmp_path: Path,
    ) -> None:
        repo_root = tmp_path / "repository"
        home = tmp_path / "home"
        repository = repo_root / "roles/devbox/files/dot_claude/settings.json"
        manifest = repo_root / "roles/devbox/files/dot_claude/settings.ai-config.json"
        live = home / ".claude/settings.json"
        for path in (repository, manifest, live):
            path.parent.mkdir(parents=True, exist_ok=True)
        repository.write_text('{"model": "repository"}\n', encoding="utf-8")
        live.write_text('{"model": "live"}\n', encoding="utf-8")
        manifest.write_text(
            '{"schema_version": 1, "engine": "claude", '
            '"fields": [{"path": "model", "scope": "shared"}]}\n',
            encoding="utf-8",
        )
        original_sources = [path.read_bytes() for path in (repository, manifest, live)]

        result = subprocess.run(
            [
                SCRIPT,
                "status",
                "claude",
                "--repo-root",
                repo_root,
                "--home",
                home,
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        output = json.loads(result.stdout)
        assert result.returncode == 1
        assert output["schema_version"] == 1
        assert output["engine"] == "claude"
        assert output["converged"] is False
        assert output["counts"]["initialisation-required"] == 1
        assert [path.read_bytes() for path in (repository, manifest, live)] == original_sources

    @pytest.mark.parametrize(
        "manifest_source",
        [
            "not json",
            "[]",
            "{}",
            '{"fields": [], "unexpected": true}',
            '{"fields": [{"path": [], "scope": "shared"}]}',
            '{"fields": [{"path": [1], "scope": "shared"}]}',
            '{"fields": [{"path": ["value"], "scope": "invalid"}]}',
            '{"fields": [{"path": "value", "scope": "environment"}]}',
            '{"fields": [{"path": "value", "scope": "shared", "strategyy": "atomic"}]}',
        ],
    )
    def test_invalid_manifest_returns_usage_error(
        self,
        tmp_path: Path,
        manifest_source: str,
    ) -> None:
        repo = tmp_path / "repo.json"
        live = tmp_path / "live.json"
        manifest = tmp_path / "manifest.json"
        repo.write_text('{"value": true}', encoding="utf-8")
        live.write_text('{"value": true}', encoding="utf-8")
        manifest.write_text(manifest_source, encoding="utf-8")

        result = subprocess.run(
            [
                SCRIPT,
                "status",
                "--repo",
                repo,
                "--live",
                live,
                "--manifest",
                manifest,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 2
        assert result.stderr

    def test_diff_redacts_secret_values_in_json_output(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo.json"
        live = tmp_path / "live.json"
        manifest = tmp_path / "manifest.json"
        repo.write_text('{"token": "repo-secret"}', encoding="utf-8")
        live.write_text('{"token": "live-secret"}', encoding="utf-8")
        manifest.write_text(
            json.dumps(
                {
                    "fields": [
                        {
                            "path": "token",
                            "scope": "environment",
                            "binding": "env:API_TOKEN",
                            "secret": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                SCRIPT,
                "diff",
                "--repo",
                repo,
                "--live",
                live,
                "--manifest",
                manifest,
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert "repo-secret" not in result.stdout
        assert "live-secret" not in result.stdout
        assert json.loads(result.stdout)["changes"][0]["repo"] == "<redacted>"
