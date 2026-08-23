"""Static contract between the otelbox edge profile, its playbook and its LaunchAgent.

Three artefacts have to agree on the same environment variables: the deployed
edge.yaml, the `validate` preflight in install_otelbox_edge.yml, and the plist that
launchd renders. Behavioural coverage of the wrapper and the endpoint contract lives
in tests/scripts/test_otelbox_edge_*.py.
"""

from __future__ import annotations

import plistlib
import re
import stat
from pathlib import Path
from typing import Any

import pytest
import yaml
from jinja2 import Environment, StrictUndefined, Template

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLE = REPO_ROOT / "roles/devbox"
EDGE_YAML = ROLE / "files/.config/otelbox/edge/edge.yaml"
TASKS = ROLE / "tasks/darwin/install_otelbox_edge.yml"
PLIST_TEMPLATE = ROLE / "templates/darwin/Library/LaunchAgents/local.otelbox-edge.plist.j2"
PACKAGES = ROLE / "defaults/main/packages.yml"
CERT_CHECKER = REPO_ROOT / "scripts/otelbox-edge-cert-check.sh"

_edge: dict[str, Any] = yaml.safe_load(EDGE_YAML.read_text(encoding="utf-8"))
_tasks: list[dict[str, Any]] = yaml.safe_load(TASKS.read_text(encoding="utf-8"))
_otelbox_defaults: dict[str, Any] = yaml.safe_load(PACKAGES.read_text(encoding="utf-8"))[
    "devbox_packages"
]["otelbox_edge"]

_GATEWAY_TLS: dict[str, Any] = _edge["exporters"]["otlp_grpc/gateway"]["tls"]


def _task(name_suffix: str) -> dict[str, Any]:
    return next(t for t in _tasks if t["name"].endswith(name_suffix))


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        # The `:-` empty default is the load-bearing part: it is what makes a machine
        # without a certificate offer none, exactly as it did before mTLS support.
        ("cert_file", "${env:OTELBOX_UPSTREAM_TLS_CERT_FILE:-}"),
        ("key_file", "${env:OTELBOX_UPSTREAM_TLS_KEY_FILE:-}"),
        ("reload_interval", "${env:OTELBOX_UPSTREAM_TLS_RELOAD_INTERVAL:-1h}"),
    ],
)
def test_gateway_tls_expansions(key: str, expected: str) -> None:
    assert _GATEWAY_TLS[key] == expected


def test_gateway_compression_defaults_to_zstd() -> None:
    exporter = _edge["exporters"]["otlp_grpc/gateway"]
    assert exporter["compression"] == "${env:OTELBOX_UPSTREAM_COMPRESSION:-zstd}"


def test_gateway_tls_stays_verified() -> None:
    assert _GATEWAY_TLS["insecure"] is False


def _client_pair(present: tuple[str, ...]) -> dict[str, Any]:
    return {
        "results": [
            {"item": name, "stat": {"exists": name in present}}
            for name in ("client.crt", "client.key")
        ]
    }


_HALF_PAIR_TASK = _task("refuse half a client certificate pair")
_HALF_PAIR_CLAUSE = next(c for c in _HALF_PAIR_TASK["when"] if "selectattr" in c)


@pytest.mark.parametrize(
    ("present", "expected"),
    [
        (("client.crt", "client.key"), "False"),
        ((), "False"),
        (("client.crt",), "True"),
        (("client.key",), "True"),
    ],
)
def test_half_a_certificate_pair_fails_the_run(present: tuple[str, ...], expected: str) -> None:
    rendered = Template("{{ " + _HALF_PAIR_CLAUSE + " }}", undefined=StrictUndefined).render(
        devbox_otelbox_edge_client_pair=_client_pair(present)
    )
    assert rendered == expected


def test_half_a_certificate_pair_task_is_a_fail() -> None:
    assert "ansible.builtin.fail" in _HALF_PAIR_TASK
    assert "client.crt and client.key" in _HALF_PAIR_TASK["ansible.builtin.fail"]["msg"]


def test_complete_certificate_pair_is_validated_before_cleanup() -> None:
    validation = _task("validate the optional client certificate pair")
    validation_index = _tasks.index(validation)
    destructive_indices = [
        index
        for index, task in enumerate(_tasks)
        if "stop " in task["name"] or "WAL" in task["name"]
    ]

    argv = validation["ansible.builtin.command"]["argv"]
    assert argv[0].endswith("scripts/otelbox-edge-cert-check.sh")
    assert argv[1:] == [
        "{{ devbox_otelbox_edge_conf }}/client/client.crt",
        "{{ devbox_otelbox_edge_conf }}/client/client.key",
    ]
    assert destructive_indices
    assert all(validation_index < index for index in destructive_indices)
    assert validation["check_mode"] is False


