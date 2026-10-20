# Orders example

The spec shape, TLC configurations, Apalache entry module and trace-validation module the
`tla-plus` skill describes, as runnable files. Every command below is the verification.

**Status**: written against TLA+ tools 1.8.0, Apalache 0.62 and CommunityModules 2026-10; not
yet executed in the repository's CI (no Java there). `tests/deploy/test_skill_examples.py` runs
them whenever the toolchain from `devbox_packages.tlaplus` is installed and skips otherwise.

```bash
TLA_LIB="$HOME/.local/share/tlaplus"
CP="${TLA2TOOLS_JAR:-$TLA_LIB/tla2tools/tla2tools.jar}:$TLA_LIB/communitymodules/CommunityModules-deps.jar"
cd "$(dirname "$0")"

# 1. Parse
java -cp "$CP" tla2sany.SANY Orders.tla

# 2. TLC: safety + liveness, three customers (no symmetry: liveness)
java -XX:+UseParallelGC -cp "$CP" tlc2.TLC -config MCOrders.cfg -workers auto -noTE -cleanup MCOrders.tla

# 3. TLC: safety only, four customers, symmetry on
java -XX:+UseParallelGC -cp "$CP" tlc2.TLC -config MCOrdersSafety.cfg -workers auto -noTE -cleanup MCOrders.tla

# 4. Apalache: bounded safety over the constant family, then the inductive invariant
apalache-mc typecheck ApaOrders.tla
apalache-mc check --cinit=CInit --inv=NoDoublePayment --length=8 ApaOrders.tla
apalache-mc check --cinit=CInit --init=Init --inv=IndInv --length=0 ApaOrders.tla     # base
apalache-mc check --cinit=CInit --init=IndInv --inv=IndInv --length=1 ApaOrders.tla   # step

# 5. Trace validation: one accepted trace, one that must be rejected
TRACE_PATH="$PWD/traces/happy-path.ndjson" java -cp "$CP" tlc2.TLC -config TraceOrders.cfg -noTE -cleanup TraceOrders.tla
TRACE_PATH="$PWD/traces/ship-before-pay.ndjson" java -cp "$CP" tlc2.TLC -config TraceOrders.cfg -noTE -cleanup TraceOrders.tla \
    && echo "UNEXPECTED: rejected trace accepted" || echo "rejected as expected"
```

Expected: steps 1–4 exit 0; step 5 accepts `happy-path` (exit 0, postcondition holds) and rejects
`ship-before-pay` (`Ship` is not enabled for an unpaid customer, so line 2 cannot be matched and the
postcondition fails).
