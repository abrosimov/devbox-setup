---
name: tla-plus
description: >
  TLA+ family toolchain: TLA+/PlusCal specs, TLC, Apalache (bounded and inductive), TLAPS,
  trace validation of an implementation against the spec. Use when deciding whether a design
  needs a formal model, encoding invariants, choosing a checker, triaging a counterexample, or
  when TLA+, TLC, Apalache, safety, liveness or refinement is mentioned.
problem: "Formal models get written as unverified prose or as specs nobody runs, with no record of which invariants a check actually covered and under which bounds."
related: [fpf-thinking, domain_modeller, formal_model_writer]
---

# TLA+ Toolchain

One paradigm, one notation. The machine carries the TLA+ family only; everything below targets what
`tasks/darwin/install_tlaplus.yml` installs under `~/.local/share/tlaplus/`:

| Tool | Location | Role |
|------|----------|------|
| `tla2tools.jar` | `$TLA2TOOLS_JAR` (env), `tla2tools/tla2tools.jar` | SANY parser, TLC model checker, PlusCal translator |
| CommunityModules | `communitymodules/CommunityModules-deps.jar` | `Json`, `IOUtils`, `SequencesExt`, `FiniteSetsExt`, `Functions`, `Folds` — needed for trace validation |
| Apalache | `apalache-mc` on PATH | Symbolic bounded checking, inductive invariants, type checking |
| TLAPS | `tlapm` on PATH | Proof manager for the one or two invariants worth a proof |

Java comes from the `temurin@21` cask. Alloy, P, Quint, SPIN and the like are out of scope: when one
of them would fit better, say so in the report and still deliver TLA+.

## Table of Contents

