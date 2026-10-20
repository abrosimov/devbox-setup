---- MODULE MCOrders ----
(* Small-instance module for TLC. Constants come from the .cfg files. *)
EXTENDS Orders, TLC

Perms == Permutations(Customers)
====
