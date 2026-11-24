"""Text output of the ai-config CLI shows the field values behind every change.

The operator reads these lines to learn what diff, apply and reconcile will do, so
the tests pin the exact shape and, above all, that a sensitive value never reaches
either stream.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from typing import TYPE_CHECKING

import pytest
import yaml
from ai_config import ChangeKind, ReconciliationPlan
from ai_config.adapters import EngineKind, resolve_engine_paths
from ai_config.cli import main
from ai_config.service import (
    DecisionsRequiredError,
    EngineInspection,
    UnknownFieldsError,
    inspect_engine,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ai_config.service import OperationResult

SHARED = {"scope": "shared"}
ORDERED_SET = {"scope": "shared", "strategy": "ordered-set"}
LOCAL_STATE = {"scope": "local-state"}
SECRET = {
    "scope": "environment",
    "binding": "keychain:devbox-example/account",
    "secret": True,
}
REPO_SENSITIVE = "repo-sensitive-value"
LIVE_SENSITIVE = "live-sensitive-value"


@dataclasses.dataclass(frozen=True, slots=True)
class Run:
    code: int
    out: str
    err: str


class Cli:
    def __init__(self, capsys: pytest.CaptureFixture[str]) -> None:
        self.capsys = capsys

    def run(self, *arguments: str | Path) -> Run:
        code = main([str(argument) for argument in arguments])
        captured = self.capsys.readouterr()
        return Run(code=code, out=captured.out, err=captured.err)


@pytest.fixture
def cli(capsys: pytest.CaptureFixture[str]) -> Cli:
    return Cli(capsys)


def explicit_arguments(
    tmp_path: Path,
    *,
    repo: Mapping[str, object],
    live: Mapping[str, object],
    rules: Mapping[str, Mapping[str, object]],
    base: Mapping[str, object] | None = None,
) -> list[str]:
    documents = {"repo": repo, "live": live}
    if base is not None:
        documents["base"] = base
    arguments: list[str] = []
    for name, document in documents.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        arguments.extend([f"--{name}", str(path)])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"fields": [{"path": path, **rule} for path, rule in rules.items()]}),
        encoding="utf-8",
    )
    return [*arguments, "--manifest", str(manifest)]


def engine_tree(
    tmp_path: Path,
    *,
    repository: str,
    manifest_fields: str,
    live: str | None = None,
    variables: Mapping[str, object] | None = None,
) -> list[str]:
    repo_root = tmp_path / "repository"
    home = tmp_path / "home"
    paths = resolve_engine_paths(EngineKind.CLAUDE, repo_root=repo_root, home=home)
    paths.repository.parent.mkdir(parents=True)
    paths.repository.write_text(repository + "\n", encoding="utf-8")
    paths.manifest.write_text(
        '{"schema_version": 1, "engine": "claude", "fields": [' + manifest_fields + "]}\n",
        encoding="utf-8",
    )
    if live is not None:
        paths.live.parent.mkdir(parents=True)
        paths.live.write_text(live + "\n", encoding="utf-8")
    if variables is not None:
        overlay = repo_root / "profiles" / "work.yml"
        overlay.parent.mkdir(parents=True)
        overlay.write_text(yaml.safe_dump(dict(variables)), encoding="utf-8")
    return [
        "claude",
        "--repo-root",
        str(repo_root),
        "--home",
        str(home),
        "--state-root",
        str(tmp_path / "state"),
        "--profile",
        "work",
    ]


MODEL_FIELD = '{"path": "model", "scope": "shared"}'


def model_tree(tmp_path: Path) -> list[str]:
    return engine_tree(
        tmp_path,
        repository='{"model": "repository"}',
        manifest_fields=MODEL_FIELD,
        live='{"model": "live"}',
    )


def inspect(tmp_path: Path) -> EngineInspection:
    return inspect_engine(
        EngineKind.CLAUDE,
        repo_root=tmp_path / "repository",
        home=tmp_path / "home",
        profile="work",
        state_root=tmp_path / "state",
    )


class TestDiffVisibility:
    def test_unchanged_and_preserve_local_are_hidden_by_default(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"moved": "old", "same": 1, "cache": "x"},
            repo={"moved": "new", "same": 1, "cache": "y"},
            live={"moved": "old", "same": 1, "cache": "z"},
            rules={"moved": SHARED, "same": SHARED, "cache": LOCAL_STATE},
        )

        result = cli.run("diff", *arguments)

        assert result.code == 1
        assert result.out == (
            'apply-repo\tmoved\n  - repo: "new"\n  + live: "old"\n'
            "drift apply-repo=1 preserve-local=1 unchanged=1\n"
        )
        assert result.err == ""

    def test_all_lists_unchanged_with_one_value_and_preserve_local_with_both_sides(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"moved": "old", "same": 1, "cache": "x"},
            repo={"moved": "new", "same": 1, "cache": "y"},
            live={"moved": "old", "same": 1, "cache": "z"},
            rules={"moved": SHARED, "same": SHARED, "cache": LOCAL_STATE},
        )

        result = cli.run("diff", "--all", *arguments)

        assert result.code == 1
        assert result.out == (
            'preserve-local\tcache\n  - repo: "y"\n  + live: "z"\n'
            'apply-repo\tmoved\n  - repo: "new"\n  + live: "old"\n'
            "unchanged\tsame\n    value: 1\n"
            "drift apply-repo=1 preserve-local=1 unchanged=1\n"
        )

    def test_a_converged_plan_prints_only_the_converged_summary(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"same": 1, "cache": "x"},
            repo={"same": 1, "cache": "y"},
            live={"same": 1, "cache": "z"},
            rules={"same": SHARED, "cache": LOCAL_STATE},
        )

        result = cli.run("diff", *arguments)

        assert result.code == 0
        assert result.out.splitlines() == ["converged preserve-local=1 unchanged=1"]

    def test_all_on_a_converged_plan_still_reports_converged_last(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"same": 1},
            live={"same": 1},
            rules={"same": SHARED},
        )

        result = cli.run("diff", "--all", *arguments)

        assert result.code == 0
        assert result.out == "unchanged\tsame\n    value: 1\nconverged unchanged=1\n"

    def test_summary_counts_include_the_hidden_kinds(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"a": 1, "b": 2, "c": 3},
            live={"a": 1, "b": 2, "c": 3},
            rules={"a": SHARED, "b": SHARED, "c": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out == "converged unchanged=3\n"

    def test_all_is_a_diff_option_only(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(tmp_path, repo={"a": 1}, live={"a": 1}, rules={"a": SHARED})

        with pytest.raises(SystemExit) as refused:
            cli.run("status", "--all", *arguments)

        assert refused.value.code == 2

    def test_status_text_stays_a_single_summary_without_values(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={"a": "new"}, live={"a": "old"}, rules={"a": SHARED}
        )

        result = cli.run("status", *arguments)

        assert result.code == 1
        assert result.out == "drift initialisation-required=1\n"

    def test_json_output_is_unchanged_by_all(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"a": "new", "same": 1},
            live={"a": "old", "same": 1},
            rules={"a": SHARED, "same": SHARED},
        )

        plain = cli.run("diff", "--json", *arguments)
        everything = cli.run("diff", "--json", "--all", *arguments)

        document = json.loads(plain.out)
        assert plain.out == everything.out
        assert [change["kind"] for change in document["changes"]] == [
            "initialisation-required",
            "unchanged",
        ]
        assert "repo:" not in plain.out
        assert document["changes"][0]["repo"] == "new"


class TestKindSpecificLines:
    def test_conflict_shows_base_before_repo_and_live(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"v": "b"},
            repo={"v": "r"},
            live={"v": "l"},
            rules={"v": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'conflict\tv\n    base: "b"\n  - repo: "r"\n  + live: "l"\ndrift conflict=1\n'
        )

    def test_merge_shows_the_merged_value_last(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"v": ["a"]},
            repo={"v": ["a", "r"]},
            live={"v": ["a", "l"]},
            rules={"v": ORDERED_SET},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'merge\tv\n  - repo: ["a","r"]\n  + live: ["a","l"]\n    merged: ["a","r","l"]\n'
            "drift merge=1\n"
        )

    def test_a_planned_merge_that_resolves_to_one_side_shows_no_merged_line(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"v": ["a"]},
            repo={"v": ["a"]},
            live={"v": ["a", "l"]},
            rules={"v": ORDERED_SET},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'capture-live\tv\n  - repo: ["a"]\n  + live: ["a","l"]\ndrift capture-live=1\n'
        )

    def test_capture_live_and_apply_repo_show_only_repo_and_live(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"captured": "old", "applied": "old"},
            repo={"captured": "old", "applied": "new"},
            live={"captured": "new", "applied": "old"},
            rules={"captured": SHARED, "applied": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'apply-repo\tapplied\n  - repo: "new"\n  + live: "old"\n'
            'capture-live\tcaptured\n  - repo: "old"\n  + live: "new"\n'
            "drift apply-repo=1 capture-live=1\n"
        )

    def test_initialisation_required_without_base_state_shows_both_sides(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={"v": "r"}, live={"v": "l"}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'initialisation-required\tv\n  - repo: "r"\n  + live: "l"\n'
            "drift initialisation-required=1\n"
        )

    def test_unknown_field_shows_its_values_too(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"known": 1, "stray": "r"},
            live={"known": 1},
            rules={"known": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'unknown\tstray\n  - repo: "r"\n  + live: <missing>\ndrift unknown=1 unchanged=1\n'
        )

    def test_dotted_manifest_path_is_the_header_path(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"permissions": {"allow": ["Read"]}},
            live={"permissions": {"allow": ["Write"]}},
            rules={"permissions.allow": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out == (
            'initialisation-required\tpermissions.allow\n  - repo: ["Read"]\n'
            '  + live: ["Write"]\ndrift initialisation-required=1\n'
        )

    def test_a_templated_path_is_flagged_in_the_header_and_still_shows_values(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"model": "{{ devbox_model }}"}',
            manifest_fields=MODEL_FIELD,
            live='{"model": "live"}',
            variables={"devbox_model": "rendered"},
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines()[:3] == [
            "apply-repo\tmodel\ttemplated",
            '  - repo: "rendered"',
            '  + live: "live"',
        ]


class TestValueRendering:
    @pytest.mark.parametrize(
        ("value", "rendered"),
        [
            (None, "null"),
            (True, "true"),
            (False, "false"),
            (3, "3"),
            (2.5, "2.5"),
            ("", '""'),
            ("text", '"text"'),
            ("<missing>", '"<missing>"'),
            ("<redacted>", '"<redacted>"'),
            ("héllo → 日本", '"héllo → 日本"'),
            ('say "hi"\\', '"say \\"hi\\"\\\\"'),
            ([], "[]"),
            ([1, "a", None, [True]], '[1,"a",null,[true]]'),
        ],
    )
    def test_values_are_compact_json_on_one_line(
        self, tmp_path: Path, cli: Cli, value: object, rendered: str
    ) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={"v": value}, live={"v": "other"}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines()[1] == f"  - repo: {rendered}"

    def test_a_newline_in_a_value_is_escaped_so_the_block_stays_three_lines(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"v": "first\nsecond\r\nthird"},
            live={"v": "a\nb"},
            rules={"v": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines() == [
            "initialisation-required\tv",
            '  - repo: "first\\nsecond\\r\\nthird"',
            '  + live: "a\\nb"',
            "drift initialisation-required=1",
        ]

    def test_a_missing_repo_value_is_marked_missing(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={}, live={"v": "present"}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines()[:3] == [
            "initialisation-required\tv",
            "  - repo: <missing>",
            '  + live: "present"',
        ]

    def test_a_missing_live_value_is_marked_missing(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={"v": "present"}, live={}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines()[:3] == [
            "initialisation-required\tv",
            '  - repo: "present"',
            "  + live: <missing>",
        ]

    def test_a_missing_base_in_a_conflict_is_marked_missing(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path,
            base={"other": 1},
            repo={"v": "r"},
            live={"v": "l"},
            rules={"v": SHARED, "other": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert result.out.splitlines()[:4] == [
            "conflict\tv",
            "    base: <missing>",
            '  - repo: "r"',
            '  + live: "l"',
        ]

    @pytest.mark.parametrize(
        ("inner_length", "truncated"),
        [(97, False), (98, False), (99, True), (100, True), (500, True)],
    )
    def test_a_value_is_cut_at_exactly_one_hundred_characters(
        self, tmp_path: Path, cli: Cli, inner_length: int, *, truncated: bool
    ) -> None:
        text = "x" * inner_length
        arguments = explicit_arguments(
            tmp_path, repo={"v": text}, live={"v": "short"}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        shown = result.out.splitlines()[1].removeprefix("  - repo: ")
        if truncated:
            assert len(shown) == 100
            assert shown == '"' + "x" * 98 + "…"
        else:
            assert shown == f'"{text}"'
            assert len(shown) == inner_length + 2

    def test_the_cap_counts_characters_not_bytes(self, tmp_path: Path, cli: Cli) -> None:
        arguments = explicit_arguments(
            tmp_path, repo={"v": "日" * 150}, live={"v": "short"}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        shown = result.out.splitlines()[1].removeprefix("  - repo: ")
        assert shown == '"' + "日" * 98 + "…"

    def test_a_terminal_escape_in_a_value_is_not_emitted_raw(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"v": "\x1b[31mred\x07"},
            live={"v": "plain"},
            rules={"v": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert "\x1b" not in result.out
        assert "\x07" not in result.out
        assert result.out.splitlines()[1] == '  - repo: "\\u001b[31mred\\u0007"'

    def test_a_long_array_is_cut_mid_value_with_an_ellipsis(self, tmp_path: Path, cli: Cli) -> None:
        items = [f"item-{index:03d}" for index in range(40)]
        arguments = explicit_arguments(
            tmp_path, repo={"v": items}, live={"v": []}, rules={"v": SHARED}
        )

        result = cli.run("diff", *arguments)

        shown = result.out.splitlines()[1].removeprefix("  - repo: ")
        assert len(shown) == 100
        assert shown == json.dumps(items, separators=(",", ":"), ensure_ascii=False)[:99] + "…"

    def test_the_cap_applies_to_the_base_and_merged_lines_too(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        long_items = ["m" * 60, "n" * 60]
        arguments = explicit_arguments(
            tmp_path,
            base={"v": []},
            repo={"v": [long_items[0]]},
            live={"v": [long_items[1]]},
            rules={"v": ORDERED_SET},
        )

        result = cli.run("diff", *arguments)

        merged = next(line for line in result.out.splitlines() if "merged:" in line)
        assert len(merged.removeprefix("    merged: ")) == 100
        assert merged.endswith("…")


class TestSensitiveValuesNeverPrinted:
    def secret_arguments(self, tmp_path: Path, *, live: Mapping[str, object]) -> list[str]:
        return explicit_arguments(
            tmp_path,
            repo={"token": REPO_SENSITIVE, "model": "repo-model"},
            live=live,
            rules={"token": SECRET, "model": SHARED},
        )

    @pytest.mark.parametrize("flags", [(), ("--all",)])
    def test_diff_redacts_both_sides(
        self, tmp_path: Path, cli: Cli, flags: tuple[str, ...]
    ) -> None:
        arguments = self.secret_arguments(
            tmp_path, live={"token": LIVE_SENSITIVE, "model": "repo-model"}
        )

        result = cli.run("diff", *flags, *arguments)

        assert REPO_SENSITIVE not in result.out + result.err
        assert LIVE_SENSITIVE not in result.out + result.err
        assert "apply-repo\ttoken\n  - repo: <redacted>\n  + live: <redacted>\n" in result.out

    def test_a_missing_sensitive_side_is_redacted_not_reported_missing(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = self.secret_arguments(tmp_path, live={"model": "repo-model"})

        result = cli.run("diff", "--all", *arguments)

        assert "<missing>" not in result.out
        assert "token\n  - repo: <redacted>\n  + live: <redacted>\n" in result.out

    def test_a_missing_repo_side_of_a_sensitive_field_is_redacted(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"model": "m"},
            live={"token": LIVE_SENSITIVE, "model": "m"},
            rules={"token": SECRET, "model": SHARED},
        )

        result = cli.run("diff", *arguments)

        assert LIVE_SENSITIVE not in result.out
        assert "  - repo: <redacted>\n  + live: <redacted>\n" in result.out

    def test_an_unchanged_sensitive_field_listed_by_all_shows_only_the_marker(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = explicit_arguments(
            tmp_path,
            repo={"token": REPO_SENSITIVE},
            live={"token": REPO_SENSITIVE},
            rules={"token": SECRET},
        )

        result = cli.run("diff", "--all", *arguments)

        assert REPO_SENSITIVE not in result.out
        assert result.out == "unchanged\ttoken\n    value: <redacted>\nconverged unchanged=1\n"

    def test_a_sensitive_value_is_not_leaked_by_a_truncated_neighbour_or_the_summary(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = self.secret_arguments(
            tmp_path, live={"token": LIVE_SENSITIVE, "model": "other-model"}
        )

        result = cli.run("diff", "--all", *arguments)

        assert LIVE_SENSITIVE not in result.out + result.err
        assert REPO_SENSITIVE not in result.out + result.err
        assert '  - repo: "repo-model"' in result.out

    def test_json_output_still_redacts(self, tmp_path: Path, cli: Cli) -> None:
        arguments = self.secret_arguments(
            tmp_path, live={"token": LIVE_SENSITIVE, "model": "repo-model"}
        )

        result = cli.run("diff", "--json", *arguments)

        assert REPO_SENSITIVE not in result.out
        assert LIVE_SENSITIVE not in result.out


class TestOperationResultListing:
    def test_apply_lists_each_written_change_with_values_before_the_summary(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"setting": "repository"}',
            manifest_fields='{"path": "setting", "scope": "shared"}',
        )

        result = cli.run("apply", *arguments)

        assert result.code == 0
        assert result.out == (
            'initialisation-required\tsetting\n  - repo: "repository"\n  + live: <missing>\n'
            "claude: changed applied=1 captured=0 preserved=0\n"
        )

    def test_check_mode_lists_the_same_changes_and_says_it_would_change(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"setting": "repository"}',
            manifest_fields='{"path": "setting", "scope": "shared"}',
        )

        result = cli.run("apply", "--check", *arguments)

        assert result.code == 0
        assert result.out == (
            'initialisation-required\tsetting\n  - repo: "repository"\n  + live: <missing>\n'
            "claude: would change applied=1 captured=0 preserved=0\n"
        )
        assert not (tmp_path / "state").exists()

    def test_a_converged_second_run_prints_only_the_summary(self, tmp_path: Path, cli: Cli) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"setting": "repository"}',
            manifest_fields='{"path": "setting", "scope": "shared"}',
        )
        assert cli.run("apply", *arguments).code == 0

        result = cli.run("apply", *arguments)

        assert result.code == 0
        assert result.out == "claude: unchanged applied=0 captured=0 preserved=0\n"

    def test_unchanged_and_preserve_local_changes_are_not_listed(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"same": "s", "setting": "repository", "cache": "repo-cache"}',
            manifest_fields=(
                '{"path": "same", "scope": "shared"},'
                '{"path": "setting", "scope": "shared"},'
                '{"path": "cache", "scope": "local-state"}'
            ),
            live='{"same": "s", "setting": "repository", "cache": "live-cache"}',
        )
        assert cli.run("apply", *arguments).code == 0
        live = tmp_path / "home" / ".claude" / "settings.json"
        live.write_text(
            '{"same": "s", "setting": "repository", "cache": "newer-cache"}\n', encoding="utf-8"
        )

        result = cli.run("apply", *arguments)

        assert result.code == 0
        assert "same" not in result.out
        assert "cache" not in result.out
        assert result.out == "claude: unchanged applied=0 captured=0 preserved=1\n"

    def test_a_reconcile_decision_is_listed_with_both_values(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = model_tree(tmp_path)
        decisions = tmp_path / "decisions.json"
        decisions.write_text(
            '{"decisions": [{"path": ["model"], "source": "live"}]}\n', encoding="utf-8"
        )

        result = cli.run("reconcile", "--decisions", decisions, *arguments)

        assert result.code == 0
        assert result.out == (
            'initialisation-required\tmodel\n  - repo: "repository"\n  + live: "live"\n'
            "claude: changed applied=0 captured=1 preserved=0\n"
        )

    def test_json_output_is_a_single_document_without_value_lines(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"setting": "repository"}',
            manifest_fields='{"path": "setting", "scope": "shared"}',
        )

        result = cli.run("apply", "--json", *arguments)

        assert json.loads(result.out)["applied"] == 1
        assert "repo:" not in result.out

    @pytest.mark.parametrize("flags", [(), ("--check",)])
    def test_a_sensitive_change_in_the_result_is_redacted(
        self, tmp_path: Path, cli: Cli, flags: tuple[str, ...]
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository=json.dumps({"token": "@home@/.claude/secret-source", "model": "m"}),
            manifest_fields=(
                '{"path": "model", "scope": "shared"},'
                '{"path": "token", "scope": "environment",'
                ' "binding": "home:.claude/secret-source", "secret": true}'
            ),
            live=json.dumps({"token": LIVE_SENSITIVE, "model": "m"}),
        )

        result = cli.run("apply", *flags, *arguments)

        assert result.code == 0
        assert LIVE_SENSITIVE not in result.out + result.err
        assert str(tmp_path / "home") not in result.out + result.err
        assert "apply-repo\ttoken\n  - repo: <redacted>\n  + live: <redacted>\n" in result.out


class TestStoppedOperations:
    def test_apply_stopping_on_a_field_decision_shows_its_repo_and_live_values(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = model_tree(tmp_path)

        result = cli.run("apply", *arguments)

        assert result.code == 1
        assert result.out == ""
        assert result.err == (
            "reconciliation requires explicit field decisions\n"
            '  model\n    - repo: "repository"\n    + live: "live"\n'
        )

    def test_every_required_path_gets_its_own_block(self, tmp_path: Path, cli: Cli) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"alpha": "a-repo", "beta": ["b-repo"]}',
            manifest_fields=(
                '{"path": "alpha", "scope": "shared"},{"path": "beta", "scope": "shared"}'
            ),
            live='{"alpha": "a-live", "beta": []}',
        )

        result = cli.run("apply", *arguments)

        assert result.err.splitlines() == [
            "reconciliation requires explicit field decisions",
            "  alpha",
            '    - repo: "a-repo"',
            '    + live: "a-live"',
            "  beta",
            '    - repo: ["b-repo"]',
            "    + live: []",
        ]

    def test_json_decisions_required_stays_machine_readable_with_a_silent_stderr(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = model_tree(tmp_path)

        result = cli.run("apply", "--json", *arguments)

        document = json.loads(result.out)
        assert document["requires_decisions"] is True
        assert document["decision_paths"] == [["model"]]
        assert result.err == ""

    def test_unknown_fields_stop_apply_and_show_the_values_under_each_path(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"model": "repository", "stray": {"a": 1}}',
            manifest_fields=MODEL_FIELD,
            live='{"model": "repository", "stray": 2}',
        )

        result = cli.run("apply", *arguments)

        assert result.code == 1
        assert result.out == ""
        assert result.err.splitlines()[0] == "unknown fields block configuration writes"
        assert result.err.splitlines()[1:] == [
            "  stray",
            "    - repo: <missing>",
            "    + live: 2",
            "  stray.a",
            "    - repo: 1",
            "    + live: <missing>",
        ]

    def test_bootstrap_stopping_on_an_unknown_field_shows_its_values(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"model": "repository"}',
            manifest_fields=MODEL_FIELD,
            live='{"model": "live", "stray": "extra"}',
        )

        result = cli.run("bootstrap", "--from-live", *arguments)

        assert result.code == 1
        assert result.err == (
            "unknown fields block configuration writes\n"
            '  stray\n    - repo: <missing>\n    + live: "extra"\n'
        )

    def test_long_values_are_capped_in_the_error_lists_too(self, tmp_path: Path, cli: Cli) -> None:
        arguments = engine_tree(
            tmp_path,
            repository=json.dumps({"model": "y" * 300}),
            manifest_fields=MODEL_FIELD,
            live='{"model": "live"}',
        )

        result = cli.run("apply", *arguments)

        repo_line = next(line for line in result.err.splitlines() if "- repo:" in line)
        assert len(repo_line.removeprefix("    - repo: ")) == 100
        assert repo_line.endswith("…")

    @pytest.mark.parametrize("error_kind", [DecisionsRequiredError, UnknownFieldsError])
    def test_a_sensitive_path_in_an_error_list_is_redacted_on_stderr(
        self,
        tmp_path: Path,
        cli: Cli,
        monkeypatch: pytest.MonkeyPatch,
        error_kind: type[DecisionsRequiredError | UnknownFieldsError],
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository=json.dumps({"token": "@home@/.claude/secret-source", "model": "m"}),
            manifest_fields=(
                '{"path": "model", "scope": "shared"},'
                '{"path": "token", "scope": "environment",'
                ' "binding": "home:.claude/secret-source", "secret": true}'
            ),
            live=json.dumps({"token": LIVE_SENSITIVE, "model": "m"}),
        )
        inspection = inspect(tmp_path)
        token = next(change for change in inspection.plan.changes if change.path == ("token",))
        sensitive = dataclasses.replace(
            token,
            kind=ChangeKind.CONFLICT,
            base=inspection.live.semantic_fields()[0].value,
            sensitive=True,
        )
        stopped = dataclasses.replace(inspection, plan=ReconciliationPlan(changes=(sensitive,)))

        def refuse(*_arguments: object, **_keywords: object) -> OperationResult:
            raise error_kind(stopped, (("token",),))

        monkeypatch.setattr("ai_config.cli.operate_engine", refuse)

        result = cli.run("apply", *arguments)

        assert result.code == 1
        assert LIVE_SENSITIVE not in result.out + result.err
        assert result.err.splitlines()[1:] == [
            "  token",
            "      base: <redacted>",
            "    - repo: <redacted>",
            "    + live: <redacted>",
        ]

    def test_a_path_without_a_planned_change_is_listed_by_name_only(
        self,
        tmp_path: Path,
        cli: Cli,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        arguments = model_tree(tmp_path)
        inspection = inspect(tmp_path)

        def refuse(*_arguments: object, **_keywords: object) -> OperationResult:
            raise DecisionsRequiredError(inspection, (("ghost",),))

        monkeypatch.setattr("ai_config.cli.operate_engine", refuse)

        result = cli.run("apply", *arguments)

        assert result.err == "reconciliation requires explicit field decisions\n  ghost\n"


class TestInteractiveReconcile:
    def test_the_operator_sees_values_before_the_question_and_the_result_lists_them(
        self,
        tmp_path: Path,
        cli: Cli,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        arguments = model_tree(tmp_path)
        asked: list[str] = []

        def answer(prompt: str) -> str:
            asked.append(prompt + "|" + capsys.readouterr().err)
            return "live"

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        monkeypatch.setattr("builtins.input", answer)

        result = cli.run("reconcile", *arguments)

        assert result.code == 0
        assert asked == [
            (
                "model (initialisation-required) [repo/live]: |"
                "Answer 'repo' or 'live'; append '!' to settle every remaining change "
                "of that kind.\n"
                "initialisation-required\tmodel\n"
                '  - repo: "repository"\n'
                '  + live: "live"\n'
            )
        ]
        assert result.out == (
            'initialisation-required\tmodel\n  - repo: "repository"\n  + live: "live"\n'
            "claude: changed applied=0 captured=1 preserved=0\n"
        )


class TestEngineStateMissing:
    def test_a_missing_state_is_drift_even_when_nothing_differs(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = engine_tree(
            tmp_path,
            repository='{"model": "same"}',
            manifest_fields=MODEL_FIELD,
            live='{"model": "same"}',
        )

        result = cli.run("diff", *arguments)

        assert result.code == 1
        assert result.out == "drift unchanged=1 state-initialisation-required=1\n"

    def test_a_missing_state_is_reported_after_the_change_blocks(
        self, tmp_path: Path, cli: Cli
    ) -> None:
        arguments = model_tree(tmp_path)

        result = cli.run("diff", *arguments)

        assert result.code == 1
        assert result.out == (
            'initialisation-required\tmodel\n  - repo: "repository"\n  + live: "live"\n'
            "drift initialisation-required=1 state-initialisation-required=1\n"
        )
