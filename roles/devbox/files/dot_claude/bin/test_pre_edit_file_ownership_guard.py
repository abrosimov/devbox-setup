from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pre_edit_file_ownership_guard as guard

if TYPE_CHECKING:
    from collections.abc import Mapping

# The source of ~/.claude/agents, so the role tests run against the globs that ship.
SHIPPED_AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "dot_ai" / "agents"

GO_ENGINEER = "software-engineer-go"
PYTHON_ENGINEER = "software-engineer-python"
FRONTEND_ENGINEER = "software-engineer-frontend"
UNIT_TEST_WRITER = "unit-test-writer"


def _write_agent(agents_dir: Path, stem: str, body: str) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{stem}.md").write_text(body, encoding="utf-8")


def _agent_md(name: str, globs: str | None) -> str:
    globs_line = "" if globs is None else f"globs: {globs}\n"
    return f"---\nname: {name}\ndescription: d\n{globs_line}---\nbody\n"


def _repo(root: Path) -> Path:
    (root / ".git").mkdir(parents=True)
    return root


def _payload(
    agent: object,
    path: str,
    *,
    key: str = "file_path",
    cwd: object = None,
) -> dict[str, object]:
    data: dict[str, object] = {"agent_type": agent, "tool_input": {key: path}}
    if cwd is not None:
        data["cwd"] = cwd
    return data


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**/*_test.go", "/r/a/b/x_test.go", True),
        ("**/*_test.go", "/x_test.go", True),
        ("**/*_test.go", "x_test.go", True),
        ("**/*_test.go", "/r/x_test.go.bak", False),
        ("**/*_test.go", "/r/x_test.gox", False),
        ("**/testdata/**", "/r/pkg/testdata/f.json", True),
        ("**/testdata/**", "/r/pkg/testdata/deep/er/f.json", True),
        ("**/testdata/**", "/r/pkg/testdatax/f.json", False),
        ("**/testdata/**", "/r/pkg/mytestdata/f.json", False),
        ("**/tests/**", "/r/tests/a/b.py", True),
        ("**/tests/**", "tests/a.py", True),
        ("**/tests/**", "/r/mytests/a.py", False),
        ("**/tests/**", "/r/tests.py", False),
        ("/r/*.py", "/r/a.py", True),
        ("/r/*.py", "/r/sub/a.py", False),
        ("/r/*.py", "/x/r/a.py", False),
        ("/r/?.py", "/r/a.py", True),
        ("/r/?.py", "/r/ab.py", False),
        ("/r/?.py", "/r/.py", False),
        ("/r/a?b.py", "/r/a/b.py", False),
        ("**/*.test.*", "/r/src/a.test.tsx", True),
        ("**/*.test.*", "/r/src/a.test", False),
        ("**/__mocks__/**", "/r/src/__mocks__/x.ts", True),
        ("tests/**", "/r/x/tests/a.py", True),
        ("tests/**", "tests/a.py", True),
        ("tests/**", "/r/x/mytests/a.py", False),
        ("**/a+b.py", "/r/a+b.py", True),
        ("**/a+b.py", "/r/aab.py", False),
        ("**/a.py", "/r/aXpy", False),
        ("**/(x)|y.py", "/r/(x)|y.py", True),
        ("**/(x)|y.py", "/r/y.py", False),
        ("**/[ab].py", "/r/[ab].py", True),
        ("**/[ab].py", "/r/a.py", False),
    ],
)
def test_path_matches(pattern: str, path: str, *, expected: bool) -> None:
    assert guard.path_matches(pattern, path) is expected


def test_glob_to_regex_star_never_crosses_a_separator() -> None:
    assert guard.glob_to_regex("*.py").fullmatch("a.py") is not None
    assert guard.glob_to_regex("/*.py").fullmatch("/a/b.py") is None


