# Orders example

The spec shape, TLC configurations, Apalache entry module and trace validation of the `tla-plus`
skill as runnable files. Run from this directory; every command is the verification.
TLC and the trace fixtures were run against TLA+ tools 1.8.0 and CommunityModules 2026-10; the
Apalache commands are written for 0.62 and run by `tests/deploy/test_skill_examples.py` on a
provisioned machine.

```bash
CP="${TLA2TOOLS_JAR:-$HOME/.local/share/tlaplus/tla2tools/tla2tools.jar}:$HOME/.local/share/tlaplus/communitymodules/CommunityModules-deps.jar"

# 1. Parse and lint the schema
java -cp "$CP" tla2sany.SANY Orders.tla
buf lint

# 2. TLC: safety + liveness, three customers (no symmetry: liveness)
java -XX:+UseParallelGC -cp "$CP" tlc2.TLC -config MCOrders.cfg -workers auto -noTE -cleanup MCOrders.tla

# 3. TLC: safety only, four customers, symmetry on
java -XX:+UseParallelGC -cp "$CP" tlc2.TLC -config MCOrdersSafety.cfg -workers auto -noTE -cleanup MCOrders.tla

# 4. Apalache: bounded safety over the constant family, then the inductive invariant
OUT="$(mktemp -d)"
apalache-mc typecheck ApaOrders.tla
apalache-mc check --cinit=CInit --inv=PaidImpliesOrdered --length=8 --out-dir="$OUT" ApaOrders.tla
apalache-mc check --cinit=CInit --init=Init --inv=ApaIndInv --length=0 --out-dir="$OUT" ApaOrders.tla
apalache-mc check --cinit=CInit --init=ApaIndInv --inv=ApaIndInv --length=1 --out-dir="$OUT" ApaOrders.tla

# 5. Trace validation: happy-path is accepted; ship-before-pay fails POSTCONDITION TraceAccepted
TRACE_PATH="$PWD/traces/happy-path.jsonl" java -cp "$CP" tlc2.TLC -config TraceOrders.cfg -noTE -cleanup TraceOrders.tla
TRACE_PATH="$PWD/traces/ship-before-pay.jsonl" java -cp "$CP" tlc2.TLC -config TraceOrders.cfg -noTE -cleanup TraceOrders.tla \
    | grep -q "Postcondition TraceAccepted" && echo "rejected as expected"
```
