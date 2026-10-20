# Claude Langfuse hook: durable delivery handoff (proposal)

Status: **design and fault-injection only**. The current hook is not proven lossless. No production changes in this proposal.

## Current state (upstream 1.2.1)

- The transcript is parsed incrementally; `SessionState.offset`, `open_turn`, `turn_progress` and `emitted_keys` are persisted in `langfuse_state.json`.
- `emit_new_turns_from_transcript` persists emission progress **before** `flush_and_shutdown_langfuse_client` runs in `main()`. SDK buffering/flush failure can permanently skip logical observations.
- `flush_and_shutdown_langfuse_client` uses a daemon thread and a five-second join, silently suppresses exceptions and returns without proving durable receiver acknowledgement.
- `save_hook_state` writes a temporary file then `os.replace` without file/directory fsync and suppresses exceptions, so a successful return does not prove durable state.
- Closed turns and transcript offsets are checkpointed, not just per-turn `emitted_keys`; replay must cover **all** state transitions.
- The available OTel edge collector uses a disk-backed queue. Its guarantees start only when events have been durably accepted, not when the hook has merely enqueued them in the SDK.

## Required contract

1. Any locally acknowledged event is either in a durable local spool or confirmed admitted by the collector under a documented durable ACK.
2. Checkpoint advancement is coupled to that handoff; no completed or partially completed turn becomes unreplayable after flush timeout, process kill, state write failure or restart.
3. Replay preserves logical trace, span and tool-use identity. Duplicates are acceptable only with explicitly verified destination behaviour.
4. A failed delivery or checkpoint is visible to operators and produces a retryable state, not a success-shaped return.
5. Hook execution remains bounded without sacrificing preservation: if synchronous delivery cannot be proven within the hook budget, persist locally before returning.
6. Concurrent sessions do not overwrite each other's pending states; atomic rename alone does not guarantee crash durability.

## Candidate strategies (selection pending)

### A. Commit only after synchronous flush

Smallest diff, but the SDK's `flush()` is not necessarily proof of receiver durable acceptance. A blocking flush may violate exit latency; timeout and failure still need replay. File-system checkpoint durability must be fixed. **Not sufficient without inspecting the exact SDK exporter and edge ACK semantics.**

### B. Local durable outbox + separate exporter (preferred hypothesis)

Persist canonical, stable-ID OTLP payloads (or immutable source transcript references plus a deterministic encoder version) to an append-only local spool before acknowledging hook completion. A separate uploader retries and advances durable delivery cursors only after an acknowledged receiver handoff. Keep the CLI hook fast and network-independent. Explicitly define spool ownership, disk-full admission policy, retention, concurrency, file locks, restart, compaction and updates. This adds components and therefore needs failure-injection evidence before adoption.

### C. Full transcript rescanning and idempotent re-emission

Use raw transcript as a local replay source; never consider a turn delivered merely because it was parsed. Feasible when transcripts are retained and complete, but requires deterministic observation IDs across restarts and a durable delivered-index. Transcript rotation/removal, asynchronous subagents, post-stop changes and backdated spans complicate correctness.

## Missing evidence to collect before implementation

- Whether pinned Langfuse SDK `flush()` reports exporter errors and what it actually acknowledges.
- Whether edge's OTLP receiver returns success after persistent enqueue and fsync; confirm in otelcol-otelbox v2.4.2 code, not by assuming `sending_queue.storage` implies transactional durability.
- Whether re-emitting the same trace/span IDs is idempotent in Langfuse 4.50 or produces duplicates.
- Whether every observation ID is stable when reprocessing a partially emitted turn.
- What happens on hook timeout, SIGKILL, terminal shutdown, missing/rotated transcript, disk full, and crash between rename and directory fsync.

## Test plan

The existing `test_langfuse_delivery_contract.py` records checkpoint-before-flush, swallowed flush exceptions, timed-out daemon flush and deterministic turn trace ID. `test_langfuse_durable_state_contract.py` adds disk state failure visibility and fsync evidence. Both suites keep known defects marked `xfail(strict=True)` until the implementation repairs them. A subsequent PR should add subprocess crash/restart tests with a fake OTLP receiver and test replay across session start/stop boundaries before removing the xfail markers.

## Boundary to setup_lab

`setup_lab` RFC 0001 separately owns gateway durable fan-out to SigNoz, ClickStack and Langfuse. A reliable hook handoff does not prove gateway fan-out, and gateway WALs cannot recover hook events that were never admitted.
