---- MODULE ApaOrders ----
(* Apalache entry module: constants constrained symbolically instead of fixed,
   so one run covers every instance in the family. *)
EXTENDS Orders

CInit ==
    /\ Customers \in SUBSET {"c1", "c2", "c3"}
    /\ Customers /= {}
    /\ MaxItems \in 1..3
====
