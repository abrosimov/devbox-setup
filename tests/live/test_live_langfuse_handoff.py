"""Claude Langfuse traces survive collector outages, crashes and replays end to end.

The real Stop hook spools; the replay runner, started exactly as the rendered
LaunchAgent plist starts it, drains the spool into the pinned otelbox edge
running the repository's edge.yaml; the edge forwards over TLS to a gateway
recipient this test owns. launchd itself is out of reach on Linux, so what is
exercised is the plist's command and environment, not its schedule.

Gates closed here (docs/runbooks/langfuse-replay.md):
  G1 runtime rollout   offline edge, SIGKILLed hook, rotated transcript, overlapping Stops
  G2 durable edge ack  an edge 2xx survives an edge SIGKILL; no spool deletion before a 2xx
  G4 duplicates        a replayed, delivered transcript repeats identical span identities
"""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING, Final, NoReturn

import pytest
from engines import require_binary, unusable
from generation import apply_engine
from langfuse_handoff import (
    EDGE,
    GATEWAY_CREDENTIAL,
    HOOK_SECONDS,
    Edge,
    EdgeUnavailableError,
    Recipient,
    SpanIdentity,
    SpoolWitnessProxy,
    Stack,
    Tls,
    deadline_wait,
    deploy_claude_bin,
    free_port,
    issue_loopback_tls,
    pinned_edge_binary,
    write_transcript,
)
from throwaway import ThrowawayHome

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from subprocess import CompletedProcess

    from langfuse_handoff import JobRun

pytestmark = pytest.mark.live

SESSION_ID: Final = "8f0c2a4e-55b1-4c47-9d2e-6a1f3b7c0e11"
SIGKILLED: Final = -9
TRANSIENT_REFUSAL: Final = 503


@pytest.fixture(scope="session")
def edge_binary(request: pytest.FixtureRequest) -> Path:
    cache = request.config.cache
    if cache is None:
        unusable(EDGE, "pytest's cache provider is disabled; nowhere to keep the release asset")
    try:
        return pinned_edge_binary(cache.mkdir("otelbox-edge"))
    except EdgeUnavailableError as error:
        unusable(EDGE, str(error))


