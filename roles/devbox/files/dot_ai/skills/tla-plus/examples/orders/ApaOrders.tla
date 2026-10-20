---- MODULE ApaOrders ----
(* Apalache entry module. CInit constrains constants symbolically so one run
   covers a family; a range bound (Items == 1..MaxItems) must stay a literal,
   so MaxItems is fixed with "=". Apalache derives initial states from --init
   through assignments only (x = e, x \in S), so the inductive invariant is
   restated in that form here. Apalache-only: SANY and TLC cannot resolve
   the Apalache module, so this file is not part of the TLC runs. *)
EXTENDS Orders, Apalache

CInit ==
    /\ Customers \in SUBSET {"c1", "c2", "c3"}
    /\ Customers /= {}
    /\ MaxItems = 2

ApaTypeOK ==
    /\ orders = [c \in Customers |-> Gen(MaxItems)]
    /\ \A c \in Customers :
        /\ Len(orders[c]) <= MaxItems
        /\ \A k \in DOMAIN orders[c] : orders[c][k] \in Items
    /\ payments \in SUBSET Customers
    /\ shipped \in SUBSET Customers

ApaIndInv == ApaTypeOK /\ PaidImpliesOrdered /\ ShipOnlyPaid
====
