# Trace Validation

Trace validation checks that an execution of the implementation is a behaviour of the specification.
The implementation logs one line per abstract action; a trace specification replays the log against
the spec with TLC. The pattern follows Cirstea, Kuppe, Loillier and Merz, "Validating Traces of
Distributed Programs Against TLA+ Specifications" (2024), adapted to Go services.

It is evidence, not proof: a validated trace says the executions seen were legal, nothing about the
ones not seen. The report always names the scenarios that produced the traces.

Terminology: this trace is a behaviour log consumed by TLC. It is not an OpenTelemetry trace, it is
not emitted through the service's logger or the telemetry pipeline, and it is not an observability
concern; it is a verification fixture owned by the formal-model-writer.

## Roles

| Artefact | Owner | Content |
|----------|-------|---------|
| `trace_contract.md` | formal-model-writer | Action ↔ code point table, event schema, abstraction rules |
| Emitter in the service | formal-model-writer (the SE on the task when the code point is under active change) | Small NDJSON writer behind a build tag or env flag, following the contract |
| `Trace<Spec>.tla`, `Trace<Spec>.cfg` | formal-model-writer | Trace spec and TLC configuration |
| Scenario harness | integration-tests-writer or SE | Runs the system under each scenario, collects trace files |

## Trace Contract

```markdown
# Trace contract: Orders

## Event schema (NDJSON, one object per line, commit order)
| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `event` | string | yes | Spec action name, exact case |
| `args` | object | yes | Action arguments at the spec's abstraction |
| `state` | object | no | Snapshot of spec variables after the step, when cheap |
| `node` | string | distributed only | Emitting process |
| `seq` | int | yes | Per-node sequence number |

## Actions
| Spec action | Args carried | Code point | Emitted when |
|-------------|--------------|------------|--------------|
| `Pay(c)` | `c` | `payments.Service.Pay`, after `tx.Commit()` | commit succeeded |
| `Ship(c)` | `c` | `shipping.Worker.handle` | message acked |
| `Crash(n)` | `n` | process exit hook | always, best effort |

## Abstraction rules
- Customer ids map 1:1 to spec model values (`"c1"`).
- Amounts in minor units as integers.
- Retries that do not change state emit nothing.
```

Rules for the emitter:

- Emit at the **commit point** of the abstract step (after the transaction commits or the message is
  acknowledged), never before; an emitted step that then fails is a false trace.
- Off by default; enabled by an environment variable naming the file (`TRACE_PATH`). Each line is
  written and flushed atomically (`encoding/json` into a buffered writer, `Flush` per line).
- A dedicated writer in its own package (`internal/tlatrace` or similar), not the service logger and
  not an OTel exporter: the file format, ordering and lifetime are the spec's, not the telemetry
  stack's.
- Carry the arguments that identify the step. Action names alone make the validation accept nearly
  anything.
- Distributed services: one file per node with `node` and `seq`; merge into one global file by a
  commit log where one exists (database, broker partition), otherwise by vector clocks
  (`VectorClocks` module in CommunityModules). The merge order is one possible order; the trace spec
  may keep sibling events unordered by matching any permutation of a concurrent block.

## Trace Specification

```tla
---- MODULE TraceOrders ----
EXTENDS Orders, Json, IOUtils, Sequences, TLC

\* NDJSON file named by the TRACE_PATH environment variable
Trace == ndJsonDeserialize(IOEnv.TRACE_PATH)

VARIABLE l                       \* index of the next log line to consume
tvars == <<vars, l>>

logline == Trace[l]

IsEvent(name) ==
    /\ l <= Len(Trace)
    /\ logline.event = name
    /\ l' = l + 1

\* Arguments present on the line are fixed; absent ones are chosen existentially
TracePay ==
    /\ IsEvent("Pay")
    /\ Pay(logline.args.c)

TraceShip ==
    /\ IsEvent("Ship")
    /\ \E c \in Customers : c = logline.args.c /\ Ship(c)

\* Optional snapshot check when the line carries state
SnapshotOK ==
    "state" \in DOMAIN logline => payments' = logline.state.payments

TraceInit == Init /\ l = 1

TraceNext ==
    /\ \/ TracePay
       \/ TraceShip
    /\ SnapshotOK

TraceSpec == TraceInit /\ [][TraceNext]_tvars

\* TLC consumed every line: the diameter of the explored graph is the trace length plus the initial state
TraceAccepted == TLCGet("stats").diameter = Len(Trace) + 1
====
```

`TraceOrders.cfg`:

```
SPECIFICATION TraceSpec
CONSTANTS
    Customers = {"c1", "c2", "c3"}
    MaxItems = 2
INVARIANTS TypeOK NoDoublePayment
POSTCONDITION TraceAccepted
CHECK_DEADLOCK FALSE
```

Deadlock checking is off because the spec legitimately has no enabled action once the log is
consumed. Constants are strings here, matching the JSON; keep model values and JSON ids aligned in
the contract.

## Running

```bash
TLA_LIB="$HOME/.local/share/tlaplus"
CP="$TLA2TOOLS_JAR:$TLA_LIB/communitymodules/CommunityModules-deps.jar"

TRACE_PATH=traces/happy-path.ndjson java -cp "$CP" tlc2.TLC \
    -config TraceOrders.cfg -workers auto -noTE formal_model/TraceOrders.tla
```

Outcomes:

| TLC output | Meaning | Next |
|------------|---------|------|
| exit 0, postcondition holds | trace accepted | record scenario as validated |
| invariant violated at state k | the implementation reached a state the spec forbids | design or implementation bug; triage as a counterexample |
| postcondition fails, graph diameter d | line `d` could not be matched by any spec action | compare line `d` against the enabled actions at state `d`; usually an emitter at the wrong point, a missing action, or a real divergence |

When several spec steps match one line (existential arguments), TLC explores all of them; a blow-up
means the line needs more identifying arguments or a `state` snapshot. For traces of thousands of
lines prefer `-dfid` or split the file by scenario.

## Scenarios

Minimum set per subsystem, each as its own trace file:

1. Happy path, single actor.
2. Happy path, concurrent actors (at least three).
3. Each failure the model's environment admits, injected once: process crash before and after the
   commit point, message loss, duplicate delivery, reordering.
4. Restart and recovery.

Run TLC with `-coverage 1` on each and collect the action counts; an action with zero coverage across
all scenarios is reported as "never exercised".
