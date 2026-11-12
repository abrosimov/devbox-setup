# Claude Langfuse durable replay — operator runbook

Status: **PR #72; the pre-merge gates are automated end-to-end tests in CI** (see [Pre-merge verification](#pre-merge-verification)). There is no manual Mac rollout step.

## Data path and guarantees

A Claude `SessionStart`, `Stop` or `SessionEnd` hook writes a local pending marker and a private snapshot of its transcript **before** calling the vendored Langfuse exporter. The hook will only remove that marker after emission, SDK flush and checkpoint saving complete. A failed or timed-out export leaves the prior emission cursor and the pending snapshot intact. The independent login-user LaunchAgent `local.langfuse-replay` replays pending sessions every 300 seconds and after login.

Pending files are located under `~/.claude/state/langfuse_pending/` unless `CC_LANGFUSE_STATE_DIR` is configured. Files are chmod 0600 and new snapshot directories 0700. They contain real transcript content and must be protected as sensitive local data. The marker records session metadata and the firing's run-scoped options, never operator Langfuse API credentials. The worker reads the *deployed* local-edge sentinel configuration and exports only through the loopback edge collector.

Replay re-runs a firing as it ran. The run-scoped options — `CC_LANGFUSE_TRACE_SEED`, `CC_LANGFUSE_TRACEPARENT`, `CC_LANGFUSE_PARENT_TRACE_ID`, `CC_LANGFUSE_PARENT_SPAN_ID`, `CC_LANGFUSE_MAX_CHARS`, `CC_LANGFUSE_SKILL_TAGS`, `CC_LANGFUSE_CAPTURE_SKILL_CONTENT` (`RUN_SCOPED_VARIABLES` in `langfuse_trace_hook.py`) — are recorded in the marker's `run_environment`, absence included, and replay restores exactly those values over whatever `settings.json` says. A seeded or attached session therefore keeps its trace and span ids on replay. A marker written before `run_environment` existed still replays: its `trace_seed` and `traceparent` fields are used, and the other run-scoped options come from the `env` block of `settings.json`, as do the per-machine options (`REPLAY_SETTINGS` in `langfuse_replay.py`).

Observation content is not truncated: prompts, replies, thinking, tool inputs and tool results are exported whole unless `CC_LANGFUSE_MAX_CHARS` is set, in which case text longer than that many characters is cut as upstream does (vendored patch `0009`).

This is **at-least-once**, not exactly once: after a crash between spooling a firing's batches and saving its checkpoint, replay re-emits that firing. Every observation id is derived from the transcript, so a re-emission repeats the original trace id, span id, parent span id and times exactly; Langfuse v4 still stores it as a second observation until deduplication lands at the otelbox gateway (`docs/design/langfuse-durable-handoff.md`). `Langfuse.flush()` is not assumed to be an end-to-end durable backend ACK: the hook acknowledges only fsynced spool files, and only an edge HTTP 2xx deletes one. The gateway's independent durable fan-out contract is addressed in `setup_lab/docs/rfcs/0001-durable-telemetry-fanout.md`.

## Disk budget

Both local stores are capped. A full store never deletes undelivered data to make room: it refuses new data, and the hook exits nonzero with one stderr line naming the cap and the path. Replay keeps draining while a store is full, so the condition clears on its own once the edge is reachable.

| Store | Path | Cap variable | Default |
| --- | --- | --- | --- |
| OTLP spool (spans fsynced, awaiting the edge) | `~/.claude/state/langfuse_otlp_spool/` | `CC_LANGFUSE_SPOOL_MAX_BYTES` | 2 GiB |
| Transcript snapshots and pending markers | `~/.claude/state/langfuse_pending/` | `CC_LANGFUSE_PENDING_MAX_BYTES` | 2 GiB |

The spool fills only while the loopback edge is unreachable; the edge carries its own WAL, sized for a 72-hour gateway outage. A snapshot outlives its Stop only when that hook failed, so the pending store is normally near empty. Both values are bytes. To change one, set it in the `env` block of Claude's settings (`roles/devbox/files/dot_claude/settings.json.j2`): the hook reads it from there, and the replay runner forwards it from the same file to the hook runs it starts.

- **Spool full:** the firing's spans are refused, its staging is dropped and its checkpoint does not advance, so its pending snapshot keeps the turns for replay. Stderr: `durable_otel_exporter: Langfuse OTLP spool full: ... exceeds CC_LANGFUSE_SPOOL_MAX_BYTES=<cap> at <path> ...`.
- **Pending store full:** no snapshot is taken for this firing, the turns are still exported to the spool, and the hook exits 1. Stderr: `langfuse_trace_hook: Langfuse pending store full: ... exceeds CC_LANGFUSE_PENDING_MAX_BYTES=<cap> at <path> ...`. The re-registration of a session does not count the snapshot it replaces.

## Oversized spans

