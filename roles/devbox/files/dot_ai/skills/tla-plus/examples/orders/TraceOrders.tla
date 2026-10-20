---- MODULE TraceOrders ----
(* Trace validation: replay a behaviour log of the implementation against
   Orders. The log is one protojson-encoded orders.trace.v1.Event per line
   (proto/orders/trace/v1/trace.proto); the oneof field name on a line names
   the spec action. Needs CommunityModules (Json, IOUtils) on the classpath. *)
EXTENDS Orders, Json, IOUtils, TLC

\* The file is named by the TRACE_PATH environment variable.
Trace == ndJsonDeserialize(IOEnv.TRACE_PATH)

VARIABLE l               \* index of the next log line to consume
tvars == <<vars, l>>

logline == Trace[l]

\* JSON arrays arrive as sequences; the spec's variables are sets.
AsSet(seq) == {seq[k] : k \in DOMAIN seq}

\* The line carries exactly one action field, named as protojson spells the oneof member.
IsEvent(name) ==
    /\ l <= Len(Trace)
    /\ name \in DOMAIN logline
    /\ l' = l + 1

\* Arguments present on the line fix the step; a missing one is chosen existentially.
TracePlace == IsEvent("place") /\ Place(logline.place.c, logline.place.item)
TracePay   == IsEvent("pay")   /\ Pay(logline.pay.c)
TraceShip  == IsEvent("ship")  /\ \E c \in Customers : c = logline.ship.c /\ Ship(c)

\* A snapshot on the line narrows the match further; protojson omits empty lists.
SnapshotOK ==
    "state" \in DOMAIN logline =>
        /\ "payments" \in DOMAIN logline.state => payments' = AsSet(logline.state.payments)
        /\ "shipped" \in DOMAIN logline.state => shipped' = AsSet(logline.state.shipped)

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