@pytest.fixture(scope="session")
def deployed_bin(edge_binary: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert edge_binary.is_file()
    return deploy_claude_bin(tmp_path_factory.mktemp("deployed") / "bin", require_binary("uv"))


@pytest.fixture(scope="session")
def claude_settings(edge_binary: Path, tmp_path_factory: pytest.TempPathFactory) -> str:
    assert edge_binary.is_file()
    home = ThrowawayHome.create(tmp_path_factory.mktemp("settings") / "home")
    apply_engine("claude", home)
    return (home.path / ".claude" / "settings.json").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def tls(tmp_path_factory: pytest.TempPathFactory) -> Tls:
    return issue_loopback_tls(tmp_path_factory.mktemp("tls"))


def build_stack(root: Path, binary: Path, deployed: Path, settings: str, tls: Tls) -> Stack:
    home = ThrowawayHome.create(root / "home")
    home.directory(".claude")
    (home.path / ".claude" / "bin").symlink_to(deployed, target_is_directory=True)
    home.write(".claude/settings.json", settings)
    transcript = home.path / ".claude" / "projects" / "-workspace" / f"{SESSION_ID}.jsonl"
    write_transcript(transcript, SESSION_ID)
    recipient = Recipient(port=free_port(), tls=tls)
    return Stack(
        home=home,
        settings=json.loads(settings),
        transcript=transcript,
        session_id=SESSION_ID,
        recipient=recipient,
        edge=Edge(binary, home.path, recipient.endpoint, tls),
    )


@pytest.fixture(scope="session")
def expected_spans(
    edge_binary: Path,
    deployed_bin: Path,
    claude_settings: str,
    tls: Tls,
    tmp_path_factory: pytest.TempPathFactory,
) -> list[SpanIdentity]:
    """What one uninterrupted Stop spools for the transcript every test uses."""
    reference = build_stack(
        tmp_path_factory.mktemp("reference"), edge_binary, deployed_bin, claude_settings, tls
    )
    hook = reference.stop_hook()
    assert hook.returncode == 0, f"{hook.stderr}\n{reference.diagnostics()}"
    spans = reference.spooled_spans()
    assert spans, reference.diagnostics()
    return spans


@pytest.fixture
def stack(
    tmp_path: Path, edge_binary: Path, deployed_bin: Path, claude_settings: str, tls: Tls
) -> Iterator[Stack]:
    built = build_stack(tmp_path, edge_binary, deployed_bin, claude_settings, tls)
    try:
        yield built
    finally:
        built.close()


def fail(stack: Stack, what: str, detail: str = "") -> NoReturn:
    pytest.fail(f"{what}\n{detail}\n{stack.diagnostics()}")


def require_hook(stack: Stack, hook: CompletedProcess[str]) -> None:
    if hook.returncode != 0:
        fail(stack, f"Stop hook exited {hook.returncode}", hook.stderr)


def require_replay(stack: Stack, run: JobRun) -> None:
    if run.returncode != 0:
        fail(stack, f"replay job exited {run.returncode}", run.output)


def kill_hook(stack: Stack, fault: str) -> None:
    hook = stack.faulted_hook(fault)
    _, stderr = hook.communicate(timeout=HOOK_SECONDS)
    if hook.returncode != SIGKILLED:
        fail(stack, f"{fault} hook exited {hook.returncode}, not SIGKILL", stderr)


def bring_up_gateway_and_edge(stack: Stack) -> None:
    stack.recipient.start()
    stack.edge.start()


def require_delivered(stack: Stack, expected: list[SpanIdentity], copies: int = 1) -> None:
    try:
        stack.recipient.wait_for_each(expected, copies)
    except TimeoutError as error:
        fail(stack, str(error))


def marker_record(stack: Stack) -> dict[str, str]:
    (marker,) = stack.markers()
    return json.loads(marker.read_text(encoding="utf-8"))


def test_spool_holds_turns_while_the_edge_is_down_and_replay_delivers_every_span(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    require_hook(stack, stack.stop_hook())
    assert stack.spooled_spans() == expected_spans
    assert not stack.markers()
    spooled = stack.committed_batches()

    offline = stack.replay()
    assert offline.returncode != 0, offline.output
    assert stack.committed_batches() == spooled

    bring_up_gateway_and_edge(stack)
    require_replay(stack, stack.replay())

    assert not stack.committed_batches()
    require_delivered(stack, expected_spans)
    assert stack.recipient.received() == Counter(expected_spans)
    assert stack.recipient.authorizations == {f"Bearer {GATEWAY_CREDENTIAL}"}


def test_hook_killed_mid_export_is_recovered_by_replay(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    kill_hook(stack, "kill-mid-export")
    assert not stack.committed_batches()
    assert len(stack.markers()) == 1

    bring_up_gateway_and_edge(stack)
    require_replay(stack, stack.replay())

    assert not stack.markers()
    require_delivered(stack, expected_spans)
    assert stack.recipient.received() == Counter(expected_spans)


def test_replay_delivers_from_the_snapshot_after_the_transcript_is_rotated(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    kill_hook(stack, "kill-mid-export")
    stack.transcript.rename(stack.transcript.with_name(f"{stack.transcript.name}.1"))

    bring_up_gateway_and_edge(stack)
    require_replay(stack, stack.replay())

    assert not stack.markers()
    require_delivered(stack, expected_spans)
    assert stack.recipient.received() == Counter(expected_spans)


def test_overlapping_stops_keep_the_newer_marker_and_lose_nothing(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    older = stack.faulted_hook("pause-after-commit")
    deadline_wait(
        lambda: (stack.signals / "paused").exists() or older.poll() is not None,
        HOOK_SECONDS,
        "the older Stop to commit its spans",
    )
    if older.poll() is not None:
        fail(stack, f"older Stop exited {older.returncode} before pausing")
    older_nonce = marker_record(stack)["nonce"]

    newer = stack.stop_hook()
    assert newer.returncode != 0, "the newer Stop got the session lock the older one holds"
    newer_record = marker_record(stack)
    assert newer_record["nonce"] != older_nonce

    (stack.signals / "release").touch()
    _, stderr = older.communicate(timeout=HOOK_SECONDS)
    if older.returncode != 0:
        fail(stack, f"older Stop exited {older.returncode} after release", stderr)
    assert marker_record(stack) == newer_record

    bring_up_gateway_and_edge(stack)
    require_replay(stack, stack.replay())

    assert not stack.markers()
    require_delivered(stack, expected_spans)
    assert stack.recipient.received() == Counter(expected_spans)


def test_edge_acknowledgement_survives_an_edge_kill_before_forwarding(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    require_hook(stack, stack.stop_hook())
    stack.edge.start()
    require_replay(stack, stack.replay())
    assert not stack.committed_batches()

    stack.edge.kill()
    assert not stack.recipient.received()
    bring_up_gateway_and_edge(stack)

    require_delivered(stack, expected_spans)
    assert set(stack.recipient.received()) == set(expected_spans)


def test_spool_batches_stay_on_disk_until_the_edge_answers_2xx(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    require_hook(stack, stack.stop_hook())
    spooled = stack.committed_batches()

    with SpoolWitnessProxy(stack.spool, refuse_with=TRANSIENT_REFUSAL) as refusing:
        stack.point_replay_at(refusing.base_url)
        refused = stack.replay()
    assert refused.returncode != 0, refused.output
    assert refusing.witnesses
    assert {witness.status for witness in refusing.witnesses} == {TRANSIENT_REFUSAL}
    assert stack.committed_batches() == spooled

    bring_up_gateway_and_edge(stack)
    with SpoolWitnessProxy(stack.spool) as relaying:
        stack.point_replay_at(relaying.base_url)
        require_replay(stack, stack.replay())

    assert len(relaying.witnesses) == len(spooled)
    for witness in relaying.witnesses:
        assert 200 <= witness.status < 300
        assert witness.on_disk_at_arrival
        assert witness.on_disk_at_answer
    assert not stack.committed_batches()
    require_delivered(stack, expected_spans)
    assert stack.recipient.received() == Counter(expected_spans)


def test_replaying_a_delivered_transcript_repeats_identical_span_identities(
    stack: Stack, expected_spans: list[SpanIdentity]
) -> None:
    kill_hook(stack, "kill-after-commit")
    assert stack.spooled_spans() == expected_spans
    assert len(stack.markers()) == 1

    bring_up_gateway_and_edge(stack)
    require_replay(stack, stack.replay())

    require_delivered(stack, expected_spans, copies=2)
    assert stack.recipient.received() == Counter(dict.fromkeys(expected_spans, 2))