A single span whose OTLP encoding exceeds `MAX_BATCH_BYTES` (96 MiB, below the edge's 128 MiB request cap) cannot be delivered in any batch. It is not truncated and it does not fail the firing: the exporter stages it whole, and when the firing commits it moves to `~/.claude/state/langfuse_otlp_quarantine/` while the firing's other spans go to the spool as usual. Replay therefore does not retry it. One line per span names the session, the size and the cap, on the hook's stderr and in the hook log (`langfuse_hook.log` beside the spool); replay copies a replayed firing's stderr into `~/Library/Logs/langfuse-replay.log`: `Langfuse OTLP span of session <id> is <n> bytes, over the <cap>-byte batch cap: quarantined whole, not delivered: <path>`. A quarantined file is a complete OTLP request holding that one span; delivering it needs an edge and gateway that accept its size. Quarantined files are not counted against `CC_LANGFUSE_SPOOL_MAX_BYTES` and are never deleted automatically.

## Inspect without mutation

```sh
launchctl print "gui/$(id -u)/local.langfuse-replay"
find ~/.claude/state/langfuse_pending -maxdepth 1 -name '*.json' -type f -print
tail -100 ~/Library/Logs/langfuse-replay.log
```

Only marker **filenames** should be shared. Do not paste pending JSON, transcript snapshots, secrets, or whole environment dumps into an issue.

## Manually invoke one retry pass

```sh
~/.claude/bin/.venv/bin/python ~/.claude/bin/langfuse_replay.py
```

Exit 0 means that this pass processed the currently readable pending registry. Nonzero means at least one item remains pending or local replay configuration is unavailable; it does **not** mean the item should be deleted. After the edge returns, repeat the command and confirm the pending count declines.

The worker may see `Stop` and `SessionEnd` pending work concurrently with live Claude. Each attempt uses the vendored hook's per-session file lock and only deletes a marker with the same nonce it read; a newer marker survives.

## Failure handling

| Failure | Required action |
| --- | --- |
| Local collector unreachable | Keep pending files; verify `local.otelbox-edge`, edge logs and restart/retry |
| Hook timeout | Keep pending snapshot; retry by LaunchAgent/manual pass |
| Session transcript was deleted | Replay falls back to the snapshot, retaining the original checkpoint identity |
| Spool or pending store at its cap | Hook stderr names the cap and path; bring the edge back and let replay drain, or raise the cap. Never delete spool or pending files |
| Disk full while snapshotting | Hook reports failure on stderr and still exports; free storage, retain original transcript and existing pending records |
| Malformed marker / missing snapshot | Do not delete marker silently; inspect local spool and investigate |
| `... over the <cap>-byte batch cap: quarantined whole` | The rest of the session was delivered; the named span sits in `langfuse_otlp_quarantine/`. Keep the file; it needs a larger receiver envelope to be delivered |
| Backlog does not drain | Check current hook log and edge metrics; never `rm -rf` the pending directory as a recovery step |

No automatic TTL-based deletion is enabled; this deliberately prioritises not deleting undelivered snapshots. The caps above bound the disk the stores can take instead.

## Pre-merge verification

The former manual Mac failure-injection exercise is replaced by tests that CI runs on every push (`.github/workflows/ci.yml`):

| Gate | Test | Make target |
| --- | --- | --- |
| G1 runtime rollout: edge offline at Stop, hook SIGKILLed mid-export, transcript rotated before replay, overlapping Stops | `tests/live/test_live_langfuse_handoff.py` | `make test-langfuse-e2e ENGINES=otelbox-edge` (CI job `langfuse-e2e`) |
| G2 edge 2xx is durable (edge SIGKILLed after 2xx, before forwarding); no spool deletion before a 2xx | `tests/live/test_live_langfuse_handoff.py` | as above |
| G3 disk budget: reaching each cap, recovery once replay frees space | `roles/devbox/files/dot_claude/bin/test_langfuse_capacity.py`, `test_langfuse_otlp_spool.py` | `make test-claude-hooks` |
| G4 identical identities when a delivered transcript is replayed | `tests/live/test_live_langfuse_handoff.py` | `make test-langfuse-e2e ENGINES=otelbox-edge` |

The end-to-end tests drive real processes: the Stop hook command from the generated `settings.json`, the replay runner with the rendered LaunchAgent plist's arguments and log path under launchd's default environment, and the pinned `otelcol-otelbox` release (checked against its published `.sha256`) running the repository's `edge.yaml` and forwarding over TLS to a gateway recipient the test owns. They need Linux: on macOS the edge trusts only the Keychain and a running local edge holds its fixed ports, so locally the suite skips with that reason; `ENGINES=otelbox-edge` turns the skip into a failure. launchd's own scheduling is not exercised.

Do **not** claim end-to-end losslessness from an empty pending directory alone; the gateway's fan-out to Langfuse is outside these tests.
