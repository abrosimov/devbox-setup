---
name: tla-plus
description: >
  TLA+ toolchain: TLA+/PlusCal specs, TLC, Apalache, TLAPS, trace validation. Use when deciding
  whether a design needs a formal model, encoding invariants, choosing a checker, triaging a
  counterexample, or when safety, liveness, refinement or model checking is mentioned.
problem: "Formal models get written as prose or as specs nobody runs, with no record of which invariants a check covered and under which bounds."
related: [fpf-thinking, domain_modeller, formal_model_writer]
---

# TLA+ Toolchain

Installed under `~/.local/share/tlaplus/<tool>/` (Java from `temurin@21`): `tla2tools.jar`
(`$TLA2TOOLS_JAR`: SANY, TLC, PlusCal), `communitymodules/CommunityModules-deps.jar` (`Json`,
`IOUtils`), `apalache-mc`, `tlapm`. Nothing else: when Alloy, P, Quint or SPIN would fit better,
say so in the report and still deliver TLA+.

Runnable reference: `examples/orders/` — spec, two TLC configurations, Apalache entry module,
trace spec with fixtures, and a README whose commands are the verification. Copy the directory
and rename; do not retype the shape.

## 1. Decide whether to model

Model when any row scores yes; otherwise write a two-line refusal with the reasons and stop.

| Signal | Yes when |
|--------|----------|
| Concurrency | Two or more actors update shared state without one serialising lock |
| Distribution | State lives on more than one node, or messages can be lost, duplicated, reordered |
| Failure handling | Crash, restart or partial failure must leave an invariant intact |
| Multi-step protocol | A transaction, handshake, saga or workflow spans several messages or commits |
| Money or inventory under races | A quantity must never go negative or be double-spent |
| Non-trivial state machine | More than four states, or transitions that depend on other aggregates |

## 2. Inputs and the link to prose

Read `domain_model.md` (invariants `INV-n`, commands with pre/postconditions, state machines) and
`domain_analysis.md` (constraints, invalidated assumptions). Each property in the spec is tied to
the note that states its invariant by a kadmos code anchor on the line above it
(`standards/code-anchors.md` of the project's vault, present when the repository root has
`.vault-root`):

```tla
\* ariadne-kadmou[orders-paid-implies-ordered|evidences|kadmos://oikos/invariants/INV-00001-paid-implies-ordered.md#Statement]
PaidImpliesOrdered == \A c \in Customers : c \in payments => orders[c] /= <<>>
```

- Slug: lowercase kebab-case, unique in the repository, prefixed with the spec name. Relation:
  `evidences` for a spec property, `tests` for a property-based or trace test, `implements` for
  code. Reference: the `kadmos://oikos/<path>.md#<heading>` of the note; read the vault for it,
  never invent a path.
- If the note carries `anchored_by`, add the slug (the field is exact when present).
- The coverage table (`INV`, kind, slug, property, status) is the scan of these anchors. Without
  a vault it is written by hand with `INV-n` ids and the report says so in its first line.

Every gap is a question in `model_requirements.md` addressed to its owner: business meaning to
the domain-expert, missing invariants and transitions to the domain-modeller, environment faults
and fairness to the architect. Ask, in order: safety (what never happens), liveness (what
eventually happens, under which fairness), environment (crash-stop, crash-recovery, loss,
duplication, reordering, clock skew), bounds (actors, keys, retries, messages). Continue with the
answer the model assumes, marked `proposed`; a `proposed` property is never reported as verified.

## 3. Spec rules

- `TypeOK` is the first invariant in every configuration. Write it so both TLC and Apalache
  evaluate it: no `\in Seq(S)`; bound sequences by `Len` and element membership.
- Every variable is in `vars`; every action ends with `UNCHANGED` for what it leaves alone.
- Actions are named after domain commands, properties after the invariant they encode. A name
  that promises more than the predicate says (`NoDoublePayment` over a set) is a defect.
- Constants are assigned by the `.cfg` (TLC) or `CInit` (Apalache); the spec never hardcodes them.
- Fairness only where a liveness property needs it, per action (`WF_vars(Ship(c))`), and the
  report says which.
- No `CONSTRAINT` the guards already imply; liveness under a `CONSTRAINT` is advisory only.

## 4. Choose the checker

