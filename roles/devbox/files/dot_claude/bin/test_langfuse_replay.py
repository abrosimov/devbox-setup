# ruff: noqa: ARG001
"""Persistent pending-session and independent replay tests (no network)."""

from __future__ import annotations

import ast
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import langfuse_replay
import langfuse_trace_hook
import pytest

BIN = Path(__file__).parent
OPTION_SOURCES = (
    BIN / "vendor" / "langfuse_hook.py",
    BIN / "vendor" / "durable_otel_exporter.py",
    BIN / "langfuse_trace_hook.py",
)
ENVIRONMENT_READERS = frozenset({"_opt", "_core_opt", "os.environ.get", "os.getenv"})
# Options that neither the marker records nor replay forwards from settings.json.
NOT_REPLAYED = {
    "CC_LANGFUSE_PENDING_REPLAY": "replay sets it on every run it starts",
    "CC_LANGFUSE_STATE_IDENTITY_PATH": "replay sets it per marker when it runs the snapshot",
    "CC_LANGFUSE_TRACE_TAGS": "the marker carries it in its own trace_tags field",
    "CC_LANGFUSE_USER_ID": (
        "deployment sets the unprefixed LANGFUSE_USER_ID, which _core_opt reads first "
        "and the marker carries in its user_id field"
    ),
}


@pytest.fixture
def pending_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    state_dir = tmp_path / "state"
    monkeypatch.setenv("CC_LANGFUSE_STATE_DIR", str(state_dir))
    monkeypatch.setenv("LANGFUSE_USER_ID", "test-user")
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "personal")
    monkeypatch.delenv(langfuse_trace_hook.REPLAY_ENV, raising=False)
    return state_dir


def sample_payload(tmp_path: Path) -> dict[str, str]:
    transcript = tmp_path / "session-001.jsonl"
    transcript.write_text('{"type":"user","message":"hello"}\n', encoding="utf-8")
    return {
        "session_id": "session-001",
        "transcript_path": str(transcript),
        "hook_event_name": "SessionEnd",
    }


def test_pending_registration_is_durable_and_recoverable(
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    marker, nonce, snapshot = record
    saved = json.loads(marker.read_text(encoding="utf-8"))
    assert saved["nonce"] == nonce
    assert saved["user_id"] == "test-user"
    assert saved["hook_event_name"] == "SessionEnd"
    assert snapshot.read_bytes() == Path(saved["transcript_path"]).read_bytes()
    assert snapshot.name == Path(saved["transcript_path"]).name
    langfuse_trace_hook.complete_pending(*record)
    assert not marker.exists()
    assert not snapshot.exists()


def test_old_hook_cannot_clear_a_newer_pending_session(
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    first = langfuse_trace_hook.register_pending(payload)
    second = langfuse_trace_hook.register_pending(payload)
    assert first is not None
    assert second is not None
    langfuse_trace_hook.complete_pending(*first)
    latest = json.loads(second[0].read_text(encoding="utf-8"))
    assert latest["nonce"] == second[1]
    assert second[2].is_file()


def test_failed_hook_keeps_its_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    def failed_hook(*_args, **_kwargs):
        raise SystemExit(1)

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", failed_hook)
    with pytest.raises(SystemExit) as exc:
        langfuse_trace_hook.main()
    assert exc.value.code == 1
    assert len(list((pending_environment / "langfuse_pending").glob("*.json"))) == 1


def test_repeated_failed_stops_keep_one_snapshot_per_session(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)

    def failed_hook(*_args, **_kwargs):
        raise SystemExit(1)

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", failed_hook)
    for _ in range(3):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        with pytest.raises(SystemExit):
            langfuse_trace_hook.main()

    root = pending_environment / "langfuse_pending"
    (marker,) = root.glob("*.json")
    record = json.loads(marker.read_text(encoding="utf-8"))
    snapshots = [path for path in root.iterdir() if path.is_dir()]
    assert snapshots == [Path(record["snapshot_path"]).parent]
    assert Path(record["snapshot_path"]).is_file()


def test_completed_hook_clears_its_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(sample_payload(tmp_path))))
    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", lambda *_args, **_kwargs: None)
    langfuse_trace_hook.main()
    assert not list((pending_environment / "langfuse_pending").glob("*.json"))


