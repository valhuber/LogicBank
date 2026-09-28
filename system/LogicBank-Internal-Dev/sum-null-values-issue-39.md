---
title: "Rule.sum Raises TypeError on NULL Values, Except on Insert" — GitHub Issue #39 (Fixed)
Description: Aggregate.adjust_from_inserted_child normalized a NULL summed child value and a NULL parent sum to 0, but adjust_from_deleted_child, adjust_from_updated_child and adjust_from_updated_reparented_child each did so only in part - so a row accepted on insert with a NULL summed value could not be deleted, cleared, or reparented without a TypeError
Source: logic_bank/rule_type/aggregate.py (Aggregate.adjust_from_deleted_child, adjust_from_updated_child, adjust_from_updated_reparented_child)
Usage: Read before touching any adjust_from_* method in aggregate.py, or assuming a summed column's value (or a parent's current sum) is non-NULL at any of these call sites - insert already knew better.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by applying adjust_from_inserted_child's existing `if x is None: x = 0` normalization consistently to delete, update and reparent, for both the child's summed value and the parent's current sum. Regression suite examples/sum_null_values/.
---

# Rule.sum Raises TypeError on NULL Values, Except on Insert

## TL;DR

[GitHub issue #39](https://github.com/valhuber/LogicBank/issues/39): `Aggregate.adjust_from_inserted_child` (`rule_type/aggregate.py`) already treats a NULL summed value on the child, and a NULL current sum on the parent, as `0`:

```python
delta = get_summed_field()
if delta is None:
    delta = 0
...
curr_value = getattr(parent_adjustor.parent_logic_row.row, self._column)
if curr_value is None:
    curr_value = 0
```

(added in `229f71b`, "inserted summed attr should allow for null", five days after issue #4 was closed in 0.9.4). The other three `adjust_from_*` methods in the same class did the equivalent normalization only in part, and subtracted or added the raw (possibly `None`) value everywhere they didn't:

- `adjust_from_deleted_child`: normalized **neither** the child's value nor the parent's current sum.
- `adjust_from_updated_child`: normalized the **old** summed value, but not the **new** one — so changing a non-NULL value to NULL failed (`delta = summed_field - old_summed_field` with `summed_field is None`).
- `adjust_from_updated_reparented_child`: normalized on the **new**-parent side, but not on the **previous**-parent side.

Net effect: a row whose summed column is legitimately NULL (accepted fine on insert, per the 0.9.4 fix) could not afterwards be **deleted**, **updated to clear the value**, or **reparented**, without:

```
TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and 'NoneType'
```

or the reverse operand order, depending on which side was `None`.

This is the same normalization-gap *class* of bug as #27/#31/#34 — one aggregate code path already knew a value could be missing/absent and handled it; a sibling path making the same arithmetic assumption didn't.

&nbsp;

## The fix

The same `if x is None: x = 0` guard `adjust_from_inserted_child` already used, applied at each of the four remaining points where a summed value or a current parent sum is read and then used arithmetically:

```diff
--- a/logic_bank/rule_type/aggregate.py
+++ b/logic_bank/rule_type/aggregate.py
@@ adjust_from_deleted_child
         delta = get_summed_field()
+        if delta is None:
+            delta = 0
         if where and delta != 0.0:
@@ adjust_from_deleted_child
             curr_value = getattr(parent_adjustor.parent_logic_row.row, self._column)
+            if curr_value is None:
+                curr_value = 0
             is_do_not_adjust = parent_adjustor.parent_logic_row._is_in_list(do_not_adjust_list)
@@ adjust_from_updated_child
         summed_field = get_summed_field()
+        if summed_field is None:
+            summed_field = 0
         old_summed_field = get_old_summed_field()
         if old_summed_field is None:
             old_summed_field = 0
@@ adjust_from_updated_reparented_child (previous-parent side)
         delta = get_old_summed_field()
+        if delta is None:
+            delta = 0
         if where and delta != 0:
@@ adjust_from_updated_reparented_child (previous-parent side)
                 curr_value = getattr(parent_adjustor.previous_parent_logic_row.row, self._column)
+                if curr_value is None:
+                    curr_value = 0
                 setattr(parent_adjustor.previous_parent_logic_row.row, self._column, curr_value - delta)
```

(`adjust_from_updated_reparented_child`'s **new**-parent side, and `adjust_from_updated_child`'s `old_summed_field`, already had this guard from earlier work on the #27/#31 issue family — this fix closes the remaining gaps, not those.)

A NULL child value now contributes nothing to any adjustment path, and a NULL current parent sum is treated as `0` to add to or subtract from — consistently, on every path, matching what insert already did.

&nbsp;

## Regression suite

`examples/sum_null_values/` — Customer/Order, `Rule.sum(Customer.balance, as_sum_of=Order.amount)`, `amount` nullable. Four tests:

- `test_insert_null_amount_baseline` — insert with `amount=None` (already worked pre-fix; kept as a baseline so a future change can't silently regress the one path that always worked).
- `test_delete_child_with_null_amount` — insert then delete a NULL-amount order. Fails against unfixed code with `TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and 'NoneType'`.
- `test_update_amount_to_null` — insert with a non-NULL amount, then set it to `None`. Fails against unfixed code with the same `TypeError` (operands reversed: `NoneType` and `decimal.Decimal`).
- `test_reparent_child_with_null_amount` — insert a NULL-amount order under one customer, then reparent it to another. Fails against unfixed code on the previous-parent decrement.

Confirmed 3 of 4 tests fail against unfixed code (the baseline passes both before and after, as expected) and all 4 pass with the fix applied. `run_tests.py` gives `ALL PASSED` with the fix in place.

&nbsp;

## Context

See [GitHub issue #39](https://github.com/valhuber/LogicBank/issues/39) for the original repro script and diff, and `sum-dequalify-decrement-issue-27.md` / `spurious-parent-dependency-issue-21-31.md` / `partial-composite-fk-unparent-issue-34.md` for the sibling normalization-gap bugs in the same aggregate-adjustment code.