- [Step 0: Decide Whether to Model](#step-0-decide-whether-to-model)
- [Inputs a Model Needs](#inputs-a-model-needs)
- [Spec Shape](#spec-shape)
- [Choosing the Combination](#choosing-the-combination)
- [Running TLC](#running-tlc)
- [Running Apalache](#running-apalache)
- [Inductive Invariant Workflow](#inductive-invariant-workflow)
- [TLAPS](#tlaps)
- [Trace Validation](#trace-validation)
- [Counterexample Triage](#counterexample-triage)
- [Model Report](#model-report)
- [Pitfalls](#pitfalls)

---

## Step 0: Decide Whether to Model

Score the design. Model when any row scores **yes**; otherwise write a two-line refusal with the
reasons and stop.

| Signal | Yes when |
|--------|----------|
| Concurrency | Two or more actors update shared state without a single serialising lock |
| Distribution | State lives on more than one node, or messages can be lost, duplicated or reordered |
| Failure handling | Crash, restart or partial failure must leave an invariant intact |
| Multi-step protocol | A transaction, handshake, saga or workflow spans several messages or commits |
| Money or inventory under races | A quantity must never go negative or be double-spent |
| Non-trivial state machine | An aggregate has more than four states, or transitions depend on other aggregates |

A CRUD service with one database transaction per command and no cross-aggregate rule scores no row.
Say so; a model there costs more than it finds.

## Inputs a Model Needs

Read `domain_model.md` (invariants `INV-n`, commands with pre/postconditions, state machines) and
`domain_analysis.md` (constraints, invalidated assumptions). Build the coverage table before writing
TLA+:

| INV | Kind | Source statement | Spec property | Status |
|-----|------|------------------|---------------|--------|
| INV-1 | safety | "an order is never paid twice" | `NoDoublePayment` | covered |
| INV-3 | liveness | "every accepted order is eventually shipped" | — | **gap: fairness unknown** |

Every gap becomes a question in `model_requirements.md`, addressed to the agent that owns the
answer (domain-expert for business rules, domain-modeller for invariants and state machines,
architect for environment assumptions). The questions to ask, in this order:

1. **Safety** — what must never happen, as a predicate over the model's state.
2. **Liveness** — what must eventually happen, and under which fairness (weak or strong, per action).
3. **Environment** — which failures are in scope: crash-stop, crash-recovery, message loss,
   duplication, reordering, clock skew.
4. **Bounds** — how many actors, keys, retries and messages the small instance should have.

An invariant the model writer proposes from the model is marked `proposed` in the coverage table and
never reported as verified until the owning agent confirms it.

## Spec Shape

One abstract spec per subsystem, one model-checking module per instance:

```
formal_model/
  Orders.tla          \* the specification: EXTENDS, CONSTANTS, VARIABLES, Init, Next, Spec, properties
  MCOrders.tla        \* EXTENDS Orders; small-instance overrides, state constraint, symmetry
  MCOrders.cfg        \* TLC configuration for MCOrders
  MCOrders_apalache.cfg
  TraceOrders.tla     \* trace validation (see below), present when the implementation exists
  README.md           \* how to run every check, in copy-paste form
  model_report.md     \* results, see Model Report
```

Skeleton:

```tla
---- MODULE Orders ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Customers, MaxItems
ASSUME MaxItems \in Nat /\ MaxItems > 0

VARIABLES orders, payments
vars == <<orders, payments>>

TypeOK ==
    /\ orders \in [Customers -> Seq(1..MaxItems)]
    /\ payments \subseteq Customers

Init == orders = [c \in Customers |-> <<>>] /\ payments = {}

Pay(c) ==
    /\ c \notin payments
    /\ orders[c] /= <<>>
    /\ payments' = payments \cup {c}
    /\ UNCHANGED orders

Next == \E c \in Customers : Pay(c)

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

NoDoublePayment == \A c \in Customers : c \in payments => orders[c] /= <<>>
EventuallyPaid == \A c \in Customers : orders[c] /= <<>> ~> c \in payments
====
```

Rules that keep the spec checkable:

- `TypeOK` is the first invariant in every configuration; a type error found later is a wasted run.
- Every `VARIABLE` appears in `vars`; every action ends with `UNCHANGED` for what it leaves alone.
- Name actions after domain commands (`Pay`, `Ship`), properties after the invariant they encode
  (`NoDoublePayment` for INV-1). The report maps the two.
- Constants are model values or small sets; `MC*.tla` overrides them, the spec never hardcodes them.
- Fairness goes in `Spec` only when a liveness property needs it, and the report says which.

`MCOrders.cfg`:

```
SPECIFICATION Spec
CONSTANTS
    Customers = {c1, c2, c3}
    MaxItems = 2
SYMMETRY Perms           \* Perms == Permutations(Customers) in MCOrders.tla
CONSTRAINT StateConstraint
INVARIANTS TypeOK NoDoublePayment
PROPERTIES EventuallyPaid
CHECK_DEADLOCK TRUE
```

## Choosing the Combination

Pick by property kind and by the guarantee the stakeholder needs; record the choice and its reason
in the report's "Why this combination" section.

| Need | Tool | Why | What it does not give |
|------|------|-----|-----------------------|
| First feedback on safety and liveness | TLC on a small instance | Minutes to a counterexample, no annotations needed | Nothing beyond the instance's bounds |
| Liveness with fairness | TLC | The only checker here that handles `~>` and `[]<>` with fairness routinely | State-space blow-up on large instances |
| Safety where TLC blows up, or bounds beyond a handful | Apalache bounded check | Symbolic, bounds on steps rather than on state count | Only up to `--length` steps |
| Safety for every reachable state, no bound | Apalache inductive invariant | One-step check of `IndInv`; see workflow below | Finding `IndInv` is the work |
| A proof the organisation will cite | TLAPS on the inductive invariant | Machine-checked, independent of bounds | Expensive; do it for one or two invariants |
| Algorithm written as code with locks and loops | PlusCal, translated to TLA+ | Readable to engineers; translation is mechanical | Labels decide atomicity; easy to over-approximate |
| Abstract spec and detailed spec both exist | Refinement (`INSTANCE` + `Spec => A!Spec`) in TLC | Proves the detail keeps the abstract guarantees | Needs a refinement mapping |
| Implementation exists | Trace validation | Connects the model to the running code | Validates executions seen, not all executions |

Default ladder for a new model: TLC small instance → Apalache bounded with larger constants → inductive
invariant for the one safety property that matters most → trace validation once code exists. Stop
climbing when the next rung costs more than the residual risk; say that in the report.

## Running TLC

```bash
TLA_LIB="$HOME/.local/share/tlaplus"
CP="$TLA2TOOLS_JAR:$TLA_LIB/communitymodules/CommunityModules-deps.jar"

# Parse only (fast syntax and semantic check)
java -cp "$CP" tla2sany.SANY formal_model/Orders.tla

# PlusCal translation (writes the TLA+ block back into the file)
java -cp "$CP" pcal.trans formal_model/Algo.tla

# Model check (BFS, all cores, deadlock check on, no trace-explorer module)
java -XX:+UseParallelGC -Xmx4g -cp "$CP" tlc2.TLC \
    -config MCOrders.cfg -workers auto -noTE -cleanup formal_model/MCOrders.tla

# Random simulation when BFS is too big; depth and run count bounded
java -cp "$CP" tlc2.TLC -config MCOrders.cfg -simulate num=1000 -depth 50 formal_model/MCOrders.tla
```

Flags worth knowing: `-deadlock` turns deadlock checking off (use when the spec has a quiescent
state by design), `-coverage 1` prints action coverage every minute (an action with zero coverage is a
dead action or a modelling bug), `-dump dot,colorize out.dot` draws small state graphs,
`-lncheck final` defers liveness checking to the end, `-dfid N` runs iterative-deepening DFS for long
traces. TLC's exit code is non-zero on a violation; the counterexample is the numbered state trace on
stdout.

Record from every run: states generated, distinct states, depth, wall time, and the command line.

## Running Apalache

Annotate every `CONSTANT` and `VARIABLE` with a type comment, then:

```bash
apalache-mc typecheck formal_model/MCOrders.tla
apalache-mc check --config=formal_model/MCOrders_apalache.cfg --inv=NoDoublePayment --length=15 \
    --run-dir=formal_model/.apalache formal_model/MCOrders.tla
apalache-mc check --cinit=CInit --inv=NoDoublePayment --length=20 formal_model/MCOrders.tla
apalache-mc simulate --max-run=200 --length=30 --inv=NoDoublePayment formal_model/MCOrders.tla
apalache-mc check --temporal=EventuallyPaid --length=10 formal_model/MCOrders.tla   # temporal: slow, use TLC first
```

`CInit` is an operator that constrains constants symbolically (`Customers \in SUBSET {"c1","c2","c3"}`),
which is how Apalache checks many instances at once. Type annotations, the unsupported-construct
list and the `Apalache.tla` operators are in `references/apalache.md`.

## Inductive Invariant Workflow

An inductive invariant proves a safety property for every reachable state without a step bound.

1. Start with `IndInv == TypeOK /\ Safety`.
2. Base: `apalache-mc check --init=Init --inv=IndInv --length=0 MC.tla`.
3. Step: `apalache-mc check --init=IndInv --inv=IndInv --length=1 MC.tla`.
4. A step counterexample starts from a state satisfying `IndInv` that is **not reachable**: add a
   conjunct to `IndInv` that excludes it (a relation between variables the spec maintains), rerun 2–3.
5. Implication: `apalache-mc check --init=IndInv --inv=Safety --length=0 MC.tla` (trivial when
   `Safety` is a conjunct; still run it).
6. Confirm with TLC on the small instance that `IndInv` holds as an ordinary invariant, which catches
   a conjunct too strong to be true.

Typically three to six strengthening rounds. Report each conjunct and the counterexample that forced it.

## TLAPS

Prove only an invariant whose inductive form already passed Apalache; the proof is then mostly
bookkeeping.

```tla
THEOREM Safe == Spec => []NoDoublePayment
<1>1. Init => IndInv                      BY DEF Init, IndInv, TypeOK, NoDoublePayment
<1>2. IndInv /\ [Next]_vars => IndInv'    BY DEF IndInv, TypeOK, NoDoublePayment, Next, Pay, vars
<1>3. IndInv => NoDoublePayment           BY DEF IndInv
<1>. QED                                  BY <1>1, <1>2, <1>3, PTL DEF Spec
```

Run `tlapm formal_model/Orders.tla`; an obligation the backends (SMT, Zenon, Isabelle) cannot
discharge is split into `<2>` steps. `PTL` is the temporal backend for the final step. The nvim
setup speaks to `tlapm_lsp` for inline obligation status.

## Trace Validation

Checks that executions of the real implementation are behaviours of the spec. Full pattern, event
schema and Go-side contract in `references/trace-validation.md`. The shape:

A "trace" here is a behaviour log for TLC, not a distributed trace: it is not an OpenTelemetry span,
never goes through the telemetry pipeline, and has nothing to do with the observability work. The
formal-model-writer owns all of it, emitter included.

1. **Trace contract** (`trace_contract.md`): one row per spec action — action name, the code point
   that performs it, the arguments the log line carries, and which variables the line snapshots.
   The formal-model-writer writes the emitter from this contract (or hands the contract to the SE
   when the code point sits in code under active change) and owns the trace spec.
2. **Emitter**: the implementation writes NDJSON, one line per abstract action, in commit order.
3. **Trace spec** `TraceOrders.tla` extends the spec, reads the file with `Json!ndJsonDeserialize`,
   and defines `TraceNext` so that line `l` can only be matched by the spec action it names; missing
   arguments are existentially chosen, so TLC explores every spec step consistent with the line.
4. **Acceptance**: `POSTCONDITION TraceAccepted` in the cfg, where `TraceAccepted` holds when TLC
   consumed every line. A rejected trace comes with the first line the spec could not match.

Validation is evidence about executions seen, never a proof; the report says how many traces, from
which scenarios (happy path, each failure injected), and which actions the traces never exercised.

## Counterexample Triage

Every counterexample is classified before anything is changed, with the evidence that supports the
class:

| Class | Evidence | Action |
|-------|----------|--------|
| Spec error | The trace takes a step the real design forbids (missing guard, wrong `UNCHANGED`) | Fix the spec, rerun, note it in the report |
| Abstraction too coarse | The step is possible in the model only because a detail was abstracted away | Refine the model for that detail; record the abstraction |
| Environment assumption too strong or too weak | The failure needs a fault the owners ruled out, or the model allows one they did not | Question to the architect in `model_requirements.md` |
| Design flaw | The trace is a legal execution of the design as described | Blocker to domain-modeller and architect, written as a domain-language narrative of the trace |

A design flaw is reported as a story ("customer c1 pays, the payment service restarts before the
ack, the retry pays again"), the trace states as an appendix. Never quietly weaken a property to make
a run pass.

## Model Report

`model_report.md`, in this order:

1. **Decision** — modelled or not, and the Step 0 rows that decided it.
2. **Why this combination** — the rows of the combination table used, the rung where climbing stopped
   and why.
3. **Coverage** — the INV table with status: `covered (TLC, bound)`, `covered (Apalache, length N)`,
   `proved (inductive)`, `proposed`, `gap`.
4. **Runs** — one row per run: command, instance, states or length, time, outcome.
5. **Counterexamples** — each with its triage class and what happened to it.
6. **Assumptions and bounds** — environment faults in scope, fairness, instance sizes.
7. **Not covered** — properties outside the bounds or the tools, with the reason.
8. **Trace validation** — traces checked, scenarios, actions never exercised.

Numbers in the report are copied from tool output, never estimated.

## Pitfalls

- A property that passes on an instance of size 1 or 2 has usually not been tested: use at least
  three actors where the invariant is about interaction.
- `SYMMETRY` with liveness checking is unsound in TLC; drop symmetry when `PROPERTIES` is set.
- A state constraint cuts the state space and also the behaviours; liveness results under a
  `CONSTRAINT` are advisory only.
- `CHOOSE` is deterministic: it never models a non-deterministic choice; use `\E`.
- Stuttering: `[][Next]_vars` allows doing nothing forever, so a liveness property needs fairness.
- Unbounded `Seq(S)` and `Nat` in `TypeOK` make TLC enumerate forever; bound them in the `MC` module.
- Apalache ignores `ASSUME` and needs every operator it evaluates to be typed; a passing TLC run says
  nothing about Apalache's type check.
- Trace validation that matches on action names only, without arguments, accepts almost anything;
  carry the identifying arguments.
