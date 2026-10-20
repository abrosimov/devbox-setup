---- MODULE Orders ----
(* Abstract specification of a small order flow. Shape: constants, variables,
   TypeOK first, one action per domain command, Spec with the fairness the
   liveness property needs, properties named after the invariant they encode. *)
EXTENDS Naturals, Sequences

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

(* Each property evidences the invariant note that states it, through a kadmos
   code anchor (standards/code-anchors.md of the project's vault). The vault's
   validator scans these lines; the note lists the slug under `anchored_by`.
   The references below are illustrative: this example lives in no vault. *)

\* ariadne-kadmou[orders-paid-implies-ordered|evidences|kadmos://oikos/invariants/INV-00001-paid-implies-ordered.md#Statement]
PaidImpliesOrdered == \A c \in Customers : c \in payments => orders[c] /= <<>>

\* ariadne-kadmou[orders-ship-only-paid|evidences|kadmos://oikos/invariants/INV-00002-ship-only-paid.md#Statement]
ShipOnlyPaid == shipped \subseteq payments

\* ariadne-kadmou[orders-eventually-shipped|evidences|kadmos://oikos/invariants/INV-00003-eventually-shipped.md#Statement] liveness
EventuallyShipped == \A c \in Customers : c \in payments ~> c \in shipped

\* Inductive invariant (TLC checks it as an ordinary invariant; Apalache uses ApaOrders.ApaIndInv).
IndInv == TypeOK /\ PaidImpliesOrdered /\ ShipOnlyPaid
====
