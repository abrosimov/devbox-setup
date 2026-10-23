# Claude Langfuse durable replay — operator runbook

Status: **candidate implementation in PR #72; do not treat as production verified before a Mac smoke test.**

## Data path and guarantees

A Claude `SessionStart`, `Stop` or `SessionEnd` hook writes a local pending marker and a private snapshot of its transcript **before** calling the vendored Langfuse exporter. The hook will only remove that marker after emission, SDK flush and checkpoint saving complete. A failed or timed-out export leaves the prior emission cursor and the pending snapshot intact. The independent login-user LaunchAgent `local.langfuse-replay` replays pending sessions every 300 seconds and after login.

Pending files are located under `~/.claude/state/langfuse_pending/` unless `CC_LANGFUSE_STATE_DIR` is configured. Files are chmod 0600 and new snapshot directories 0700. They contain real transcript content and must be protected as sensitive local data. The marker records session metadata only, never operator Langfuse API credentials. The worker reads the *deployed* local-edge sentinel configuration and exports only through the loopback edge collector.

This is **at-least-once**, not exactly once: after a crash between remote acceptance and local checkpoint a session may be re-emitted. Stable trace identity does not automatically make generated observation IDs idempotent. `Langfuse.flush()` is not assumed to be an end-to-end durable backend ACK. The gateway's independent durable fan-out contract is addressed in `setup_lab/docs/rfcs/0001-durable-telemetry-fanout.md`.

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
| Disk full while snapshotting | Hook reports failure; free storage, retain original transcript and existing pending records |
| Malformed marker / missing snapshot | Do not delete marker silently; inspect local spool and investigate |
| Backlog does not drain | Check current hook log and edge metrics; never `rm -rf` the pending directory as a recovery step |

No automatic TTL-based deletion is currently enabled; this deliberately prioritises not deleting undelivered snapshots. Plan capacity monitoring and a *verified* orphan cleanup policy before production adoption.

## Pre-merge Mac failure-injection exercise

1. Apply this PR's configuration on a non-production Mac profile; verify the pinned Python venv and LaunchAgent are installed.
2. Stop local otelbox edge, execute one non-sensitive Claude turn and end the session. Confirm the hook reports unsuccessful handoff and creates a pending marker/snapshot.
3. Restore the edge and invoke the retry runner. Check the marker is removed **only** after the worker reports success, and verify the trace in Langfuse.
4. Repeat with forced process kill during hook export, while preserving the pending directory. Confirm recovery after restart/login.
5. Test deletion/rotation of an original transcript with a durable snapshot and verify replay can still read its content under the original session key.
6. Test two overlapping `Stop` attempts for the same session and verify the older completion does not remove the newer marker.
7. Cross-check edge accepted-spans and gateway exporter metrics; verify the target observation identity and payload. Record any duplicate observations and reconcile them against the at-least-once contract.

Do **not** claim end-to-end losslessness from successful unit tests or an empty pending directory alone.
