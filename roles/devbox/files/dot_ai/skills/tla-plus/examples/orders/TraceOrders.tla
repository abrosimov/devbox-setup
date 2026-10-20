---- MODULE TraceOrders ----
(* Trace validation: replay an NDJSON behaviour log of the implementation
   against Orders. Needs CommunityModules (Json, IOUtils) on the classpath. *)
EXTENDS Orders, Json, IOUtils, TLC

\* The file is named by the TRACE_PATH environment variable.
Trace == ndJsonDeserialize(IOEnv.TRACE_PATH)

VARIABLE l               \* index of the next log line to consume
tvars == <<vars, l>>

logline == Trace[l]

\* JSON arrays arrive as sequences; the spec's variables are sets.
AsSet(seq) == {seq[k] : k \in DOMAIN seq}

IsEvent(name) ==
    /\ l <= Len(Trace)
    /\ logline.event = name
    /\ l' = l + 1

\* Arguments present on the line fix the step; a missing one is chosen existentially.
TracePlace == IsEvent("Place") /\ Place(logline.args.c, logline.args.item)
TracePay   == IsEvent("Pay")   /\ Pay(logline.args.c)
TraceShip  == IsEvent("Ship")  /\ \E c \in Customers : c = logline.args.c /\ Ship(c)

\* Optional snapshot on the line narrows the match further.
SnapshotOK ==
    "state" \in DOMAIN logline => payments' = AsSet(logline.state.payments)

TraceInit == Init /\ l = 1

TraceNext ==
    /\ \/ TracePlace
       \/ TracePay
       \/ TraceShip
    /\ SnapshotOK

TraceSpec == TraceInit /\ [][TraceNext]_tvars

\* Every line was consumed: the longest path has one state per line plus the initial state.
TraceAccepted == TLCGet("stats").diameter = Len(Trace) + 1
====
