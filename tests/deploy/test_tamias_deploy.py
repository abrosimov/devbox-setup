from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from jinja2 import Environment, StrictUndefined

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parents[2]
TASKS_DIR = ROOT / "roles/devbox/tasks/darwin"
INSTALL = TASKS_DIR / "install_tamias.yml"
CONTRACT = TASKS_DIR / "go_module_proxy_contract.yml"
CONFIGURE = TASKS_DIR / "configure_go_module_proxy.yml"
VERIFY = TASKS_DIR / "verify_go_module_proxy.yml"
MAIN_DARWIN = ROOT / "roles/devbox/tasks/main_darwin.yml"
PACKAGES = ROOT / "roles/devbox/defaults/main/packages.yml"
DEFAULTS_DIR = ROOT / "roles/devbox/defaults/main"
PROFILES_DIR = ROOT / "profiles"
ROLE_TASKS_DIR = ROOT / "roles/devbox/tasks"
SWITCH = "devbox_tamias_enabled"

ASSET = "tamias-darwin-arm64"
AUTH_MARKER = "AUTH-STATUS-SECRET-MARKER"
BLOCK_KEYS = ("block", "rescue", "always")

Doc = dict


def _load(path: Path) -> list[Doc]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    return loaded


def _flatten(tasks: list[Doc]) -> Iterator[Doc]:
    for task in tasks:
        yield task
        for key in BLOCK_KEYS:
            if key in task:
                yield from _flatten(task[key])


def _module(task: Doc) -> str | None:
    return next((key for key in task if key.startswith("ansible.builtin.")), None)


def _defaults() -> Doc:
    return yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))


def _packages() -> Doc:
    return copy.deepcopy(_defaults()["devbox_packages"])


def _proxy() -> Doc:
    return copy.deepcopy(_defaults()["devbox_go_module_proxy"])