def test_replay_uses_snapshot_when_original_transcript_was_removed(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    record = langfuse_trace_hook.register_pending(payload)
    assert record is not None
    marker, _, snapshot = record
    Path(payload["transcript_path"]).unlink()
    calls: list[dict] = []

    def fake_run(_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(langfuse_replay.subprocess, "run", fake_run)
    env = {"CC_LANGFUSE_BASE_URL": "http://127.0.0.1:14318"}
    assert langfuse_replay.replay_one(marker, env)
    request = json.loads(calls[0]["input"])
    assert request["transcript_path"] == str(snapshot)
    assert calls[0]["env"]["CC_LANGFUSE_STATE_IDENTITY_PATH"] == payload["transcript_path"]
    assert not marker.exists()


def test_failed_replay_preserves_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    marker, _, snapshot = record
    monkeypatch.setattr(
        langfuse_replay.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr=""),
    )
    assert not langfuse_replay.replay_one(marker, {})
    assert marker.is_file()
    assert snapshot.is_file()


def test_replay_forwards_the_disk_caps_configured_for_the_hook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    configured = {
        "CC_LANGFUSE_BASE_URL": "http://127.0.0.1:14318",
        "CC_LANGFUSE_PUBLIC_KEY": "pk",
        "CC_LANGFUSE_SECRET_KEY": "sk",
        "CC_LANGFUSE_SPOOL_MAX_BYTES": "1048576",
        "CC_LANGFUSE_PENDING_MAX_BYTES": "2097152",
    }
    settings.write_text(json.dumps({"env": configured}), encoding="utf-8")
    monkeypatch.setattr(langfuse_replay, "SETTINGS", settings)

    environment = langfuse_replay.replay_environment()

    assert environment["CC_LANGFUSE_SPOOL_MAX_BYTES"] == "1048576"
    assert environment["CC_LANGFUSE_PENDING_MAX_BYTES"] == "2097152"


def replayed_environment(
    monkeypatch: pytest.MonkeyPatch, marker: Path, base_env: dict[str, str]
) -> dict[str, str]:
    calls: list[dict] = []

    def fake_run(_args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(langfuse_replay.subprocess, "run", fake_run)
    assert langfuse_replay.replay_one(marker, base_env)
    return calls[0]["env"]


def test_marker_run_options_win_over_settings_including_their_absence(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    for name in langfuse_trace_hook.RUN_SCOPED_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CC_LANGFUSE_MAX_CHARS", "5000")
    monkeypatch.setenv("CC_LANGFUSE_SKILL_TAGS", "false")
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    settings = {"CC_LANGFUSE_MAX_CHARS": "100", "CC_LANGFUSE_CAPTURE_SKILL_CONTENT": "true"}

    environment = replayed_environment(monkeypatch, record[0], settings)

    assert environment["CC_LANGFUSE_MAX_CHARS"] == "5000"
    assert environment["CC_LANGFUSE_SKILL_TAGS"] == "false"
    assert "CC_LANGFUSE_CAPTURE_SKILL_CONTENT" not in environment


def test_marker_without_run_options_falls_back_to_settings(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    record = langfuse_trace_hook.register_pending(sample_payload(tmp_path))
    assert record is not None
    marker = record[0]
    legacy = json.loads(marker.read_text(encoding="utf-8"))
    del legacy["run_environment"]
    legacy |= {"trace_seed": "legacy-seed", "traceparent": ""}
    marker.write_text(json.dumps(legacy), encoding="utf-8")
    settings = {"CC_LANGFUSE_MAX_CHARS": "100", "CC_LANGFUSE_TRACE_SEED": "settings-seed"}

    environment = replayed_environment(monkeypatch, marker, settings)

    assert environment["CC_LANGFUSE_MAX_CHARS"] == "100"
    assert environment["CC_LANGFUSE_TRACE_SEED"] == "legacy-seed"
    assert environment["CC_LANGFUSE_TRACEPARENT"] == ""


def test_replay_environment_takes_run_options_from_settings_for_legacy_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = tmp_path / "settings.json"
    configured = {
        "CC_LANGFUSE_BASE_URL": "http://127.0.0.1:14318",
        "CC_LANGFUSE_PUBLIC_KEY": "pk",
        "CC_LANGFUSE_SECRET_KEY": "sk",
        "CC_LANGFUSE_MAX_CHARS": "4096",
        "CC_LANGFUSE_SKILL_TAGS": "false",
    }
    settings.write_text(json.dumps({"env": configured}), encoding="utf-8")
    monkeypatch.setattr(langfuse_replay, "SETTINGS", settings)

    environment = langfuse_replay.replay_environment()

    assert environment["CC_LANGFUSE_MAX_CHARS"] == "4096"
    assert environment["CC_LANGFUSE_SKILL_TAGS"] == "false"


def string_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants |= {t.id: value.value for t in targets if isinstance(t, ast.Name)}
    return constants


def environment_options_read(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"))
    constants = string_constants(tree)

    def literal(node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return constants.get(node.id) if isinstance(node, ast.Name) else None

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            reader = ast.unparse(node.func)
            name = literal(node.args[0]) if reader in ENVIRONMENT_READERS else None
            if name is not None:
                names.add(f"CC_{name}" if reader == "_core_opt" else name)
        elif isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ":
            name = literal(node.slice)
            if name is not None:
                names.add(name)
    return {name for name in names if name.startswith("CC_LANGFUSE_")}


def test_every_langfuse_option_the_hook_reads_is_classified_for_replay() -> None:
    read = set().union(*(environment_options_read(source) for source in OPTION_SOURCES))
    assert {
        "CC_LANGFUSE_MAX_CHARS",
        "CC_LANGFUSE_PUBLIC_KEY",
        "CC_LANGFUSE_SPOOL_MAX_BYTES",
    } <= read
    classified = (
        set(langfuse_trace_hook.RUN_SCOPED_VARIABLES)
        | set(langfuse_replay.REPLAY_SETTINGS)
        | set(NOT_REPLAYED)
    )
    unclassified = sorted(read - classified)
    assert not unclassified, (
        f"{unclassified}: add each to RUN_SCOPED_VARIABLES (per run, recorded by the marker), "
        "REPLAY_SETTINGS (per machine, from settings.json) or NOT_REPLAYED with the reason"
    )


def test_transcript_removed_during_hook_retains_pending_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    pending_environment: Path,
    tmp_path: Path,
) -> None:
    payload = sample_payload(tmp_path)
    source = Path(payload["transcript_path"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))

    def remove_source(*_args, **_kwargs):
        source.unlink()

    monkeypatch.setattr(langfuse_trace_hook.runpy, "run_path", remove_source)
    langfuse_trace_hook.main()
    markers = list((pending_environment / "langfuse_pending").glob("*.json"))
    assert len(markers) == 1
    record = json.loads(markers[0].read_text(encoding="utf-8"))
    assert Path(record["snapshot_path"]).is_file()