@pytest.mark.parametrize(
    ("tool_input", "expected"),
    [
        ({"file_path": "/r/a.py"}, "/r/a.py"),
        ({"notebook_path": "/r/n.ipynb"}, "/r/n.ipynb"),
        ({"file_path": "/r/a.py", "notebook_path": "/r/n.ipynb"}, "/r/a.py"),
        ({"file_path": "", "notebook_path": "/r/n.ipynb"}, "/r/n.ipynb"),
        ({"file_path": 7, "notebook_path": "/r/n.ipynb"}, "/r/n.ipynb"),
        ({"file_path": "/r/tests/../src/m.py"}, "/r/src/m.py"),
        ({"file_path": "/r/src/../tests/test_a.py"}, "/r/tests/test_a.py"),
        ({"file_path": "/r//src/./m.py"}, "/r/src/m.py"),
        ({}, ""),
        ({"file_path": ""}, ""),
        ({"file_path": None}, ""),
        ({"file_path": 42}, ""),
        ({"file_path": ["/r/a.py"]}, ""),
        ({"notebook_path": ""}, ""),
    ],
)
def test_target_path(tool_input: dict[str, object], expected: str) -> None:
    assert guard.target_path(tool_input) == expected


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("**/*.fuzz.{js,ts}", ["**/*.fuzz.js", "**/*.fuzz.ts"]),
        ("{a,{b,c}}", ["a", "b", "c"]),
        ("{a,{b,c},d}", ["a", "b", "c", "d"]),
        ("{{a,b}}", ["{a}", "{b}"]),
        ("x{a,b}y{1,2}", ["xay1", "xay2", "xby1", "xby2"]),
        ("x{,a}", ["x", "xa"]),
        ("{a}", ["{a}"]),
        ("{}", ["{}"]),
        ("{a", ["{a"]),
        ("a}", ["a}"]),
        ("{a,{b,c}", ["{a,b", "{a,c"]),
        ("**/*.py", ["**/*.py"]),
        ("", [""]),
    ],
)
def test_expand_braces(pattern: str, expected: list[str]) -> None:
    assert guard.expand_braces(pattern) == expected


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**/*.fuzz.{js,ts}", "src/x.fuzz.ts", True),
        ("**/*.fuzz.{js,ts}", "x.fuzz.js", True),
        ("**/*.fuzz.{js,ts}", "x.fuzz.tsx", False),
        ("**/*.fuzz.{js,ts}", "x.fuzz.{js,ts}", False),
        ("{src,lib}/**", "src/a/b.py", True),
        ("{src,lib}/**", "lib/a.py", True),
        ("{src,lib}/**", "r/lib/a.py", True),
        ("{src,lib}/**", "bin/a.py", False),
        ("x.{a}", "x.{a}", True),
        ("x.{a}", "x.a", False),
        ("{a", "{a", True),
    ],
)
def test_path_matches_expands_braces(pattern: str, path: str, *, expected: bool) -> None:
    assert guard.path_matches(pattern, path) is expected


def test_load_agent_globs_found_by_frontmatter_name_not_file_name(tmp_path: Path) -> None:
    _write_agent(tmp_path, "unrelated_file_name", _agent_md("my-agent", '["**/*.go", "!x"]'))
    _write_agent(tmp_path, "my-agent", _agent_md("someone-else", '["**/*.rs"]'))

    assert guard.load_agent_globs(tmp_path) == {
        "my-agent": ["**/*.go", "!x"],
        "someone-else": ["**/*.rs"],
    }


@pytest.mark.parametrize(
    "body",
    [
        _agent_md("my-agent", None),
        _agent_md("my-agent", ""),
        _agent_md("my-agent", "[]"),
        _agent_md("my-agent", "[**/*.go]"),
        _agent_md("my-agent", "['**/*.go']"),
        _agent_md("my-agent", '["**/*.go", ""]'),
        _agent_md("my-agent", "[1]"),
        _agent_md("my-agent", '"**/*.go"'),
    ],
)
def test_load_agent_globs_unusable_globs_yield_empty_list(tmp_path: Path, body: str) -> None:
    _write_agent(tmp_path, "my_agent", body)

    assert guard.load_agent_globs(tmp_path) == {"my-agent": []}