| Need | Tool | Gives | Does not give |
|------|------|-------|---------------|
| First feedback on safety and liveness | TLC, small instance | Counterexample in minutes | Anything beyond the instance |
| Liveness with fairness | TLC | `~>`, `[]<>` with WF/SF | Large instances |
| Safety beyond a handful of constants | Apalache bounded (`--length`, `CInit`) | A constant family per run | Beyond `--length` steps |
| Safety for every reachable state | Apalache inductive invariant | No step bound | Finding the invariant is the work |
| A citable proof | TLAPS on the inductive invariant | Machine-checked | Expensive; one or two invariants |
| Algorithm with loops and locks | PlusCal, translated | Readable to engineers | Coarse labels hide interleavings |
| Abstract and detailed spec | Refinement (`INSTANCE`, `Spec => A!Spec`) in TLC | Detail keeps the guarantees | Needs a mapping |
| Implementation exists | Trace validation (§8) | Model meets the code | Only executions seen |

Ladder: TLC small instance → Apalache bounded with `CInit` → inductive invariant for the safety
property the owners rank first → trace validation once code exists; TLAPS only on request.
Budgets: a TLC run stops at thirty minutes or fifty million distinct states and reports the
partial result; inductive strengthening stops after six rounds. Record every run's command,
instance, distinct states or length, time and outcome as the tool printed them.

## 5. Run

```bash
CP="$TLA2TOOLS_JAR:$HOME/.local/share/tlaplus/communitymodules/CommunityModules-deps.jar"
java -cp "$CP" tla2sany.SANY Orders.tla                                     # parse
java -cp "$CP" pcal.trans Algo.tla                                          # PlusCal → TLA+
java -XX:+UseParallelGC -cp "$CP" tlc2.TLC -config MCOrders.cfg -workers auto -noTE -cleanup MCOrders.tla
java -cp "$CP" tlc2.TLC -config MCOrders.cfg -simulate num=1000 -depth 50 MCOrders.tla   # when BFS is too big
apalache-mc typecheck ApaOrders.tla
apalache-mc check --cinit=CInit --inv=PaidImpliesOrdered --length=8 --out-dir="$(mktemp -d)" ApaOrders.tla
tlapm Orders.tla
```

`.cfg` keys: `SPECIFICATION`, `CONSTANTS` (model values or sets), `INVARIANTS`, `PROPERTIES`,
`SYMMETRY` (never together with `PROPERTIES`: unsound), `CHECK_DEADLOCK`, `POSTCONDITION`. TLC
flags: `-deadlock` turns deadlock checking off, `-coverage 1` prints action coverage (zero
coverage is a dead action), `-dump dot out.dot` draws small graphs. A TLAPS proof is the standard
`Init => Inv`, `Inv /\ [Next]_vars => Inv'`, `Inv => Safety`, `QED BY ..., PTL DEF Spec` with
`EXTENDS TLAPS`; prove only an invariant Apalache already found inductive.

## 6. Apalache specifics

Annotate every `CONSTANT` and `VARIABLE` on the line before it (`\* @type: Set(Str);`); types are
`Int`, `Bool`, `Str`, `Set(T)`, `Seq(T)`, `A -> B`, `<<A, B>>`, `{ f: Int }`, operators
`(Int, Str) => Bool`. Operators are inferred; annotate one only when `typecheck` asks. Model
values from a `.cfg` are strings. `CInit` constrains constants symbolically
(`Customers \in SUBSET {"c1","c2","c3"}`), which is how one run covers a family.

| Construct | Apalache | Use instead |
|-----------|----------|-------------|
| `a..b` with a bound that is not a literal (a `CInit` constant fixed by `\in`) | unsupported | fix that constant with `=` in `CInit` |
| `--init=P` where `P` does not assign every variable with `=` or `\in` | fails | an `ApaTypeOK` written with `=`, `\in`, `Gen(n)` (see `examples/orders/ApaOrders.tla`) |
| `CHOOSE` | unsupported | `Guess(S)` when any element will do; folds for a deterministic pick |
| `RECURSIVE`, recursive functions | unsupported | `ApaFoldSet`, `ApaFoldSeqLeft` |
| `Seq(S)` as a set, quantification over `Nat`, `Int`, `Seq(S)` | unsupported | `Gen(n)` with a length bound; ranges |
| `Reals`, string operations beyond `=`, `ENABLED`, `TLCGet`, `Permutations` | unsupported | integers scaled; model values; TLC |
| `SYMMETRY`, `CONSTRAINT`, `POSTCONDITION` in `.cfg` | ignored | nothing (bounded steps) |
| `ASSUME` | unreliable | put every constant constraint in `CInit` |
| Temporal properties (`--temporal`) | no fairness | TLC for anything that needs WF/SF |

