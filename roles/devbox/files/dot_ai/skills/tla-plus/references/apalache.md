# Apalache Reference

Pinned by `devbox_packages.tlaplus.tools` (`apalache-mc`, release `v0.62.x`). Apalache checks TLA+
symbolically: it encodes `--length` steps of `Next` as SMT constraints, so the cost grows with the
number of steps and the complexity of the actions, not with the number of reachable states.

## Type Annotations

Every `CONSTANT`, `VARIABLE` and every operator Apalache has to evaluate from a comment-free context
carries a type comment on the line before it. Missing annotations are the first and most common
failure; run `apalache-mc typecheck` before any `check`.

```tla
CONSTANTS
    \* @type: Set(Str);
    Customers,
    \* @type: Int;
    MaxItems

VARIABLES
    \* @type: Str -> Seq(Int);
    orders,
    \* @type: Set(Str);
    payments

\* @type: (Str, Int) => Bool;
Pay(c, amount) == ...
```

Type grammar:

| Type | Written as |
|------|-----------|
| Integer, Boolean, string | `Int`, `Bool`, `Str` |
| Set, sequence | `Set(Int)`, `Seq(Str)` |
| Function | `Int -> Str` |
| Tuple | `<<Int, Str>>` |
| Record | `{ id: Int, status: Str }` |
| Operator | `(Int, Str) => Bool` |
| Alias | `\* @typeAlias: order = { id: Int, status: Str };` then `$order` |
| Variant (tagged union) | `A(Int) \| B(Str)`, with the `Variants` module operators |

Model values from a TLC `.cfg` (`Customers = {c1, c2}`) become strings for Apalache; annotate the
constant as `Set(Str)`.

## Commands

```bash
apalache-mc typecheck MC.tla
apalache-mc check --inv=Inv1,Inv2 --length=10 MC.tla              # bounded safety, default length 10
apalache-mc check --config=MC.cfg --inv=Inv MC.tla                 # TLC cfg syntax: SPECIFICATION/INIT/NEXT/CONSTANT
apalache-mc check --init=Init --next=Next --cinit=CInit --inv=Inv MC.tla
apalache-mc check --init=IndInv --inv=IndInv --length=1 MC.tla     # inductive step
apalache-mc check --init=Init --inv=IndInv --length=0 MC.tla       # inductive base
apalache-mc check --temporal=Live --length=8 MC.tla                # temporal property, loop encoding; slow
apalache-mc check --max-error=5 --view=View --inv=Inv MC.tla       # several distinct counterexamples
apalache-mc simulate --max-run=100 --length=30 --inv=Inv MC.tla    # random symbolic runs
apalache-mc check --run-dir=.apalache/run1 --inv=Inv MC.tla        # keep logs and counterexamples here
```

Output on a violation: `counterexample1.tla` (a TLA+ module replaying the states), `violation1.tla`,
and `counterexample1.itf.json` (machine-readable, for diff tooling). The exit code is non-zero.

`CInit` constrains constants instead of fixing them:

```tla
\* @type: Bool;
CInit ==
    /\ Customers \in SUBSET {"c1", "c2", "c3", "c4"}
    /\ Customers /= {}
    /\ MaxItems \in 1..3
```

One run then covers every instance in that family, which is the main reason to prefer Apalache over
TLC for the "larger constants" rung.

## The `Apalache` Module

`EXTENDS Apalache` gives operators the symbolic encoding needs in place of constructs it cannot
encode:

| Operator | Replaces | Note |
|----------|----------|------|
| `ApaFoldSet(Op, base, S)` | recursive operator over a set | `Op(acc, x)` |
| `ApaFoldSeqLeft(Op, base, seq)` | recursive operator over a sequence | left fold |
| `Gen(n)` | `Seq(S)` as a type set | a sequence of up to `n` elements, unconstrained |
| `SetAsFun(S)` | `CHOOSE f \in [..] : ...` | set of pairs to function |
| `FunAsSeq(f, len, cap)`, `MkSeq(n, F)` | sequence construction | explicit bounds |
| `x' := e` | `x' = e` | tells the encoder this is an assignment, not a constraint |
| `Guess(S)` | `CHOOSE x \in S : TRUE` | explicitly non-deterministic pick |
| `Skolem(\E x \in S : P)` | `\E` | hints the solver; use when a quantifier is slow |

## Unsupported or Restricted

| Construct | Status | Use instead |
|-----------|--------|-------------|
| Quantification over `Nat`, `Int`, `STRING`, `Seq(S)` | unsupported | bounded ranges; `Gen` |
| `RECURSIVE` operators, recursive functions | unsupported | `ApaFoldSet`, `ApaFoldSeqLeft` |
| `Seq(S)` as a set in `TypeOK` or `\in` | unsupported | `Gen(n)` and an explicit length bound |
| `Reals`, real arithmetic | unsupported | integers scaled by a factor |
| `CHOOSE x \in S : P` | restricted | `Guess`, or `\E` when any choice is acceptable |
| String operations beyond equality | unsupported | model values |
| `ENABLED`, `\AA`, `\EE`, action composition `\cdot` | unsupported | rewrite the property |
| `TLCGet`, `TLCSet`, `Print` as state | unsupported | TLC only |
| `SYMMETRY`, `CONSTRAINT` in `.cfg` | ignored | `CInit` and `--length` |
| `ASSUME` | ignored | encode the assumption in `CInit` |
| Temporal properties | supported with loop encoding | TLC first; Apalache when TLC cannot finish |

## Performance

- Keep `--length` at the smallest number of steps that can exhibit the property; a protocol with
  three phases rarely needs more than eight.
- Prefer records with fixed fields to functions with computed domains; prefer `SUBSET` of small
  sets only.
- Split a disjunctive `Next` into separate `--next` runs when the solver stalls; the report lists
  each.
- `--tuning-options=search.invariant.mode=after` checks invariants after each step rather than
  during; faster for cheap invariants.
- Reuse `--run-dir` and read `detailed.log` when a run is slow: the step at which time goes is where
  the action is too permissive.