def test_certificate_checker_is_executable() -> None:
    assert CERT_CHECKER.stat().st_mode & stat.S_IXUSR


def _render_boolean(expression: str, **context: object) -> str:
    environment = Environment(undefined=StrictUndefined, autoescape=True)
    environment.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
    return environment.from_string(expression).render(**context)


@pytest.mark.parametrize(
    ("exists", "returncode", "version", "compatible", "incompatible"),
    [
        (1, 0, "otelcol-otelbox version 2.1.0", "True", "False"),
        (1, 0, "otelcol-otelbox version 2.2.0", "True", "False"),
        (1, 0, "otelcol-otelbox version 1.9.0", "False", "True"),
        (1, 0, "unexpected output", "False", "False"),
        (1, 1, "", "False", "False"),
        (0, 1, "", "False", "False"),
    ],
)
def test_existing_wal_compatibility_is_classified_explicitly(
    exists: int,
    returncode: int,
    version: str,
    compatible: str,
    incompatible: str,
) -> None:
    facts = _task("classify the current managed binary")["ansible.builtin.set_fact"]
    context = {
        "devbox_otelbox_edge_existing_bin_stat": {"stat": {"exists": bool(exists)}},
        "devbox_otelbox_edge_existing_version": {
            "rc": returncode,
            "stdout": version,
        },
        "devbox_packages": {"otelbox_edge": {"version": "2.2.0"}},
    }

    assert (
        _render_boolean(facts["devbox_otelbox_edge_existing_is_compatible_v2"], **context)
        == compatible
    )
    assert (
        _render_boolean(
            facts["devbox_otelbox_edge_existing_is_explicitly_incompatible"],
            **context,
        )
        == incompatible
    )


def test_wal_cleanup_requires_explicit_incompatibility() -> None:
    cleanup = _task("discard WAL from an incompatible managed collector")

    assert cleanup["when"][-1] == ("devbox_otelbox_edge_existing_is_explicitly_incompatible | bool")


def test_preflight_gate_ignores_the_client_certificate() -> None:
    # REGRESSION GUARD. devbox_otelbox_edge_preflight_ready gates the entire install —
    # binary, profile, wrapper, plist, legacy cleanup. Folding certificate presence
    # into it would turn a missing optional certificate into a kill-switch for the
    # whole collector, so the expression must not mention it at all.
    expression = _task("decide whether preflight can run")["ansible.builtin.set_fact"][
        "devbox_otelbox_edge_preflight_ready"
    ].lower()
    for token in ("client", "cert", "tls", "crt"):
        assert token not in expression


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        # Empty on purpose: the absent-certificate case is the one `validate` must cover.
        ("OTELBOX_UPSTREAM_TLS_CERT_FILE", ""),
        ("OTELBOX_UPSTREAM_TLS_KEY_FILE", ""),
        ("OTELBOX_UPSTREAM_TLS_RELOAD_INTERVAL", "1h"),
        ("OTELBOX_UPSTREAM_COMPRESSION", "zstd"),
    ],
)
def test_profile_validate_environment(key: str, expected: str) -> None:
    environment = _task("validate the pinned profile before cleanup")["environment"]
    assert key in environment
    assert environment[key] == expected


def _render_plist(compression: str) -> dict[str, Any]:
    rendered = Template(
        PLIST_TEMPLATE.read_text(encoding="utf-8"), undefined=StrictUndefined
    ).render(
        ansible_facts={"env": {"HOME": "/Users/tester"}},
        devbox_packages={"otelbox_edge": {"upstream_compression": compression}},
        devbox_active_profile="personal",
    )
    return plistlib.loads(rendered.encode("utf-8"))["EnvironmentVariables"]


def test_plist_renders_compression_from_the_variable() -> None:
    assert _render_plist("gzip")["OTELBOX_UPSTREAM_COMPRESSION"] == "gzip"


def test_plist_compression_matches_the_role_default() -> None:
    default = _otelbox_defaults["upstream_compression"]
    assert _render_plist(default)["OTELBOX_UPSTREAM_COMPRESSION"] == default