@pytest.mark.parametrize(
    "body",
    [
        'name: my-agent\nglobs: ["!**/*"]\n',
        '---\nname: my-agent\nglobs: ["!**/*"]\n',
        '---\ndescription: d\nglobs: ["**/*.go"]\n---\nbody\n',
        '---\nname:\nglobs: ["**/*.go"]\n---\nbody\n',
        "",
    ],
)
def test_load_agent_globs_definition_without_name_is_skipped(tmp_path: Path, body: str) -> None:
    _write_agent(tmp_path, "my_agent", body)

    assert guard.load_agent_globs(tmp_path) == {}


def test_load_agent_globs_missing_directory_is_empty(tmp_path: Path) -> None:
    assert guard.load_agent_globs(tmp_path / "absent") == {}


def test_load_agent_globs_skips_non_utf8_file_and_keeps_reading(tmp_path: Path) -> None:
    (tmp_path / "a_broken.md").write_bytes(b"---\nname: broken\n\xff\xfe\n---\n")
    _write_agent(tmp_path, "b_valid", _agent_md("my-agent", '["!**/tests/**"]'))

    assert guard.load_agent_globs(tmp_path) == {"my-agent": ["!**/tests/**"]}


def test_load_agent_globs_non_utf8_only_file_is_empty(tmp_path: Path) -> None:
    (tmp_path / "broken.md").write_bytes(b"---\nname: my-agent\n\xff\xfe\n---\n")

    assert guard.load_agent_globs(tmp_path) == {}


def test_load_agent_globs_ignores_non_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "my_agent.toml").write_text(_agent_md("my-agent", '["!**/*"]'), encoding="utf-8")

    assert guard.load_agent_globs(tmp_path) == {}


def test_load_agent_globs_duplicate_name_first_sorted_file_wins(tmp_path: Path) -> None:
    _write_agent(tmp_path, "b_second", _agent_md("my-agent", '["**/*.rs"]'))
    _write_agent(tmp_path, "a_first", _agent_md("my-agent", '["**/*.go"]'))
    _write_agent(tmp_path, "c_third", _agent_md("my-agent", '["**/*.py"]'))

    assert guard.load_agent_globs(tmp_path) == {"my-agent": ["**/*.go"]}