def _role_defaults() -> Doc:
    merged: Doc = {}
    for path in sorted(DEFAULTS_DIR.glob("*.yml")):
        merged.update(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    return merged


def _profile(name: str) -> Doc:
    return yaml.safe_load((PROFILES_DIR / f"{name}.yml").read_text(encoding="utf-8")) or {}


def _profile_names() -> list[str]:
    return sorted(path.stem for path in PROFILES_DIR.glob("*.yml"))


def _resolved_switch(profile: str | None = None) -> bool:
    variables = _role_defaults()
    if profile is not None:
        variables.update(_profile(profile))
    rendered = _render_env(Path("/nonexistent")).from_string(
        variables["devbox_packages"]["tamias"]["enabled"]
    )
    return rendered.render(variables) == "True"


TAG = f"v{_packages()['tamias']['version']}"


def _find(tasks: list[Doc], needle: str) -> Doc:
    return next(task for task in _flatten(tasks) if needle in str(task.get("name", "")))


def _argv_task(tasks: list[Doc], *words: str) -> Doc:
    for task in _flatten(tasks):
        argv = task.get("ansible.builtin.command", {}).get("argv", [])
        if all(word in argv for word in words):
            return task
    message = f"no command task with argv containing {words}"
    raise AssertionError(message)


class TestPackageDeclaration:
    def test_exact_key_set(self) -> None:
        assert set(_packages()["tamias"]) == {
            "enabled",
            "repository",
            "version",
            "assets",
            "install_path",
        }

    def test_declaration_is_well_formed(self) -> None:
        tamias = _packages()["tamias"]
        assert tamias["enabled"] == "{{ devbox_tamias_enabled | bool }}"
        assert tamias["repository"] == "abrosimov/tamias"
        assert tamias["version"] == "0.2.2"
        assert tamias["assets"] == {"arm64": ASSET}
        assert tamias["install_path"] == "~/.local/bin/tamias"

    def test_declaration_yields_a_valid_contract(self, tmp_path: Path) -> None:
        assert _contract_holds(tmp_path, _proxy(), _packages())

    def test_tamias_enabled_is_the_only_switch(self) -> None:
        assert [key for key in _proxy() if "enabled" in key.lower()] == []
        assert [key for key in _defaults() if "enabled" in key.lower()] == []
        assert [key for key in _packages()["tamias"] if "enabled" in key.lower()] == ["enabled"]

    def test_profile_variable_is_the_only_other_declaration_of_the_switch(self) -> None:
        declared = [
            key for key in _role_defaults() if "tamias" in key.lower() and "enabled" in key.lower()
        ]
        assert declared == [SWITCH]
        for name in _profile_names():
            assert [
                key for key in _profile(name) if "tamias" in key.lower() and key != SWITCH
            ] == []

    def test_tasks_read_the_package_switch_not_the_profile_variable(self) -> None:
        offenders: list[str] = []
        for path in sorted(ROLE_TASKS_DIR.rglob("*.yml")):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                continue
            for task in _flatten(loaded):
                conditions = [task.get("when", [])]
                conditions.append(task.get("ansible.builtin.assert", {}).get("that", []))
                if SWITCH in json.dumps(conditions):
                    offenders.append(f"{path.relative_to(ROOT)}: {task.get('name')}")
        assert offenders == []

    def test_switch_default_is_a_literal_false(self) -> None:
        assert _role_defaults()[SWITCH] is False

    def test_personal_profile_sets_the_switch_to_a_literal_true(self) -> None:
        assert _profile("personal")[SWITCH] is True

    def test_work_profile_does_not_set_the_switch(self) -> None:
        assert SWITCH not in _profile("work")

    def test_switch_resolves_true_for_personal(self) -> None:
        assert _resolved_switch("personal") is True

    def test_switch_resolves_false_for_work(self) -> None:
        assert _resolved_switch("work") is False

    def test_switch_resolves_false_for_bare_defaults(self) -> None:
        assert _resolved_switch() is False

    @pytest.mark.parametrize("name", _profile_names())
    def test_only_the_personal_profile_enables_the_client(self, name: str) -> None:
        assert _resolved_switch(name) is (name == "personal")

    def test_switch_follows_the_profile_variable_not_a_constant(self) -> None:
        variables = _role_defaults()
        template = variables["devbox_packages"]["tamias"]["enabled"]
        environment = _render_env(Path("/nonexistent"))
        for value, expected in ((True, "True"), (False, "False")):
            assert (
                environment.from_string(template).render({**variables, SWITCH: value}) == expected
            )

    def test_no_checksum_like_field_anywhere(self) -> None:
        def keys(node: object) -> Iterator[str]:
            if isinstance(node, dict):
                for key, value in node.items():
                    yield str(key)
                    yield from keys(value)
            elif isinstance(node, list):
                for item in node:
                    yield from keys(item)

        forbidden = ("sha", "checksum", "digest", "sum")
        offenders = [
            key for key in keys(_packages()["tamias"]) if any(w in key.lower() for w in forbidden)
        ]
        assert offenders == []


class TestInstallHasNoFallback:
    def test_only_expected_modules_are_used(self) -> None:
        modules = {_module(task) for task in _flatten(_load(INSTALL))} - {None}
        assert modules <= {
            "ansible.builtin.set_fact",
            "ansible.builtin.assert",
            "ansible.builtin.command",
            "ansible.builtin.file",
            "ansible.builtin.stat",
            "ansible.builtin.tempfile",
            "ansible.builtin.copy",
        }

    @pytest.mark.parametrize(
        "pattern",
        [r"go\s+(install|build)", r"brew", r"get_url", r"\buri\b", r"curl", r"wget", r"sha256sums"],
    )
    def test_banned_fallback_is_absent(self, pattern: str) -> None:
        bodies = []
        for task in _flatten(_load(INSTALL)):
            body = {
                key: value
                for key, value in task.items()
                if key not in ("name", "environment", *BLOCK_KEYS)
            }
            bodies.append(json.dumps(body))
        assert re.search(pattern, "\n".join(bodies), re.IGNORECASE) is None

    def test_verify_asset_precedes_copy_in_the_same_block(self) -> None:
        staging = next(
            task
            for task in _flatten(_load(INSTALL))
            if any(_module(inner) == "ansible.builtin.copy" for inner in task.get("block", []))
        )
        inner = staging["block"]
        copy_index = next(i for i, t in enumerate(inner) if _module(t) == "ansible.builtin.copy")
        verify_index = next(
            i
            for i, t in enumerate(inner)
            if "verify-asset" in t.get("ansible.builtin.command", {}).get("argv", [])
        )
        download_index = next(
            i
            for i, t in enumerate(inner)
            if "download" in t.get("ansible.builtin.command", {}).get("argv", [])
        )
        assert download_index < verify_index < copy_index
        verify = inner[verify_index]
        assert "failed_when" not in verify
        assert "ignore_errors" not in verify
        assert inner[copy_index]["ansible.builtin.copy"]["mode"] == "0755"

    def test_staging_cleanup_is_in_always(self) -> None:
        staging = next(task for task in _flatten(_load(INSTALL)) if "always" in task)
        cleanup = staging["always"][0]["ansible.builtin.file"]
        assert cleanup["state"] == "absent"
        assert "devbox_tamias_staging.path" in cleanup["path"]
        assert "rescue" not in staging

    def test_auth_status_is_no_log(self) -> None:
        assert _argv_task(_load(INSTALL), "auth", "status")["no_log"] is True


class FakeGh:
    SCRIPT = """#!{python}
import json, pathlib, sys
cfg = json.loads(pathlib.Path({cfg!r}).read_text())
args = sys.argv[1:]
with pathlib.Path({log!r}).open('a') as stream:
    stream.write(json.dumps(args) + '\\n')
if args[:1] == ['--version']:
    print('gh version fake')
    sys.exit(0)
if args[:2] == ['auth', 'status']:
    print(cfg['auth_marker'])
    print(cfg['auth_marker'], file=sys.stderr)
    sys.exit(cfg['auth_rc'])
if args[:2] == ['release', 'view']:
    if cfg['view_rc']:
        print('release not found', file=sys.stderr)
        sys.exit(cfg['view_rc'])
    print(json.dumps(cfg['release']))
    sys.exit(0)
if args[:2] == ['release', 'download']:
    pattern = args[args.index('--pattern') + 1]
    target = pathlib.Path(args[args.index('--dir') + 1]) / pattern
    target.write_bytes(bytes.fromhex(cfg['asset_hex']))
    sys.exit(0)
if args[:2] == ['release', 'verify-asset']:
    installed = args[3] == cfg['install_path']
    sys.exit(cfg['verify_rc_installed'] if installed else cfg['verify_rc_staged'])
sys.exit(97)
"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / "home"
        self.tmpdir = root / "tmp"
        self.install_path = self.home / ".local/bin/tamias"
        self.log = root / "gh-calls.jsonl"
        self.cfg = root / "gh-config.json"
        self.executable = root / "fake-gh"
        self.home.mkdir()
        self.tmpdir.mkdir()
        self.executable.write_text(
            self.SCRIPT.format(python=sys.executable, cfg=str(self.cfg), log=str(self.log))
        )
        self.executable.chmod(0o700)
        self.asset_bytes = b"tamias release bytes\n"
        self.configure()

    @staticmethod
    def digest(content: bytes) -> str:
        return "sha256:" + hashlib.sha256(content).hexdigest()

    def release(self, **overrides: object) -> Doc:
        release: Doc = {
            "tagName": TAG,
            "isDraft": False,
            "isImmutable": True,
            "assets": [{"name": ASSET, "digest": self.digest(self.asset_bytes)}],
        }
        release.update(overrides)
        return release

    def configure(self, **overrides: object) -> None:
        config: Doc = {
            "auth_marker": AUTH_MARKER,
            "auth_rc": 0,
            "view_rc": 0,
            "release": self.release(),
            "asset_hex": self.asset_bytes.hex(),
            "verify_rc_installed": 0,
            "verify_rc_staged": 0,
            "install_path": str(self.install_path),
        }
        config.update(overrides)
        self.cfg.write_text(json.dumps(config))

    def preinstall(self, content: bytes, mode: int = 0o755) -> None:
        self.install_path.parent.mkdir(parents=True, exist_ok=True)
        self.install_path.write_bytes(content)
        self.install_path.chmod(mode)

    def calls(self) -> list[list[str]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def calls_of(self, *prefix: str) -> list[list[str]]:
        return [call for call in self.calls() if call[: len(prefix)] == list(prefix)]

    def clear_calls(self) -> None:
        self.log.unlink(missing_ok=True)

    def leftovers(self) -> list[str]:
        return [p.name for p in self.tmpdir.glob("devbox-tamias.*")]


def _ansible() -> str:
    sibling = Path(sys.executable).parent / "ansible-playbook"
    return str(sibling) if sibling.exists() else "ansible-playbook"


def _run_playbook(
    root: Path,
    play: Doc,
    *,
    env: dict[str, str],
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    playbook = root / "playbook.yml"
    playbook.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", **play}]))
    environment = os.environ.copy()
    environment.update(
        {
            "ANSIBLE_LOCAL_TEMP": str(root / "ansible-local"),
            "ANSIBLE_REMOTE_TEMP": str(root / "ansible-remote"),
            "ANSIBLE_HOME": str(root / "ansible-home"),
            "ANSIBLE_NOCOLOR": "1",
            **env,
        }
    )
    return subprocess.run(
        [_ansible(), "-i", "localhost,", str(playbook), *(["--check"] if check else [])],
        capture_output=True,
        text=True,
        timeout=180,
        env=environment,
        cwd=root,
        check=False,
    )


def _changed(result: subprocess.CompletedProcess[str]) -> int:
    match = re.search(r"changed=(\d+)", result.stdout)
    assert match, result.stdout + result.stderr
    return int(match.group(1))


@pytest.mark.integration
class TestInstallAdmission:
    @pytest.fixture
    def gh(self, tmp_path: Path) -> FakeGh:
        return FakeGh(tmp_path)

    def run(
        self,
        gh: FakeGh,
        *,
        arch: str = "arm64",
        seam: str | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        packages = _packages()
        packages["tamias"]["enabled"] = True
        packages["tamias"]["install_path"] = str(gh.install_path)
        play = {
            "gather_facts": False,
            "vars": {
                "ansible_python_interpreter": sys.executable,
                "ansible_facts": {
                    "architecture": arch,
                    "env": {"HOME": str(gh.home), "PATH": os.environ["PATH"]},
                },
                "devbox_packages": packages,
                "devbox_tamias_gh_bin": seam if seam is not None else str(gh.executable),
            },
            "tasks": [{"ansible.builtin.include_tasks": str(INSTALL)}],
        }
        result = _run_playbook(
            gh.root,
            play,
            env={"HOME": str(gh.home), "TMPDIR": str(gh.tmpdir)},
            check=check,
        )
        assert AUTH_MARKER not in result.stdout + result.stderr
        return result

    def assert_rejected_untouched(
        self, gh: FakeGh, result: subprocess.CompletedProcess[str]
    ) -> None:
        assert result.returncode != 0, result.stdout
        assert gh.calls_of("release", "download") == []
        assert gh.install_path.read_bytes() == b"previous admitted binary"

    @pytest.mark.parametrize(
        "release_overrides",
        [
            {"isImmutable": False},
            {"isDraft": True},
            {"tagName": "v0.2.3"},
            {"tagName": f"{TAG}0"},
            {"assets": []},
            {"assets": [{"name": "tamias-darwin-amd64", "digest": "sha256:" + "a" * 64}]},
            {"assets": [{"name": ASSET}]},
            {"assets": [{"name": ASSET, "digest": "sha256:" + "A" * 64}]},
            {"assets": [{"name": ASSET, "digest": "md5:" + "a" * 32}]},
        ],
        ids=[
            "mutable",
            "draft",
            "tag-mismatch",
            "tag-prefix-lookalike",
            "no-assets",
            "other-architecture-only",
            "missing-digest",
            "uppercase-digest",
            "wrong-digest-algorithm",
        ],
    )
    def test_inadmissible_release_is_rejected(self, gh: FakeGh, release_overrides: Doc) -> None:
        gh.preinstall(b"previous admitted binary")
        gh.configure(release=gh.release(**release_overrides))
        self.assert_rejected_untouched(gh, self.run(gh))

    def test_release_not_found_is_rejected(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        gh.configure(view_rc=1)
        self.assert_rejected_untouched(gh, self.run(gh))

    def test_ambiguous_asset_is_rejected(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        digest = gh.digest(gh.asset_bytes)
        gh.configure(
            release=gh.release(
                assets=[{"name": ASSET, "digest": digest}, {"name": ASSET, "digest": digest}]
            )
        )
        self.assert_rejected_untouched(gh, self.run(gh))

    def test_unmapped_architecture_fails_before_any_gh_call(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        result = self.run(gh, arch="x86_64")
        assert result.returncode != 0
        assert gh.calls() == []
        assert gh.install_path.read_bytes() == b"previous admitted binary"

    def test_missing_gh_fails(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        result = self.run(gh, seam=str(gh.root / "no-such-gh"))
        assert result.returncode != 0
        assert gh.calls() == []
        assert gh.install_path.read_bytes() == b"previous admitted binary"

    def test_auth_failure_fails_and_hides_status_output(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        gh.configure(auth_rc=1)
        result = self.run(gh)
        assert result.returncode != 0
        assert gh.calls_of("release", "view") == []
        assert gh.calls_of("release", "download") == []
        assert gh.install_path.read_bytes() == b"previous admitted binary"

    def test_verify_asset_failure_leaves_previous_binary_and_no_staging(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        gh.configure(verify_rc_staged=1)
        result = self.run(gh)
        assert result.returncode != 0
        assert len(gh.calls_of("release", "download")) == 1
        assert gh.calls_of("release", "verify-asset")
        assert gh.install_path.read_bytes() == b"previous admitted binary"
        assert gh.leftovers() == []

    def test_digest_mismatch_installs_nothing_and_cleans_staging(self, gh: FakeGh) -> None:
        gh.configure(release=gh.release(assets=[{"name": ASSET, "digest": gh.digest(b"other")}]))
        result = self.run(gh)
        assert result.returncode != 0
        assert len(gh.calls_of("release", "verify-asset")) == 1
        assert not gh.install_path.exists()
        assert gh.leftovers() == []

    def test_digest_mismatch_keeps_previous_binary(self, gh: FakeGh) -> None:
        gh.preinstall(b"previous admitted binary")
        gh.configure(release=gh.release(assets=[{"name": ASSET, "digest": gh.digest(b"other")}]))
        result = self.run(gh)
        assert result.returncode != 0
        assert gh.install_path.read_bytes() == b"previous admitted binary"

    def test_happy_path_installs_exact_bytes_verified_at_staged_path(self, gh: FakeGh) -> None:
        result = self.run(gh)
        assert result.returncode == 0, result.stdout + result.stderr
        assert gh.install_path.read_bytes() == gh.asset_bytes
        assert stat.S_IMODE(gh.install_path.stat().st_mode) == 0o755
        [download] = gh.calls_of("release", "download")
        assert download[download.index("--pattern") + 1] == ASSET
        assert download[download.index("--repo") + 1] == "abrosimov/tamias"
        staging = download[download.index("--dir") + 1]
        assert staging.startswith(str(gh.tmpdir))
        [verify] = gh.calls_of("release", "verify-asset")
        assert verify[2:4] == [TAG, f"{staging}/{ASSET}"]
        assert verify[verify.index("--repo") + 1] == "abrosimov/tamias"
        assert gh.calls().index(download) < gh.calls().index(verify)
        assert gh.leftovers() == []

    def test_second_run_is_idle_and_downloads_nothing(self, gh: FakeGh) -> None:
        assert self.run(gh).returncode == 0
        gh.clear_calls()
        result = self.run(gh)
        assert result.returncode == 0, result.stdout + result.stderr
        assert _changed(result) == 0
        assert gh.calls_of("release", "download") == []
        [verify] = gh.calls_of("release", "verify-asset")
        assert verify[3] == str(gh.install_path)

    def test_matching_bytes_with_failing_attestation_are_reinstalled(self, gh: FakeGh) -> None:
        gh.preinstall(gh.asset_bytes)
        gh.configure(verify_rc_installed=1)
        result = self.run(gh)
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(gh.calls_of("release", "download")) == 1
        assert gh.install_path.read_bytes() == gh.asset_bytes

    def test_admitted_binary_regains_executable_mode_without_download(self, gh: FakeGh) -> None:
        gh.preinstall(gh.asset_bytes, mode=0o644)
        result = self.run(gh)
        assert result.returncode == 0, result.stdout + result.stderr
        assert stat.S_IMODE(gh.install_path.stat().st_mode) == 0o755
        assert gh.calls_of("release", "download") == []

    def test_check_mode_downloads_and_installs_nothing(self, gh: FakeGh) -> None:
        result = self.run(gh, check=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert gh.calls_of("release", "download") == []
        assert not gh.install_path.exists()


def _render_env(home: Path) -> Environment:
    environment = Environment(undefined=StrictUndefined, autoescape=True)
    environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
    environment.filters["expanduser"] = lambda value: str(value).replace("~", str(home), 1)
    environment.filters["bool"] = lambda value: str(value).lower() in {"1", "true", "yes", "on"}
    return environment


def _derive_contract(home: Path, proxy: Doc, packages: Doc) -> dict[str, str]:
    templates = _load(CONTRACT)[0]["ansible.builtin.set_fact"]["devbox_go_module_proxy_desired"]
    environment = _render_env(home)
    context = {"devbox_go_module_proxy": proxy, "devbox_packages": packages}
    return {key: environment.from_string(value).render(context) for key, value in templates.items()}


def _contract_holds(home: Path, proxy: Doc, packages: Doc) -> bool:
    desired = _derive_contract(home, proxy, packages)
    conditions = _load(CONTRACT)[1]["ansible.builtin.assert"]["that"]
    environment = _render_env(home)
    context = {
        "devbox_go_module_proxy": proxy,
        "devbox_packages": packages,
        "devbox_go_module_proxy_desired": desired,
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return all(
            environment.from_string("{{ " + str(condition) + " }}").render(context) == "True"
            for condition in conditions
        )


class TestGoProxyContract:
    def test_contract_values_are_exact(self, tmp_path: Path) -> None:
        assert _derive_contract(tmp_path, _proxy(), _packages()) == {
            "GOAUTH": f"{tmp_path}/.local/bin/tamias goauth",
            "GOPROXY": "https://go.abrosimov.tech",
            "GONOPROXY": "none",
            "GONOSUMDB": "github.com/abrosimov/*,github.com/abrosimov-tech/*",
            "GOSUMDB": "sum.golang.org",
        }

    def test_default_contract_passes_its_own_assertions(self, tmp_path: Path) -> None:
        assert _contract_holds(tmp_path, _proxy(), _packages())

    @pytest.mark.parametrize(
        "goproxy",
        [
            "https://go.abrosimov.tech,direct",
            "https://go.abrosimov.tech|direct",
            "https://go.abrosimov.tech,https://proxy.golang.org",
            "https://proxy.golang.org,https://go.abrosimov.tech",
            "direct",
            "off",
            "http://go.abrosimov.tech",
            "https://go.abrosimov.tech direct",
            "",
        ],
    )
    def test_proxy_with_fallback_is_rejected(self, tmp_path: Path, goproxy: str) -> None:
        proxy = _proxy()
        proxy["goproxy"] = goproxy
        assert not _contract_holds(tmp_path, proxy, _packages())

    @pytest.mark.parametrize("gonoproxy", ["", "github.com/abrosimov/*", "none,other"])
    def test_proxy_exemptions_are_rejected(self, tmp_path: Path, gonoproxy: str) -> None:
        proxy = _proxy()
        proxy["gonoproxy"] = gonoproxy
        assert not _contract_holds(tmp_path, proxy, _packages())

    @pytest.mark.parametrize("enabled", [True, False])
    def test_contract_does_not_depend_on_the_switch(self, tmp_path: Path, *, enabled: bool) -> None:
        packages = _packages()
        packages["tamias"]["enabled"] = enabled
        assert _contract_holds(tmp_path, _proxy(), packages)
        assert _derive_contract(tmp_path, _proxy(), packages) == _derive_contract(
            tmp_path, _proxy(), _packages()
        )

    def test_contract_does_not_mention_the_switch(self) -> None:
        assert "enabled" not in CONTRACT.read_text(encoding="utf-8")

    @pytest.mark.parametrize("install_path", ["relative/tamias", "/path with space/tamias", ""])
    def test_unusable_helper_path_is_rejected(self, tmp_path: Path, install_path: str) -> None:
        packages = _packages()
        packages["tamias"]["install_path"] = install_path
        assert not _contract_holds(tmp_path, _proxy(), packages)


def _go_supports_goauth() -> bool:
    try:
        version = subprocess.run(
            ["go", "version"], capture_output=True, text=True, timeout=30, check=False
        ).stdout
    except FileNotFoundError:
        return False
    found = re.search(r"go(\d+)\.(\d+)", version)
    return bool(found) and (int(found.group(1)), int(found.group(2))) >= (1, 24)


GO_KEYS = ("GOAUTH", "GOPROXY", "GONOPROXY", "GONOSUMDB", "GOSUMDB")


def _go_environment(goenv: Path) -> dict[str, str]:
    environment = {k: v for k, v in os.environ.items() if k not in GO_KEYS}
    environment.update({"GOENV": str(goenv), "GOTOOLCHAIN": "local", "GOFLAGS": ""})
    return environment


def _effective(goenv: Path) -> dict[str, str]:
    output = subprocess.run(
        ["go", "env", "-json", *GO_KEYS],
        capture_output=True,
        text=True,
        timeout=60,
        env=_go_environment(goenv),
        check=True,
    ).stdout
    return json.loads(output)


def _read_goenv(path: Path) -> dict[str, str]:
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    return dict(pairs)


@pytest.mark.integration
@pytest.mark.skipif(not _go_supports_goauth(), reason="go >= 1.24 is required for GOAUTH")
class TestConfigureGoEnv:
    @pytest.fixture
    def sandbox(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        home = tmp_path / "home"
        home.mkdir()
        goenv = tmp_path / "goenv"
        goenv.write_text("GOPROXY=https://proxy.golang.org,direct\nGOFLAGS=-trimpath\n")
        return tmp_path, home, goenv

    def run(
        self,
        sandbox: tuple[Path, Path, Path],
        inherited: dict[str, str] | None = None,
        *,
        enabled: bool = True,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        root, home, goenv = sandbox
        packages = _packages()
        packages["tamias"]["enabled"] = enabled
        play = {
            "gather_facts": False,
            "vars": {
                "ansible_python_interpreter": sys.executable,
                "ansible_facts": {"env": {"HOME": str(home), "PATH": os.environ["PATH"]}},
                "devbox_packages": packages,
            },
            "tasks": [
                {
                    "ansible.builtin.include_role": {
                        "name": "devbox",
                        "tasks_from": "darwin/configure_go_module_proxy.yml",
                    }
                }
            ],
        }
        result = _run_playbook(
            root,
            play,
            env={
                "HOME": str(home),
                "GOENV": str(goenv),
                "GOTOOLCHAIN": "local",
                "GOFLAGS": "",
                "ANSIBLE_ROLES_PATH": str(ROOT / "roles"),
                "TMPDIR": str(root),
                **(inherited or {}),
            },
            check=check,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def expected(self, home: Path) -> dict[str, str]:
        return {
            "GOAUTH": f"{home}/.local/bin/tamias goauth",
            "GOPROXY": "https://go.abrosimov.tech",
            "GONOPROXY": "none",
            "GONOSUMDB": "github.com/abrosimov/*,github.com/abrosimov-tech/*",
            "GOSUMDB": "sum.golang.org",
        }

    def contract_lines(self, home: Path, *, with_gosumdb: bool = False) -> list[str]:
        values = self.expected(home)
        keys = ["GOAUTH", "GOPROXY", "GONOPROXY", "GONOSUMDB"]
        if with_gosumdb:
            keys.append("GOSUMDB")
        return [f"{key}={values[key]}" for key in keys]

    def defaults(self, root: Path) -> dict[str, str]:
        empty = root / "empty-goenv"
        empty.write_text("")
        return _effective(empty)

    def test_converges_once_and_then_reports_no_change(
        self, sandbox: tuple[Path, Path, Path]
    ) -> None:
        _, home, goenv = sandbox
        assert _changed(self.run(sandbox)) == 1
        assert _effective(goenv) == self.expected(home)
        assert _read_goenv(goenv)["GOFLAGS"] == "-trimpath"
        before = goenv.read_bytes()
        assert _changed(self.run(sandbox)) == 0
        assert goenv.read_bytes() == before

    def test_inherited_goproxy_does_not_change_the_outcome(
        self, sandbox: tuple[Path, Path, Path]
    ) -> None:
        _, home, goenv = sandbox
        inherited = {"GOPROXY": "direct", "GONOPROXY": "*", "GOSUMDB": "off"}
        assert _changed(self.run(sandbox, inherited)) == 1
        assert _effective(goenv) == self.expected(home)
        assert _changed(self.run(sandbox, inherited)) == 0

    def test_single_drifted_key_is_repaired(self, sandbox: tuple[Path, Path, Path]) -> None:
        _, home, goenv = sandbox
        self.run(sandbox)
        subprocess.run(
            ["go", "env", "-w", "GOSUMDB=off"],
            env=_go_environment(goenv),
            capture_output=True,
            timeout=60,
            check=True,
        )
        assert _effective(goenv)["GOSUMDB"] == "off"
        assert _changed(self.run(sandbox)) == 1
        assert _effective(goenv) == self.expected(home)
        assert _changed(self.run(sandbox)) == 0

    @pytest.mark.parametrize("with_gosumdb", [False, True], ids=["four-lines", "five-lines"])
    def test_disabled_removes_the_contract_and_keeps_other_keys(
        self, sandbox: tuple[Path, Path, Path], *, with_gosumdb: bool
    ) -> None:
        root, home, goenv = sandbox
        lines = [*self.contract_lines(home, with_gosumdb=with_gosumdb), "GOFLAGS=-trimpath"]
        goenv.write_text("\n".join(lines) + "\n")
        assert _changed(self.run(sandbox, enabled=False)) == 1
        assert _read_goenv(goenv) == {"GOFLAGS": "-trimpath"}
        assert _effective(goenv) == self.defaults(root)
        before = goenv.read_bytes()
        assert _changed(self.run(sandbox, enabled=False)) == 0
        assert goenv.read_bytes() == before

    def test_disabled_leaves_lines_with_foreign_values(
        self, sandbox: tuple[Path, Path, Path]
    ) -> None:
        _, home, goenv = sandbox
        goenv.write_text(
            "GOPROXY=https://corp.example\n"
            "GOAUTH=/opt/other/helper goauth\n"
            f"GONOSUMDB={self.expected(home)['GONOSUMDB']}\n"
            "GONOPROXY=none\n"
            "GOFLAGS=-trimpath\n"
        )
        assert _changed(self.run(sandbox, enabled=False)) == 1
        assert _read_goenv(goenv) == {
            "GOPROXY": "https://corp.example",
            "GOAUTH": "/opt/other/helper goauth",
            "GOFLAGS": "-trimpath",
        }

    def test_disabled_ignores_near_miss_values(self, sandbox: tuple[Path, Path, Path]) -> None:
        _, home, goenv = sandbox
        content = (
            f"GOAUTH={self.expected(home)['GOAUTH']} --extra\n"
            "GOPROXY=https://go.abrosimov.tech,direct\n"
            "GONOPROXY=none,other\n"
            "GONOSUMDB=github.com/abrosimov/*\n"
        )
        goenv.write_text(content)
        assert _changed(self.run(sandbox, enabled=False)) == 0
        assert goenv.read_text() == content

    def test_disabled_without_a_go_env_file_is_a_no_op(
        self, sandbox: tuple[Path, Path, Path]
    ) -> None:
        _, _, goenv = sandbox
        goenv.unlink()
        assert _changed(self.run(sandbox, enabled=False)) == 0
        assert not goenv.exists()

    def test_disabled_with_goenv_off_is_a_no_op(self, sandbox: tuple[Path, Path, Path]) -> None:
        _, home, goenv = sandbox
        goenv.write_text("\n".join(self.contract_lines(home)) + "\n")
        before = goenv.read_bytes()
        assert _changed(self.run(sandbox, {"GOENV": "off"}, enabled=False)) == 0
        assert goenv.read_bytes() == before

    def test_disabled_ignores_inherited_variables(self, sandbox: tuple[Path, Path, Path]) -> None:
        root, home, goenv = sandbox
        goenv.write_text("\n".join(self.contract_lines(home)) + "\nGOFLAGS=-trimpath\n")
        inherited = {
            "GOPROXY": "direct",
            "GONOPROXY": "*",
            "GOSUMDB": "off",
            "GOAUTH": "off",
            "GONOSUMDB": "*",
        }
        assert _changed(self.run(sandbox, inherited, enabled=False)) == 1
        assert _read_goenv(goenv) == {"GOFLAGS": "-trimpath"}
        assert _effective(goenv) == self.defaults(root)
        assert _changed(self.run(sandbox, inherited, enabled=False)) == 0

    def test_disabled_check_mode_changes_nothing(self, sandbox: tuple[Path, Path, Path]) -> None:
        _, home, goenv = sandbox
        goenv.write_text("\n".join(self.contract_lines(home)) + "\nGOFLAGS=-trimpath\n")
        before = goenv.read_bytes()
        self.run(sandbox, enabled=False, check=True)
        assert goenv.read_bytes() == before

    def test_enable_disable_enable_round_trip_matches_the_contract_each_time(
        self, sandbox: tuple[Path, Path, Path]
    ) -> None:
        root, home, goenv = sandbox
        default = self.defaults(root)
        for _ in range(2):
            assert _changed(self.run(sandbox, enabled=True)) == 1
            assert _effective(goenv) == self.expected(home)
            assert _changed(self.run(sandbox, enabled=True)) == 0
            assert _changed(self.run(sandbox, enabled=False)) == 1
            assert _effective(goenv) == default
            assert _read_goenv(goenv) == {"GOFLAGS": "-trimpath"}
            assert _changed(self.run(sandbox, enabled=False)) == 0


class TestVerifyEntryPoint:
    def test_credential_check_is_no_log_and_discards_output(self) -> None:
        task = _find(_load(VERIFY), "check for a usable Tamias credential")
        assert task["no_log"] is True
        assert "goauth >/dev/null 2>&1" in task["ansible.builtin.shell"]["cmd"]

    def test_downloads_are_no_log_and_pinned(self) -> None:
        task = _argv_task(_load(VERIFY), "go", "mod", "download")
        assert task["no_log"] is True
        env = task["environment"]
        assert env["GOPROXY"] == "{{ devbox_go_module_proxy_desired.GOPROXY }}"
        assert env["GOVCS"] == "*:off"
        assert env["GOPRIVATE"] == ""
        assert env["GOINSECURE"] == ""
        assert env["GONOPROXY"] == "{{ devbox_go_module_proxy_desired.GONOPROXY }}"
        assert env["GOMODCACHE"].startswith("{{ devbox_go_proxy_verify_tmp.path }}/")

    def test_download_proxy_is_the_contract_value(self, tmp_path: Path) -> None:
        assert _derive_contract(tmp_path, _proxy(), _packages())["GOPROXY"] == (
            "https://go.abrosimov.tech"
        )

    def test_throwaway_workspace_is_a_tempfile_removed_in_always(self) -> None:
        block = next(task for task in _flatten(_load(VERIFY)) if "always" in task)
        assert _module(block["block"][0]) == "ansible.builtin.tempfile"
        cleanup = block["always"][0]["ansible.builtin.file"]
        assert cleanup["state"] == "absent"
        assert "devbox_go_proxy_verify_tmp.path" in cleanup["path"]

    def test_main_darwin_does_not_include_the_verify_entry_point(self) -> None:
        assert "verify_go_module_proxy" not in MAIN_DARWIN.read_text(encoding="utf-8")

    @staticmethod
    def _main_include(name: str) -> Doc:
        return next(
            task
            for task in _flatten(_load(MAIN_DARWIN))
            if task.get("ansible.builtin.include_tasks") == name
        )

    @staticmethod
    def _conditions(task: Doc) -> list[str]:
        when = task.get("when", [])
        return [str(item) for item in (when if isinstance(when, list) else [when])]

    def test_configure_is_included_in_both_states(self) -> None:
        conditions = self._conditions(self._main_include("darwin/configure_go_module_proxy.yml"))
        assert conditions
        assert not any("tamias" in condition for condition in conditions)

    def test_install_is_gated_on_the_switch(self) -> None:
        conditions = self._conditions(self._main_include("darwin/install_tamias.yml"))
        assert any("devbox_packages.tamias.enabled" in condition for condition in conditions)

    def test_verify_refuses_to_run_when_disabled(self) -> None:
        first = _load(VERIFY)[0]
        [condition] = first["ansible.builtin.assert"]["that"]
        assert "devbox_packages.tamias.enabled" in condition

    def test_configure_blanks_the_five_inherited_variables(self) -> None:
        environment = _load(CONFIGURE)[0]["environment"]
        assert {key: environment[key] for key in environment if key != "PATH"} == {
            "GOAUTH": "",
            "GOPROXY": "",
            "GONOPROXY": "",
            "GONOSUMDB": "",
            "GOSUMDB": "",
        }


CLIENT = TASKS_DIR / "configure_tamias_client.yml"
INSTALL_CONFIGS = ROOT / "roles/devbox/tasks/install_configs.yml"

CLIENT_MARKER = "TAMIAS-CLIENT-ISSUER-SECRET-MARKER"
CLIENT_CONFIG = (
    '{"profiles": {"default": {"proxy": "https://go.example.test",'
    f' "issuer": "https://id.example.test/é", "client_id": "{CLIENT_MARKER}"}}}}'
).encode()


def _main_includes() -> list[str]:
    return [
        task["ansible.builtin.include_tasks"]
        for task in _flatten(_load(MAIN_DARWIN))
        if isinstance(task.get("ansible.builtin.include_tasks"), str)
    ]


def _include_task(name: str) -> Doc:
    return next(
        task
        for task in _flatten(_load(MAIN_DARWIN))
        if task.get("ansible.builtin.include_tasks") == name
    )


def _holds(task: Doc, **context: object) -> bool:
    conditions = task.get("when", [])
    conditions = conditions if isinstance(conditions, list) else [conditions]
    environment = _render_env(Path())
    return all(bool(environment.compile_expression(str(c))(**context)) for c in conditions)


class TestMainDarwinOrdering:
    def test_tamias_and_proxy_steps_precede_every_module_fetching_step(self) -> None:
        includes = _main_includes()
        chain = [
            "darwin/install_tamias.yml",
            "darwin/configure_tamias_client.yml",
            "darwin/configure_go_module_proxy.yml",
            "darwin/install_from_go.yml",
        ]
        assert [includes.count(name) for name in chain] == [1, 1, 1, 1]
        positions = [includes.index(name) for name in chain]
        assert positions == sorted(positions)

    @pytest.mark.parametrize(
        "later",
        [
            "darwin/install_from_uv.yml",
            "darwin/install_kubectl.yml",
            "darwin/install_tlaplus.yml",
        ],
    )
    def test_other_installers_stay_after_the_go_proxy_configuration(self, later: str) -> None:
        includes = _main_includes()
        assert includes.index("darwin/configure_go_module_proxy.yml") < includes.index(later)

    @pytest.mark.parametrize(
        "name",
        ["darwin/install_tamias.yml", "darwin/configure_tamias_client.yml"],
    )
    @pytest.mark.parametrize("dev_mode", [None, False, True], ids=["unset", "false", "true"])
    @pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
    def test_tamias_includes_run_only_outside_dev_mode_and_when_enabled(
        self, name: str, *, dev_mode: bool | None, enabled: bool
    ) -> None:
        context: Doc = {"devbox_packages": {"tamias": {"enabled": enabled}}}
        if dev_mode is not None:
            context["dev_mode"] = dev_mode
        assert _holds(_include_task(name), **context) is (enabled and not dev_mode)

    def test_tamias_package_switch_absent_means_not_run(self) -> None:
        task = _include_task("darwin/configure_tamias_client.yml")
        assert _holds(task, devbox_packages={"tamias": {}}) is False

    @pytest.mark.parametrize("dev_mode", [None, False, True], ids=["unset", "false", "true"])
    @pytest.mark.parametrize("enabled", [False, True], ids=["disabled", "enabled"])
    def test_go_proxy_configuration_ignores_the_tamias_switch_but_not_dev_mode(
        self, *, dev_mode: bool | None, enabled: bool
    ) -> None:
        context: Doc = {"devbox_packages": {"tamias": {"enabled": enabled}}}
        if dev_mode is not None:
            context["dev_mode"] = dev_mode
        task = _include_task("darwin/configure_go_module_proxy.yml")
        assert _holds(task, **context) is (not dev_mode)

    @pytest.mark.parametrize(
        "name",
        ["darwin/install_tamias.yml", "darwin/configure_tamias_client.yml"],
    )
    def test_tamias_includes_are_selectable_by_both_tags(self, name: str) -> None:
        assert {"tamias", "go-proxy"} <= set(_include_task(name)["tags"])


class TestClientConfigTaskShape:
    def test_steps_run_in_order_before_any_write(self) -> None:
        modules = [_module(task) for task in _flatten(_load(CLIENT)) if _module(task)]
        assert modules == [
            "ansible.builtin.stat",
            "ansible.builtin.assert",
            "ansible.builtin.file",
            "ansible.builtin.copy",
        ]

    def test_private_modes_and_no_diff(self) -> None:
        tasks = list(_flatten(_load(CLIENT)))
        directory = _find(tasks, "private configuration directory")["ansible.builtin.file"]
        install = _find(tasks, "install the client profiles")
        assert directory["state"] == "directory"
        assert directory["mode"] == "0700"
        assert install["ansible.builtin.copy"]["mode"] == "0600"
        assert install["diff"] is False

    def test_the_task_is_tagged_for_both_selectors(self) -> None:
        assert {"tamias", "go-proxy"} <= set(_load(CLIENT)[0]["tags"])


@pytest.mark.integration
class TestClientConfigDeploy:
    @pytest.fixture
    def env(self, tmp_path: Path) -> Doc:
        role = tmp_path / "role"
        home = tmp_path / "home"
        overlay = role / "local/tamias/config.json"
        overlay.parent.mkdir(parents=True)
        overlay.write_bytes(CLIENT_CONFIG)
        overlay.chmod(0o644)
        home.mkdir()
        return {
            "root": tmp_path,
            "role": role,
            "home": home,
            "overlay": overlay,
            "dest": home / "Library/Application Support/tamias/config.json",
        }

    def run(
        self,
        env: Doc,
        *,
        extra_vars: Doc | None = None,
        check: bool = False,
        diff: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        play = {
            "gather_facts": False,
            "vars": {
                "ansible_python_interpreter": sys.executable,
                "ansible_facts": {"env": {"HOME": str(env["home"]), "PATH": os.environ["PATH"]}},
                "role_path": str(env["role"]),
                **(extra_vars or {}),
            },
            "tasks": [{"ansible.builtin.include_tasks": str(CLIENT)}],
        }
        result = _run_playbook(
            env["root"],
            play,
            env={"HOME": str(env["home"]), **({"ANSIBLE_DIFF_ALWAYS": "1"} if diff else {})},
            check=check,
        )
        assert CLIENT_MARKER not in result.stdout + result.stderr
        return result

    @staticmethod
    def mode(path: Path) -> int:
        return stat.S_IMODE(path.stat().st_mode)

    def test_deploys_exact_bytes_with_private_modes(self, env: Doc) -> None:
        result = self.run(env, diff=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert env["dest"].read_bytes() == CLIENT_CONFIG
        assert self.mode(env["dest"]) == 0o600
        assert self.mode(env["dest"].parent) == 0o700
        assert _changed(result) >= 1

    def test_overlay_is_left_untouched(self, env: Doc) -> None:
        assert self.run(env).returncode == 0
        assert env["overlay"].read_bytes() == CLIENT_CONFIG
        assert self.mode(env["overlay"]) == 0o644

    def test_second_run_reports_no_change(self, env: Doc) -> None:
        assert self.run(env).returncode == 0
        result = self.run(env, diff=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert _changed(result) == 0
        assert env["dest"].read_bytes() == CLIENT_CONFIG

    def test_changed_overlay_replaces_the_deployed_file_without_a_diff(self, env: Doc) -> None:
        assert self.run(env).returncode == 0
        updated = CLIENT_CONFIG.replace(b"go.example.test", b"other.example.test")
        env["overlay"].write_bytes(updated)
        result = self.run(env, diff=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert _changed(result) == 1
        assert env["dest"].read_bytes() == updated

    def test_loose_existing_modes_are_tightened(self, env: Doc) -> None:
        env["dest"].parent.mkdir(parents=True)
        env["dest"].write_bytes(CLIENT_CONFIG)
        env["dest"].parent.chmod(0o755)
        env["dest"].chmod(0o644)
        result = self.run(env)
        assert result.returncode == 0, result.stdout + result.stderr
        assert _changed(result) == 2
        assert self.mode(env["dest"]) == 0o600
        assert self.mode(env["dest"].parent) == 0o700
        assert env["dest"].read_bytes() == CLIENT_CONFIG

    def test_stale_deployed_file_with_other_content_is_overwritten(self, env: Doc) -> None:
        env["dest"].parent.mkdir(parents=True)
        env["dest"].write_bytes(b"{}")
        assert self.run(env).returncode == 0
        assert env["dest"].read_bytes() == CLIENT_CONFIG

    def test_overrides_take_precedence_over_the_defaults(self, env: Doc) -> None:
        src = env["root"] / "elsewhere/source.json"
        dest = env["root"] / "elsewhere/out/dest.json"
        src.parent.mkdir()
        src.write_bytes(b'{"from": "override"}')
        result = self.run(
            env,
            extra_vars={
                "devbox_tamias_client_config_src_override": str(src),
                "devbox_tamias_client_config_dest_override": str(dest),
            },
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert dest.read_bytes() == b'{"from": "override"}'
        assert self.mode(dest) == 0o600
        assert self.mode(dest.parent) == 0o700
        assert not env["dest"].exists()

    def test_missing_overlay_fails_and_writes_nothing(self, env: Doc) -> None:
        env["overlay"].unlink()
        result = self.run(env)
        assert result.returncode != 0
        assert "local/tamias/config.json" in result.stdout + result.stderr
        assert not (env["home"] / "Library").exists()

    def test_missing_overlay_keeps_the_previously_deployed_file(self, env: Doc) -> None:
        env["dest"].parent.mkdir(parents=True)
        env["dest"].write_bytes(b"previous")
        env["dest"].parent.chmod(0o755)
        env["overlay"].unlink()
        assert self.run(env).returncode != 0
        assert env["dest"].read_bytes() == b"previous"
        assert self.mode(env["dest"].parent) == 0o755

    def test_overlay_directory_in_place_of_the_file_fails_and_writes_nothing(
        self, env: Doc
    ) -> None:
        env["overlay"].unlink()
        env["overlay"].mkdir()
        result = self.run(env)
        assert result.returncode != 0
        assert not (env["home"] / "Library").exists()

    def test_dangling_overlay_symlink_fails_and_writes_nothing(self, env: Doc) -> None:
        env["overlay"].unlink()
        env["overlay"].symlink_to(env["root"] / "nowhere.json")
        result = self.run(env)
        assert result.returncode != 0
        assert not (env["home"] / "Library").exists()

    def test_check_mode_creates_nothing(self, env: Doc) -> None:
        result = self.run(env, check=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (env["home"] / "Library").exists()

    def test_check_mode_with_missing_overlay_still_fails(self, env: Doc) -> None:
        env["overlay"].unlink()
        assert self.run(env, check=True).returncode != 0


OVERLAY_TASK_NAMES = (
    "Check if local overlay directory exists",
    "Collect files from local overlay",
    "Create directories from local overlay",
    "Copy local overlay files",
    "Render local overlay templates",
)


def _overlay_task(name: str) -> Doc:
    return next(task for task in _load(INSTALL_CONFIGS) if task.get("name") == name)


def _overlay_runs(task_name: str, path: str, state: str) -> bool:
    return _holds(
        _overlay_task(task_name),
        devbox_local_overlay_dir={"stat": {"exists": True}},
        item={"path": path, "state": state},
    )


class TestOverlayLoopsLeaveTamiasToItsOwnTask:
    @pytest.mark.parametrize(
        ("task_name", "path", "state"),
        [
            ("Create directories from local overlay", "tamias", "directory"),
            ("Create directories from local overlay", "tamias/nested", "directory"),
            ("Copy local overlay files", "tamias/config.json", "file"),
            ("Copy local overlay files", "tamias/nested/other.json", "file"),
            ("Render local overlay templates", "tamias/config.json.j2", "file"),
            ("Render local overlay templates", "tamias/nested/x.j2", "file"),
        ],
    )
    def test_tamias_paths_are_skipped(self, task_name: str, path: str, state: str) -> None:
        assert _overlay_runs(task_name, path, state) is False

    @pytest.mark.parametrize(
        ("task_name", "path", "state"),
        [
            ("Create directories from local overlay", ".config/tamias", "directory"),
            ("Create directories from local overlay", "tamias-extra", "directory"),
            ("Create directories from local overlay", "tamiasx", "directory"),
            ("Create directories from local overlay", ".config/fish", "directory"),
            ("Copy local overlay files", ".config/tamias/config.json", "file"),
            ("Copy local overlay files", "tamias-notes.txt", "file"),
            ("Copy local overlay files", ".config/fish/config.fish", "file"),
            ("Render local overlay templates", ".config/tamias/x.j2", "file"),
            ("Render local overlay templates", "tamiasx/x.j2", "file"),
            ("Render local overlay templates", ".bashrc.j2", "file"),
        ],
    )
    def test_lookalike_and_unrelated_paths_are_still_deployed(
        self, task_name: str, path: str, state: str
    ) -> None:
        assert _overlay_runs(task_name, path, state) is True

    @pytest.mark.parametrize(
        ("task_name", "path", "state"),
        [
            ("Create directories from local overlay", "vars", "directory"),
            ("Create directories from local overlay", "host_state/sub", "directory"),
            ("Copy local overlay files", "vars/personal.yml", "file"),
            ("Copy local overlay files", "host_state/x.plist", "file"),
            ("Render local overlay templates", "vars/x.j2", "file"),
        ],
    )
    def test_existing_exclusions_still_hold(self, task_name: str, path: str, state: str) -> None:
        assert _overlay_runs(task_name, path, state) is False


COLLECTIONS = Path(os.environ.get("ANSIBLE_COLLECTIONS_PATH", Path.home() / ".ansible/collections"))


@pytest.mark.integration
@pytest.mark.skipif(
    not (COLLECTIONS / "ansible_collections/community/general").is_dir(),
    reason="community.general collection is required for the filetree lookup",
)
class TestOverlayDeployLeavesTamiasAlone:
    def test_only_tamias_paths_stay_out_of_the_dotfiles_tree(self, tmp_path: Path) -> None:
        role = tmp_path / "role"
        dotfiles = tmp_path / "dotfiles"
        dotfiles.mkdir()
        files = {
            "tamias/config.json": CLIENT_CONFIG,
            "tamias/nested/other.json": b"{}",
            "tamias/template.j2": b"rendered",
            ".config/tamias/config.json": b"lookalike",
            "tamias-notes.txt": b"notes",
            ".config/tool/settings.conf": b"setting",
            ".config/tool/rendered.conf.j2": b"rendered {{ 1 + 1 }}",
        }
        for relative, content in files.items():
            target = role / "local" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (role / "local/tamias/empty").mkdir()
        play = {
            "gather_facts": False,
            "vars": {
                "ansible_python_interpreter": sys.executable,
                "role_path": str(role),
                "devbox_paths": {"dotfiles_root_dir": str(dotfiles)},
            },
            "tasks": [_overlay_task(name) for name in OVERLAY_TASK_NAMES],
        }
        result = _run_playbook(
            tmp_path,
            play,
            env={"HOME": str(tmp_path), "ANSIBLE_COLLECTIONS_PATH": str(COLLECTIONS)},
        )
        assert result.returncode == 0, result.stdout + result.stderr
        deployed = {
            str(path.relative_to(dotfiles)): path.read_bytes() if path.is_file() else None
            for path in dotfiles.rglob("*")
        }
        assert deployed == {
            ".config": None,
            ".config/tamias": None,
            ".config/tamias/config.json": b"lookalike",
            ".config/tool": None,
            ".config/tool/settings.conf": b"setting",
            ".config/tool/rendered.conf": b"rendered 2",
            "tamias-notes.txt": b"notes",
        }
