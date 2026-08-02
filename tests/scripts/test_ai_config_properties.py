from __future__ import annotations

from enum import StrEnum

from ai_config import (
    ChangeKind,
    FieldManifest,
    FieldRule,
    FieldScope,
    SemanticSnapshot,
    plan_reconciliation,
)
from hypothesis import given
from hypothesis import strategies as st


class BaseMode(StrEnum):
    MISSING = "missing"
    PRESENT = "present"


JSON_SCALARS: st.SearchStrategy[object] = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=16),
)
JSON_KEYS = st.text(alphabet="abcde", min_size=1, max_size=5)


def json_collections(children: st.SearchStrategy[object]) -> st.SearchStrategy[object]:
    return st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(JSON_KEYS, children, max_size=4),
    )


JSON_VALUES = st.recursive(JSON_SCALARS, json_collections, max_leaves=10)
JSON_OBJECTS = st.dictionaries(JSON_KEYS, JSON_VALUES, min_size=2, max_size=5)


def snapshot_with_field(value: object) -> SemanticSnapshot:
    return SemanticSnapshot.from_value({"value": value})


def manifest_for(scope: FieldScope) -> FieldManifest:
    return FieldManifest(rules=(FieldRule(path=("value",), scope=scope),))


def changed_value(value: object, marker: str) -> object:
    return [marker, value]


class TestReconciliationProperties:
    @given(
        base_value=JSON_VALUES,
        repo_value=JSON_VALUES,
        live_value=JSON_VALUES,
        base_mode=st.sampled_from(tuple(BaseMode)),
    )
    def test_arbitrary_inputs_produce_deterministic_plans(
        self,
        base_value: object,
        repo_value: object,
        live_value: object,
        base_mode: BaseMode,
    ) -> None:
        base = snapshot_with_field(base_value) if base_mode is BaseMode.PRESENT else None
        repo = snapshot_with_field(repo_value)
        live = snapshot_with_field(live_value)
        manifest = manifest_for(FieldScope.SHARED)

        first = plan_reconciliation(base=base, repo=repo, live=live, manifest=manifest)
        second = plan_reconciliation(base=base, repo=repo, live=live, manifest=manifest)

        assert first == second

    @given(
        value=JSON_VALUES,
        base_mode=st.sampled_from(tuple(BaseMode)),
    )
    def test_equal_repo_and_live_are_deterministically_unchanged(
        self,
        value: object,
        base_mode: BaseMode,
    ) -> None:
        stale_base = changed_value(value, "stale-base")
        base = snapshot_with_field(stale_base) if base_mode is BaseMode.PRESENT else None
        repo = snapshot_with_field(value)
        live = snapshot_with_field(value)
        manifest = manifest_for(FieldScope.SHARED)

        first = plan_reconciliation(base=base, repo=repo, live=live, manifest=manifest)
        second = plan_reconciliation(base=base, repo=repo, live=live, manifest=manifest)

        assert first == second
        assert first.changes
        assert all(change.kind is ChangeKind.UNCHANGED for change in first.changes)

    @given(base_value=JSON_VALUES)
    def test_repo_only_change_applies_repo(self, base_value: object) -> None:
        plan = plan_reconciliation(
            base=snapshot_with_field(base_value),
            repo=snapshot_with_field(changed_value(base_value, "repo-change")),
            live=snapshot_with_field(base_value),
            manifest=manifest_for(FieldScope.SHARED),
        )

        assert plan.changes
        assert all(change.kind is ChangeKind.APPLY_REPO for change in plan.changes)

    @given(base_value=JSON_VALUES)
    def test_live_only_change_is_captured(self, base_value: object) -> None:
        plan = plan_reconciliation(
            base=snapshot_with_field(base_value),
            repo=snapshot_with_field(base_value),
            live=snapshot_with_field(changed_value(base_value, "live-change")),
            manifest=manifest_for(FieldScope.SHARED),
        )

        assert plan.changes
        assert all(change.kind is ChangeKind.CAPTURE_LIVE for change in plan.changes)

    @given(base_value=JSON_VALUES)
    def test_distinct_simultaneous_changes_conflict(self, base_value: object) -> None:
        plan = plan_reconciliation(
            base=snapshot_with_field(base_value),
            repo=snapshot_with_field(changed_value(base_value, "repo-change")),
            live=snapshot_with_field(changed_value(base_value, "live-change")),
            manifest=manifest_for(FieldScope.SHARED),
        )
        differing_changes = [change for change in plan.changes if change.repo != change.live]

        assert differing_changes
        assert all(change.kind is ChangeKind.CONFLICT for change in differing_changes)

    @given(
        base_value=JSON_VALUES,
        repo_value=JSON_VALUES,
        live_value=JSON_VALUES,
        base_mode=st.sampled_from(tuple(BaseMode)),
        scope=st.sampled_from((FieldScope.LOCAL_STATE, FieldScope.RUNTIME)),
    )
    def test_local_and_runtime_fields_are_always_preserved(
        self,
        base_value: object,
        repo_value: object,
        live_value: object,
        base_mode: BaseMode,
        scope: FieldScope,
    ) -> None:
        base = snapshot_with_field(base_value) if base_mode is BaseMode.PRESENT else None
        plan = plan_reconciliation(
            base=base,
            repo=snapshot_with_field(repo_value),
            live=snapshot_with_field(live_value),
            manifest=manifest_for(scope),
        )

        assert plan.changes
        assert all(change.kind is ChangeKind.PRESERVE_LOCAL for change in plan.changes)
        assert plan.is_converged() is True

    @given(
        base_value=JSON_VALUES,
        repo_value=JSON_VALUES,
        live_value=JSON_VALUES,
        base_mode=st.sampled_from(tuple(BaseMode)),
    )
    def test_unclassified_fields_are_always_unknown(
        self,
        base_value: object,
        repo_value: object,
        live_value: object,
        base_mode: BaseMode,
    ) -> None:
        base = snapshot_with_field(base_value) if base_mode is BaseMode.PRESENT else None
        plan = plan_reconciliation(
            base=base,
            repo=snapshot_with_field(repo_value),
            live=snapshot_with_field(live_value),
            manifest=FieldManifest(rules=()),
        )

        assert plan.changes
        assert all(change.kind is ChangeKind.UNKNOWN for change in plan.changes)
        assert plan.is_converged() is False

    @given(fields=JSON_OBJECTS)
    def test_plan_changes_have_stable_lexicographic_order(
        self,
        fields: dict[str, object],
    ) -> None:
        reversed_fields = dict(reversed(tuple(fields.items())))
        forward_rules = tuple(FieldRule(path=(key,), scope=FieldScope.SHARED) for key in fields)
        reversed_rules = tuple(reversed(forward_rules))

        first = plan_reconciliation(
            base=SemanticSnapshot.from_value(fields),
            repo=SemanticSnapshot.from_value(reversed_fields),
            live=SemanticSnapshot.from_value(fields),
            manifest=FieldManifest(rules=forward_rules),
        )
        second = plan_reconciliation(
            base=SemanticSnapshot.from_value(reversed_fields),
            repo=SemanticSnapshot.from_value(fields),
            live=SemanticSnapshot.from_value(reversed_fields),
            manifest=FieldManifest(rules=reversed_rules),
        )
        paths = [change.path for change in first.changes]

        assert paths == sorted(paths)
        assert first == second