def test_repository_root_with_git_directory(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")

    assert guard.repository_root(root / "src" / "a.py") == root


def test_repository_root_with_git_file_worktree(tmp_path: Path) -> None:
    worktree = tmp_path / "proj" / "feature_x"
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/feature_x\n")

    assert guard.repository_root(worktree / "src" / "a.ts") == worktree


def test_repository_root_nested_repositories_pick_the_nearest(tmp_path: Path) -> None:
    outer = _repo(tmp_path / "outer")
    inner = _repo(outer / "vendor" / "inner")

    assert guard.repository_root(inner / "tests" / "t.py") == inner
    assert guard.repository_root(outer / "tests" / "t.py") == outer


def test_repository_root_non_existent_target_resolves_via_ancestors(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")

    assert guard.repository_root(root / "new" / "dir" / "test_new.py") == root


def test_repository_root_without_git_is_none(tmp_path: Path) -> None:
    assert guard.repository_root(tmp_path / "src" / "a.py") is None


def test_repository_root_oserror_is_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path / "proj")

    def raise_permission_error(_self: Path) -> bool:
        raise PermissionError

    monkeypatch.setattr(Path, "exists", raise_permission_error)

    assert guard.repository_root(tmp_path / "proj" / "a.py") is None


def test_matched_path_inside_repository_is_relative_to_root(tmp_path: Path) -> None:
    root = _repo(tmp_path / "tests" / "proj")

    assert guard.matched_path(str(root / "src" / "main.py"), str(tmp_path)) == "src/main.py"


def test_matched_path_repository_wins_over_cwd(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")

    assert guard.matched_path(str(root / "pkg" / "a.go"), str(root / "pkg")) == "pkg/a.go"


def test_matched_path_without_repository_is_relative_to_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "test" / "proj"

    assert guard.matched_path(str(cwd / "lib" / "a.py"), str(cwd)) == "lib/a.py"


def test_matched_path_cwd_is_normalised(tmp_path: Path) -> None:
    cwd = tmp_path / "test" / "proj"

    assert guard.matched_path(str(cwd / "lib" / "a.py"), f"{cwd}/../proj/") == "lib/a.py"


def test_matched_path_cwd_prefix_of_a_sibling_is_not_an_ancestor(tmp_path: Path) -> None:
    target = tmp_path / "project" / "a.py"

    assert guard.matched_path(str(target), str(tmp_path / "proj")) == str(target)


def test_matched_path_without_repository_outside_cwd_is_absolute(tmp_path: Path) -> None:
    target = tmp_path / "other" / "a.py"

    assert guard.matched_path(str(target), str(tmp_path / "cwd")) == str(target)


@pytest.mark.parametrize("cwd", ["", "relative/dir", "."])
def test_matched_path_unusable_cwd_is_absolute(tmp_path: Path, cwd: str) -> None:
    target = tmp_path / "lib" / "a.py"

    assert guard.matched_path(str(target), cwd) == str(target)


@pytest.mark.parametrize("path", ["tests/test_a.py", "src/a.py", "../x/a.py"])
def test_matched_path_relative_target_returned_as_is(tmp_path: Path, path: str) -> None:
    _repo(tmp_path)

    assert guard.matched_path(path, str(tmp_path)) == path


@pytest.mark.parametrize(
    ("agent", "relative", "pattern"),
    [
        (GO_ENGINEER, "pkg/x_test.go", "!**/*_test.go"),
        (GO_ENGINEER, "x_test.go", "!**/*_test.go"),
        (GO_ENGINEER, "pkg/testdata/golden.json", "!**/testdata/**"),
        (PYTHON_ENGINEER, "tests/test_a.py", "!**/test_*.py"),
        (PYTHON_ENGINEER, "src/pkg/a_test.py", "!**/*_test.py"),
        (PYTHON_ENGINEER, "conftest.py", "!**/conftest.py"),
        (PYTHON_ENGINEER, "tests/helpers.py", "!**/tests/**"),
        (PYTHON_ENGINEER, "test/helpers.py", "!**/test/**"),
        (FRONTEND_ENGINEER, "src/a.spec.ts", "!**/*.spec.*"),
        (FRONTEND_ENGINEER, "src/a.test.tsx", "!**/*.test.*"),
        (FRONTEND_ENGINEER, "src/__tests__/a.tsx", "!**/__tests__/**"),
        (FRONTEND_ENGINEER, "src/__mocks__/api.ts", "!**/__mocks__/**"),
        (FRONTEND_ENGINEER, "tests/setup.ts", "!**/tests/**"),
        (FRONTEND_ENGINEER, "e2e/login.ts", "!**/e2e/**"),
    ],
)
def test_decide_denies_engineer_edit_of_test_file(
    tmp_path: Path,
    agent: str,
    relative: str,
    pattern: str,
) -> None:
    root = _repo(tmp_path / "proj")
    target = str(root / relative)

    reason = guard.decide(_payload(agent, target), SHIPPED_AGENTS_DIR)

    assert reason is not None
    assert agent in reason
    assert target in reason
    assert pattern in reason


@pytest.mark.parametrize(
    ("agent", "relative"),
    [
        (GO_ENGINEER, "pkg/x.go"),
        (GO_ENGINEER, "cmd/testing.go"),
        (PYTHON_ENGINEER, "src/pkg/a.py"),
        (PYTHON_ENGINEER, "src/pkg/testing_utils.py"),
        (GO_ENGINEER, "internal/observability/tracer.go"),
        (FRONTEND_ENGINEER, "src/app.ts"),
        (FRONTEND_ENGINEER, "src/components/latest.tsx"),
    ],
)
def test_decide_allows_engineer_edit_of_production_file(
    tmp_path: Path,
    agent: str,
    relative: str,
) -> None:
    root = _repo(tmp_path / "proj")

    assert guard.decide(_payload(agent, str(root / relative)), SHIPPED_AGENTS_DIR) is None


def test_decide_denies_notebook_edit_via_notebook_path(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")
    target = str(root / "tests" / "n.ipynb")

    reason = guard.decide(
        _payload(PYTHON_ENGINEER, target, key="notebook_path"),
        SHIPPED_AGENTS_DIR,
    )

    assert reason is not None
    assert target in reason


def test_decide_path_traversal_into_tests_is_denied(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")
    target = f"{root}/src/../tests/test_a.py"

    reason = guard.decide(_payload(PYTHON_ENGINEER, target), SHIPPED_AGENTS_DIR)

    assert reason is not None
    assert f"{root}/tests/test_a.py" in reason


@pytest.mark.parametrize(
    "relative",
    [
        "pkg/x_test.go",
        "pkg/testdata/f.json",
        "tests/test_a.py",
        "conftest.py",
        "src/a.spec.ts",
        "src/__mocks__/x.ts",
        "e2e/login.spec.ts",
        "docs/README.md",
    ],
)
def test_decide_unit_test_writer_is_allowed_on_its_own_and_unclaimed_paths(
    tmp_path: Path, relative: str
) -> None:
    root = _repo(tmp_path / "proj")

    assert (
        guard.decide(_payload(UNIT_TEST_WRITER, str(root / relative)), SHIPPED_AGENTS_DIR) is None
    )


@pytest.mark.parametrize(
    ("agent", "relative", "cause"),
    [
        (
            PYTHON_ENGINEER,
            "tests/helpers.py",
            "its globs exclude it (!**/tests/**) and it is owned by unit-test-writer",
        ),
        (
            PYTHON_ENGINEER,
            "tests/test_a.py",
            "its globs exclude it (!**/test_*.py) and it is owned by unit-test-writer",
        ),
        (
            PYTHON_ENGINEER,
            "fuzz/x.py",
            "its globs exclude it (!**/fuzz/**) and it is owned by fuzzing-tests-writer",
        ),
        (
            PYTHON_ENGINEER,
            "src/formal_model/m.py",
            "its globs exclude it (!**/formal_model/**) and it is owned by formal-model-writer",
        ),
        (PYTHON_ENGINEER, "pkg/x.go", "it is owned by software-engineer-go"),
        (
            GO_ENGINEER,
            "pkg/x_test.go",
            "its globs exclude it (!**/*_test.go) and it is owned by unit-test-writer",
        ),
        (
            GO_ENGINEER,
            "pkg/x_fuzz_test.go",
            "its globs exclude it (!**/*_test.go) and it is owned by fuzzing-tests-writer",
        ),
        (
            GO_ENGINEER,
            "pkg/x_integration_test.go",
            "its globs exclude it (!**/*_test.go) and it is owned by unit-test-writer",
        ),
        (
            GO_ENGINEER,
            "tests/integration/x_integration_test.go",
            "its globs exclude it (!**/*_test.go)",
        ),
        (
            UNIT_TEST_WRITER,
            "tests/integration/x_integration_test.go",
            "its globs exclude it (!**/tests/integration/**)",
        ),
        (
            GO_ENGINEER,
            "observability/dashboards/main.go",
            (
                "its globs exclude it (!observability/dashboards/**) and it is owned by "
                "observability-engineer"
            ),
        ),
        (
            FRONTEND_ENGINEER,
            "src/app.fuzz.ts",
            "its globs exclude it (!**/*.fuzz.ts) and it is owned by fuzzing-tests-writer",
        ),
        (
            UNIT_TEST_WRITER,
            "pkg/x_fuzz_test.go",
            "its globs exclude it (!**/*_fuzz_test.go) and it is owned by fuzzing-tests-writer",
        ),
        (
            UNIT_TEST_WRITER,
            "tests/integration/test_a.py",
            (
                "its globs exclude it (!**/tests/integration/**) and it is owned by "
                "integration-tests-writer-python"
            ),
        ),
        (UNIT_TEST_WRITER, "pkg/x.go", "it is owned by software-engineer-go"),
        (UNIT_TEST_WRITER, "src/app.ts", "it is owned by software-engineer-frontend"),
    ],
)
def test_decide_shipped_roles_deny_paths_of_another_owner(
    tmp_path: Path,
    agent: str,
    relative: str,
    cause: str,
) -> None:
    root = _repo(tmp_path / "proj")
    target = str(root / relative)

    reason = guard.decide(_payload(agent, target), SHIPPED_AGENTS_DIR)

    assert reason is not None
    assert reason.startswith(f"{agent} does not own {target}: {cause}. ")


@pytest.mark.parametrize(
    ("agent", "relative"),
    [
        (PYTHON_ENGINEER, "pkg/x.go"),
        (GO_ENGINEER, "observability/dashboards/main.go"),
        (UNIT_TEST_WRITER, "src/app.ts"),
    ],
)
def test_decide_deny_message_does_not_blame_test_writers_for_production_paths(
    tmp_path: Path,
    agent: str,
    relative: str,
) -> None:
    root = _repo(tmp_path / "proj")

    reason = guard.decide(_payload(agent, str(root / relative)), SHIPPED_AGENTS_DIR)

    assert reason is not None
    assert "test writers" not in reason
    assert "Test files" not in reason


@pytest.mark.parametrize(
    ("agent", "relative"),
    [
        (PYTHON_ENGINEER, "docs/README.md"),
        (GO_ENGINEER, "Makefile"),
        (FRONTEND_ENGINEER, "package.json"),
        (UNIT_TEST_WRITER, "docs/README.md"),
    ],
)
def test_decide_path_nobody_claims_stays_editable(
    tmp_path: Path,
    agent: str,
    relative: str,
) -> None:
    root = _repo(tmp_path / "proj")

    assert guard.decide(_payload(agent, str(root / relative)), SHIPPED_AGENTS_DIR) is None


def _decide_with_definitions(
    tmp_path: Path,
    definitions: Mapping[str, str | None],
    agent: str,
    relative: str,
) -> str | None:
    agents = tmp_path / "agents"
    for name, globs in definitions.items():
        _write_agent(agents, name, _agent_md(name, globs))
    root = _repo(tmp_path / "proj")
    return guard.decide(_payload(agent, str(root / relative)), agents)


@pytest.mark.parametrize(
    "globs",
    [None, "", "[]", "[**/*.go]", "['**/*.go']", '["**/*.go", ""]', "[1]"],
)
def test_decide_agent_without_usable_globs_is_allowed_on_a_claimed_path(
    tmp_path: Path, globs: str | None
) -> None:
    definitions = {"resolver": globs, "owner": '["**/*.go"]'}

    assert _decide_with_definitions(tmp_path, definitions, "resolver", "pkg/x.go") is None


def test_decide_unknown_agent_is_allowed_on_a_claimed_path(tmp_path: Path) -> None:
    definitions = {"owner": '["**/*.go"]'}

    assert _decide_with_definitions(tmp_path, definitions, "ghost", "pkg/x.go") is None


def test_decide_co_claimed_path_is_allowed_to_each_claimant(tmp_path: Path) -> None:
    definitions = {"first": '["**/*.py"]', "second": '["**/*.py"]'}

    assert _decide_with_definitions(tmp_path, definitions, "first", "src/a.py") is None
    assert _decide_with_definitions(tmp_path / "again", definitions, "second", "src/a.py") is None


def test_decide_other_agents_own_exclusion_releases_the_path(tmp_path: Path) -> None:
    definitions = {"editor": '["**/*.go"]', "other": '["**/*.py", "!**/gen/**"]'}

    released = _decide_with_definitions(tmp_path, definitions, "editor", "gen/x.py")
    claimed = _decide_with_definitions(tmp_path / "again", definitions, "editor", "src/x.py")

    assert released is None
    assert claimed is not None
    assert "it is owned by other" in claimed


def test_decide_several_owners_are_listed_sorted_by_name(tmp_path: Path) -> None:
    agents = tmp_path / "agents"
    _write_agent(agents, "a_file", _agent_md("zeta", '["**/*.py"]'))
    _write_agent(agents, "b_file", _agent_md("alpha", '["**/*.py"]'))
    _write_agent(agents, "c_file", _agent_md("editor", '["**/*.go"]'))
    root = _repo(tmp_path / "proj")

    reason = guard.decide(_payload("editor", str(root / "x.py")), agents)

    assert reason is not None
    assert "it is owned by alpha, zeta." in reason


def test_decide_own_exclusion_without_another_owner_names_no_owner(tmp_path: Path) -> None:
    definitions = {"editor": '["**/*.py", "!**/gen/**"]', "other": '["**/*.rs"]'}

    reason = _decide_with_definitions(tmp_path, definitions, "editor", "gen/x.py")

    assert reason is not None
    assert "its globs exclude it (!**/gen/**)." in reason
    assert "owned by" not in reason


def test_decide_exclusion_only_agent_may_edit_unclaimed_but_not_owned_paths(
    tmp_path: Path,
) -> None:
    definitions = {"editor": '["!**/tests/**"]', "other": '["**/*.py"]'}

    unclaimed = _decide_with_definitions(tmp_path, definitions, "editor", "docs/a.md")
    owned = _decide_with_definitions(tmp_path / "again", definitions, "editor", "src/a.py")
    excluded = _decide_with_definitions(tmp_path / "third", definitions, "editor", "tests/a.md")

    assert unclaimed is None
    assert owned is not None
    assert "it is owned by other" in owned
    assert excluded is not None
    assert "(!**/tests/**)" in excluded


def test_decide_brace_set_in_a_definition_claims_every_alternative(tmp_path: Path) -> None:
    definitions = {"editor": '["**/*.go"]', "fuzzer": '["**/*.fuzz.{js,ts}"]'}

    js = _decide_with_definitions(tmp_path, definitions, "editor", "src/a.fuzz.js")
    ts = _decide_with_definitions(tmp_path / "again", definitions, "editor", "src/a.fuzz.ts")
    tsx = _decide_with_definitions(tmp_path / "third", definitions, "editor", "src/a.fuzz.tsx")

    assert js is not None
    assert ts is not None
    assert tsx is None


@pytest.mark.parametrize(
    "data",
    [
        {"tool_input": {"file_path": "/r/tests/test_a.py"}},
        {"agent_type": "", "tool_input": {"file_path": "/r/tests/test_a.py"}},
        {"agent_type": None, "tool_input": {"file_path": "/r/tests/test_a.py"}},
        {"agent_type": 7, "tool_input": {"file_path": "/r/tests/test_a.py"}},
        {"agent_type": ["software-engineer-python"], "tool_input": {"file_path": "/r/t.py"}},
        {"agent_type": PYTHON_ENGINEER},
        {"agent_type": PYTHON_ENGINEER, "tool_input": None},
        {"agent_type": PYTHON_ENGINEER, "tool_input": "/r/tests/test_a.py"},
        {"agent_type": PYTHON_ENGINEER, "tool_input": ["/r/tests/test_a.py"]},
        {"agent_type": PYTHON_ENGINEER, "tool_input": {}},
        {"agent_type": PYTHON_ENGINEER, "tool_input": {"file_path": ""}},
        {"agent_type": PYTHON_ENGINEER, "tool_input": {"content": "x"}},
    ],
)
def test_decide_unusable_input_is_allowed(data: dict[str, object]) -> None:
    assert guard.decide(data, SHIPPED_AGENTS_DIR) is None


def test_decide_unknown_agent_is_allowed(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")

    data = _payload("software-engineer-cobol", str(root / "tests" / "test_a.py"))

    assert guard.decide(data, SHIPPED_AGENTS_DIR) is None


def test_decide_missing_agents_dir_is_allowed(tmp_path: Path) -> None:
    root = _repo(tmp_path / "proj")

    data = _payload(PYTHON_ENGINEER, str(root / "tests" / "test_a.py"))

    assert guard.decide(data, tmp_path / "no-agents") is None


def test_decide_positive_glob_alone_never_denies(tmp_path: Path) -> None:
    agents = tmp_path / "agents"
    _write_agent(agents, "writer", _agent_md("writer", '["**/tests/**"]'))
    root = _repo(tmp_path / "proj")

    assert guard.decide(_payload("writer", str(root / "src" / "a.py")), agents) is None


def test_decide_repository_under_tests_directory(tmp_path: Path) -> None:
    root = _repo(tmp_path / "tests" / "proj")

    allowed = guard.decide(
        _payload(PYTHON_ENGINEER, str(root / "src" / "main.py")), SHIPPED_AGENTS_DIR
    )
    denied = guard.decide(
        _payload(PYTHON_ENGINEER, str(root / "tests" / "test_a.py")),
        SHIPPED_AGENTS_DIR,
    )

    assert allowed is None
    assert denied is not None


def test_decide_worktree_under_e2e_directory(tmp_path: Path) -> None:
    worktree = tmp_path / "e2e" / "proj" / "feature_x"
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/feature_x\n")

    allowed = guard.decide(
        _payload(FRONTEND_ENGINEER, str(worktree / "src" / "app.ts")),
        SHIPPED_AGENTS_DIR,
    )
    denied = guard.decide(
        _payload(FRONTEND_ENGINEER, str(worktree / "src" / "a.spec.ts")),
        SHIPPED_AGENTS_DIR,
    )

    assert allowed is None
    assert denied is not None


def test_decide_repository_under_testdata_directory(tmp_path: Path) -> None:
    root = _repo(tmp_path / "testdata" / "repo")

    allowed = guard.decide(_payload(GO_ENGINEER, str(root / "pkg" / "x.go")), SHIPPED_AGENTS_DIR)
    denied = guard.decide(
        _payload(GO_ENGINEER, str(root / "pkg" / "x_test.go")), SHIPPED_AGENTS_DIR
    )

    assert allowed is None
    assert denied is not None


def test_decide_without_repository_matches_relative_to_cwd(tmp_path: Path) -> None:
    cwd = tmp_path / "test" / "proj"

    allowed = guard.decide(
        _payload(PYTHON_ENGINEER, str(cwd / "lib" / "a.py"), cwd=str(cwd)),
        SHIPPED_AGENTS_DIR,
    )
    denied = guard.decide(
        _payload(PYTHON_ENGINEER, str(cwd / "tests" / "test_a.py"), cwd=str(cwd)),
        SHIPPED_AGENTS_DIR,
    )

    assert allowed is None
    assert denied is not None


@pytest.mark.parametrize("cwd", [None, "", 42, "relative"])
def test_decide_without_repository_or_cwd_matches_absolute_path(
    tmp_path: Path, cwd: object
) -> None:
    target = str(tmp_path / "x" / "tests" / "test_a.py")

    reason = guard.decide(_payload(PYTHON_ENGINEER, target, cwd=cwd), SHIPPED_AGENTS_DIR)

    assert reason is not None
    assert target in reason


def _run_main(monkeypatch: pytest.MonkeyPatch, stdin: str, agents_dir: Path) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    monkeypatch.setattr(guard, "AGENTS_DIR", agents_dir)
    return guard.main()


def test_main_deny_emits_pre_tool_use_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repo(tmp_path / "proj")
    target = str(root / "pkg" / "x_test.go")
    stdin = json.dumps({"tool_name": "Write", **_payload(GO_ENGINEER, target)})

    exit_code = _run_main(monkeypatch, stdin, SHIPPED_AGENTS_DIR)

    output = json.loads(capsys.readouterr().out)
    decision = output["hookSpecificOutput"]
    assert exit_code == 0
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert target in decision["permissionDecisionReason"]


@pytest.mark.parametrize(
    "stdin",
    [
        "",
        "   \n",
        "{not json",
        "[1, 2]",
        "null",
        json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/r/tests/test_a.py"}}),
    ],
)
def test_main_allow_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin: str,
) -> None:
    assert _run_main(monkeypatch, stdin, SHIPPED_AGENTS_DIR) == 0
    assert capsys.readouterr().out == ""


def test_main_engineer_editing_production_file_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repo(tmp_path / "proj")
    stdin = json.dumps({"tool_name": "Edit", **_payload(GO_ENGINEER, str(root / "pkg" / "x.go"))})

    assert _run_main(monkeypatch, stdin, SHIPPED_AGENTS_DIR) == 0
    assert capsys.readouterr().out == ""
