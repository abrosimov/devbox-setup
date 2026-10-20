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
| `proto/<spec>/trace/v1/trace.proto` | formal-model-writer | The schema: `Event` with a `oneof action`, one member per spec action, optional snapshot |
| `trace_contract.md` | formal-model-writer | Action ↔ code point table, abstraction rules, what the snapshot carries |
| Emitter in the service | formal-model-writer (the SE on the task when the code point is under active change) | Generated types + `protojson.Marshal`, one line per step, behind an env flag, its own package |
| `Trace<Spec>.tla`, `Trace<Spec>.cfg` | formal-model-writer | Trace spec and TLC configuration |
| `traces/*.jsonl` fixtures | formal-model-writer | Hand-written lines that exercise the trace spec; labelled as fixtures |
| Scenario harness, `.runs/` | integration-tests-writer or SE | Runs the system under each scenario, records traces; gitignored |

## Schema

The schema is protobuf because a structured record needs a contract that tools can check for
compatibility, and the encoding is a separate choice. protojson is the encoding here because the
TLA+ `Json` module reads it; nothing else about the pipeline depends on JSON.

```proto
message Event {
  oneof action {              // the member name is the key TLC sees: "place", "pay", "ship"
    Place place = 1;
    Pay pay = 2;
    Ship ship = 3;
  }
  Snapshot state = 10;        // optional; narrows the match
  string node = 11;           // distributed deployments only
  uint32 seq = 12;            // per-node sequence number
}
message Pay { string c = 1; }
message Snapshot { repeated string payments = 1; repeated string shipped = 2; }
```

Rules that follow from protojson, and that the trace spec relies on:

- Field names appear in lowerCamelCase; the trace spec uses those names (`logline.pay.c`).
- A field at its default value is omitted. An id, an item number or an amount that carries meaning
  is never `0` or `""`; the spec's constants start at 1 for that reason.
- `int64`, `uint64` and `sint64` serialise as JSON strings; anything TLC compares as a number is
  32-bit.
- Repeated fields that are empty are omitted; the trace spec guards each snapshot field with
  `"payments" \in DOMAIN logline.state`.
- Enums serialise as their names; the spec matches the string.

`buf lint` on every change; `buf breaking --against <base>` before a schema change lands, because
the emitter and the trace spec are two consumers of one contract and either can silently diverge.

## Trace Contract

```markdown
# Trace contract: Orders

Schema: proto/orders/trace/v1/trace.proto (orders.trace.v1.Event), protojson, one object per line,
commit order.

## Actions
| oneof member | Spec action | Args carried | Code point | Emitted when |
|--------------|-------------|--------------|------------|--------------|
| `place` | `Place(c, i)` | `c`, `item` | `orders.Service.Place`, after `tx.Commit()` | commit succeeded |
| `pay` | `Pay(c)` | `c` | `payments.Service.Pay`, after `tx.Commit()` | commit succeeded |
| `ship` | `Ship(c)` | `c` | `shipping.Worker.handle` | message acked |

## Snapshot
`state.payments`, `state.shipped` after the step, when the service can read them cheaply.

## Abstraction rules
- Customer ids map 1:1 to the spec's string constants (`"c1"`).
- Items are 1-based integers (`Items == 1..MaxItems`).
- Retries that do not change state emit nothing.
```

Rules for the emitter:

- Emit at the **commit point** of the abstract step (after the transaction commits or the message is
  acknowledged), never before; an emitted step that then fails is a false trace.
- Off by default; enabled by an environment variable naming the file (`TRACE_PATH`). Each line is
  `protojson.Marshal` of one `Event`, written and flushed atomically.
- A dedicated writer in its own package (`internal/tlatrace` or similar), not the service logger and
  not an OTel exporter: the file format, ordering and lifetime are the spec's, not the telemetry
  stack's.
- Carry the arguments that identify the step. Action names alone make the validation accept nearly
  anything.
- Distributed services: one file per node with `node` and `seq`; merge into one global file by a
  commit log where one exists (database, broker partition), otherwise by vector clocks
  (`VectorClocks` module in CommunityModules). The merge order is one possible order; the trace spec
  may keep sibling events unordered by matching any permutation of a concurrent block.

## What Goes to Git

| Artefact | In git | Edited by hand | Why |
|----------|--------|----------------|-----|
| `trace.proto`, `trace_contract.md`, `Trace<Spec>.tla`, `.cfg` | yes | yes | the contract |
| `traces/*.jsonl` fixtures | yes | yes, labelled as fixtures | they test the trace spec, not the system |
| Recordings from the harness | no (`.runs/`) | never | regenerated by the test that needs them |
| A recording attached to a finding | yes, next to the report | never | evidence, with scenario, commit and date in the report |
| Counterexamples (TLC trace, Apalache `*.itf.json`) | no (`.runs/`) | never | tool output; quoted by the report |
| A counterexample attached to a design-flaw finding | yes, next to the report | never | evidence |

## Trace Specification

The full module is `examples/orders/TraceOrders.tla` with `TraceOrders.cfg` and two traces under
`examples/orders/traces/`. The parts that carry the pattern:

```tla
Trace == ndJsonDeserialize(IOEnv.TRACE_PATH)          \* Json + IOUtils from CommunityModules
VARIABLE l                                            \* next line to consume
IsEvent(name) == l <= Len(Trace) /\ Trace[l].event = name /\ l' = l + 1
TracePay  == IsEvent("Pay") /\ Pay(Trace[l].args.c)   \* argument on the line fixes the step
TraceShip == IsEvent("Ship") /\ \E c \in Customers : c = Trace[l].args.c /\ Ship(c)
TraceNext == (TracePlace \/ TracePay \/ TraceShip) /\ SnapshotOK
TraceAccepted == TLCGet("stats").diameter = Len(Trace) + 1
```

`TraceOrders.cfg` sets `SPECIFICATION TraceSpec`, keeps the safety `INVARIANTS`, adds
`POSTCONDITION TraceAccepted` and `CHECK_DEADLOCK FALSE` (the spec legitimately stops once the log is
consumed). Constants are strings there, matching the JSON ids; the contract keeps model values and
JSON ids aligned. JSON arrays deserialise as sequences, so a snapshot of a set variable goes through
`AsSet`.

## Running

```bash
TLA_LIB="$HOME/.local/share/tlaplus"
CP="$TLA2TOOLS_JAR:$TLA_LIB/communitymodules/CommunityModules-deps.jar"

TRACE_PATH=traces/happy-path.jsonl java -cp "$CP" tlc2.TLC \
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

Source: Cirstea, Kuppe, Loillier, Merz, *Validating Traces of Distributed Programs Against TLA+
Specifications*, https://arxiv.org/abs/2404.16075; TLC docs, https://docs.tlapl.us/using:tlc:trace_validation.