Output goes to `_apalache-out/` or `--out-dir`: `violation<N>.tla` and `violation<N>.itf.json`.
ITF is untagged JSON; `proto/apalache/itf/v1/itf.proto` is the typed contract a converter maps it
onto, with conformance vectors next to it.

## 7. Inductive invariant

1. `IndInv == TypeOK /\ Safety`, in the Apalache-assignable form of §6.
2. Base: `--init=Init --inv=IndInv --length=0`. Step: `--init=IndInv --inv=IndInv --length=1`.
3. A step counterexample starts from an unreachable state: add the conjunct the spec maintains
   that excludes it, rerun.
4. `--init=IndInv --inv=Safety --length=0`, then TLC on the small instance with `IndInv` as an
   ordinary invariant (catches a conjunct too strong to be true).

## 8. Trace validation

A behaviour log of the implementation replayed against the spec by TLC. It is a verification
fixture: not an OpenTelemetry trace, never the service logger or the telemetry pipeline.

- **Schema**: a protobuf `Event` with a `oneof action`, one member per spec action and its
  arguments, an optional state snapshot (`examples/orders/proto/orders/trace/v1/trace.proto`).
  On disk one protojson object per line, because the `Json` module reads it. protojson: field
  names lowerCamelCase; scalars and repeated fields at their default are omitted (ids start at 1;
  guard snapshot fields with `\in DOMAIN`); a set message is written as `{}`; 64-bit integers
  become strings, so anything TLC compares is 32-bit. `buf lint` always; `buf breaking` before a
  change lands.
- **Contract** `trace_contract.md`: one row per action — `oneof` member, spec action, arguments,
  code point, emitted when (at the commit point, never before) — plus abstraction rules. The SE
  writes the emitter from it: own package, off by default, enabled by `TRACE_PATH`.
- **Trace spec** (`TraceOrders.tla`): `IsEvent(name) == l <= Len(Trace) /\ name \in DOMAIN
  logline /\ l' = l + 1`; an argument on the line fixes the step, a missing one is chosen with
  `\E`; `POSTCONDITION TraceAccepted` with `TLCGet("stats").diameter = Len(Trace) + 1`;
  `CHECK_DEADLOCK FALSE`. A rejected trace names the first unmatched line.
- **Scenarios**: happy path single and concurrent (three actors), each admitted failure injected
  once, restart. Report accepted, rejected, and actions never exercised.

| Artefact | In git | Edited |
|----------|--------|--------|
| schema, contract, trace spec, `.cfg`, labelled fixtures in `traces/` | yes | yes |
| harness recordings, counterexamples | no (`.runs/`, `_apalache-out/`) | never |
| a recording or counterexample attached to a finding | yes, next to the report, with scenario, commit, date | never |

## 9. Counterexample triage

| Class | Evidence | Action |
|-------|----------|--------|
| Spec error | The step is forbidden by the real design (missing guard, wrong `UNCHANGED`) | Fix the spec, rerun, note it |
| Abstraction too coarse | Possible only because a detail was abstracted away | Refine for that detail, record it |
| Environment assumption | Needs a fault the owners ruled out, or one they did not | Question to the architect |
| Design flaw | A legal execution of the design as described | Blocker to domain-modeller and architect as a story, trace as appendix |

Never weaken a property to make a run pass; never edit tool output.

## 10. Report

`model_report.md`: decision (§1 rows), why this combination and where the ladder stopped,
coverage table, runs, counterexamples with class, assumptions and bounds, not covered, trace
validation. Every number is copied from tool output.

## Sources

- Lamport, *Specifying Systems* — https://lamport.azurewebsites.net/tla/book.html ; PlusCal
  manual — https://lamport.azurewebsites.net/tla/p-manual.pdf
- Hillel Wayne, *Practical TLA+*; TLA+ Examples — https://github.com/tlaplus/Examples
- TLC options and trace validation — https://docs.tlapl.us ; Cirstea, Kuppe, Loillier, Merz,
  *Validating Traces of Distributed Programs Against TLA+ Specifications* (2024) —
  https://arxiv.org/abs/2404.16075
- Apalache manual and ADR-015 (ITF) — https://apalache-mc.org/docs/ ; TLAPS — https://proofs.tlapl.us
- kadmos `standards/code-anchors.md`, `standards/cross-instance-references.md`
