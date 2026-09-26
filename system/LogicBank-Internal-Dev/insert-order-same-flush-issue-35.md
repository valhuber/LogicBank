---
title: "Child Formula Can Read a Parent's Value Before It's Derived, in the Same Flush" — GitHub Issue #35 (Fixed)
Description: RowSets.client_inserts was a plain set(), so before_flush processed same-flush inserts in hash order rather than the order they were added - a child formula reading a derived parent column (row.Order.apply_tax) could see it before the parent's own formula had run, with nothing to recompute the child afterwards and no error
Source: logic_bank/exec_trans_logic/row_sets.py (RowSets.client_inserts / add_client_inserts), logic_bank/exec_trans_logic/listeners.py (iteration sites)
Usage: Read before touching client_inserts or assuming a.session.new's insertion order survives into how LogicBank actually processes same-flush inserts.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by making client_inserts a dict (insertion-ordered) instead of a set. Regression suite examples/insert_order_same_flush/.
---

# Child Formula Can Read a Parent's Value Before It's Derived, in the Same Flush

## TL;DR

[GitHub issue #35](https://github.com/valhuber/LogicBank/issues/35): `before_flush` processes inserts by iterating `RowSets.client_inserts`:

```python
for each_instance in row_sets.client_inserts:  # a_session.new:
```

`client_inserts` was a plain `set()`, populated (`add_client_inserts`) by walking `a_session.new` — which *does* preserve the order rows were added in. But a `set()` iterates in hash order, not insertion order, so that ordering guarantee is thrown away the moment each row is copied into it.

When a parent and its child are both new and committed in the same flush, this means the child can be visited before the parent. If the child's formula reads a value the parent's own formula derives (`row.Order.apply_tax`), it can read the parent's *pre-derivation* value — and nothing recomputes the child afterwards, silently. `_aggregate_defaults` already accounts for this kind of same-flush ordering ("This can occur because SQLAlchemy does not guarantee order of inserts" — its own comment); formulas that read a parent attribute did not.

**Fixed:** make `client_inserts` a `dict` instead of a `set()`. Dicts are insertion-ordered; membership and iteration semantics are otherwise identical, so this is a same-behavior, different-order change.

&nbsp;

## The concrete scenario

```python
Rule.formula(derive=Order.apply_tax, calling=order_apply_tax)          # computed on the order itself
Rule.formula(derive=OrderDetail.apply_tax, calling=detail_apply_tax)   # copies row.Order.apply_tax
```

One `Order` and one `OrderDetail`, both added and committed together:

```
order.apply_tax = 1   detail.apply_tax = None  STALE - detail processed before its order
```

With the fix:

```
order.apply_tax = 1   detail.apply_tax = 1  ok
```

&nbsp;

## The fix

```diff
--- a/logic_bank/exec_trans_logic/row_sets.py
+++ b/logic_bank/exec_trans_logic/row_sets.py
@@ -25,7 +25,7 @@ class RowSets():
-        self.client_inserts = set()
+        self.client_inserts = {}  # dict, not set: keeps insertion order
@@ -48,7 +48,7 @@ class RowSets():
     def add_client_inserts(self, row: base):
-        self.client_inserts.add(row)
+        self.client_inserts[row] = None
```

The two read sites in `listeners.py` (`for each_instance in row_sets.client_inserts: ...` and `row in row_sets.client_inserts` via `is_client_insert`) only ever iterate or test membership — never call a set-only method — so the dict swap is transparent to both.

&nbsp;

## Regression suite

`examples/insert_order_same_flush/` (`Order`/`OrderDetail`, matching the issue's own repro shape). Two tests:

- `test_client_inserts_preserves_insertion_order` — a direct, deterministic unit test of the mechanism itself: adds ten distinct objects to a fresh `RowSets().client_inserts` and asserts they iterate back in the same order. This is the part of the fix that's actually guaranteed; a plain `set()` of several distinct object instances does not reliably preserve insertion order (it depends on identity-hash-to-bucket placement, which is consistent on a given Python build but not a documented guarantee), so this test fails against unfixed code independent of any particular flush's hash-order luck.
- `test_child_formula_sees_parent_value_in_same_flush` — the functional scenario: `Order` and `OrderDetail` added and committed together, asserts the detail's formula observed the parent's derived value. This one is inherently exposed to the same hash-order dependency the bug itself is about; it failed reliably against unfixed code on the machine and Python build used to develop this fix, but — precisely because the underlying failure mode is hash-order-dependent rather than deterministic — treat the structural test above as the authoritative regression check if this one is ever seen to pass spuriously on a different Python build.

Confirmed both tests fail against unfixed code and pass with the fix applied.

&nbsp;

## Context

See [GitHub issue #35](https://github.com/valhuber/LogicBank/issues/35) for the original repro script and diff.
