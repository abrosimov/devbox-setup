---- MODULE Orders ----
(* Abstract specification of a small order flow. Shape: constants, variables,
   TypeOK first, one action per domain command, Spec with the fairness the
   liveness property needs, properties named after the invariant they encode. *)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS
    \* @type: Set(Str);
    Customers,
    \* @type: Int;
    MaxItems

ASSUME MaxItems \in Nat /\ MaxItems > 0

VARIABLES
    \* @type: Str -> Seq(Int);
    orders,
    \* @type: Set(Str);
    payments,
    \* @type: Set(Str);
    shipped

vars == <<orders, payments, shipped>>

Items == 1..MaxItems

\* Written so that both TLC and Apalache can evaluate it: no `\in Seq(S)`.
TypeOK ==
    /\ DOMAIN orders = Customers
    /\ \A c \in Customers :
        /\ Len(orders[c]) <= MaxItems
        /\ \A k \in DOMAIN orders[c] : orders[c][k] \in Items
    /\ payments \subseteq Customers
    /\ shipped \subseteq Customers

Init ==
    /\ orders = [c \in Customers |-> <<>>]
    /\ payments = {}
    /\ shipped = {}

Place(c, i) ==
    /\ Len(orders[c]) < MaxItems
    /\ orders' = [orders EXCEPT ![c] = Append(@, i)]
    /\ UNCHANGED <<payments, shipped>>

Pay(c) ==
    /\ c \notin payments
    /\ orders[c] /= <<>>
    /\ payments' = payments \cup {c}
    /\ UNCHANGED <<orders, shipped>>

Ship(c) ==
    /\ c \in payments
    /\ c \notin shipped
    /\ shipped' = shipped \cup {c}
    /\ UNCHANGED <<orders, payments>>

Next ==
    \E c \in Customers :
        \/ \E i \in Items : Place(c, i)
        \/ Pay(c)
        \/ Ship(c)

\* Weak fairness per customer on Ship: a paid order is not left unshipped forever.
Spec == Init /\ [][Next]_vars /\ \A c \in Customers : WF_vars(Ship(c))

\* INV-1: a customer is paid only when an order exists.
NoDoublePayment == \A c \in Customers : c \in payments => orders[c] /= <<>>
\* INV-2: only paid customers are shipped.
ShipOnlyPaid == shipped \subseteq payments
\* INV-3 (liveness): every paid customer is eventually shipped.
EventuallyShipped == \A c \in Customers : c \in payments ~> c \in shipped

\* Candidate inductive invariant for the Apalache workflow.
IndInv == TypeOK /\ NoDoublePayment /\ ShipOnlyPaid
====
