---
title: "Deleting a Child Can Skip Its Parent's Sum Adjustment, or Raise AttributeError" — GitHub Issue #38 (Fixed)
Description: LogicRow._is_in_list compared primary-key columns of the row-to-adjust against every row in a do_not_adjust_list without checking the rows belonged to the same table - raising AttributeError when column names differ, or silently skipping a legitimate adjustment when they coincide (e.g. both "id")
Source: logic_bank/exec_row_logic/logic_row.py (LogicRow._is_in_list)
Usage: Read before touching _is_in_list, adjust_from_deleted_child's do_not_adjust_list, or _cascade_delete_children - a cascade or a same-flush multi-delete can legitimately put rows of UNRELATED tables in that list.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by skipping any list entry whose table_meta differs from the row being checked. Regression suite examples/cascade_delete_multi_parent/.
---

# Deleting a Child Can Skip Its Parent's Sum Adjustment, or Raise AttributeError

## TL;DR

[GitHub issue #38](https://github.com/valhuber/LogicBank/issues/38): `LogicRow._is_in_list` (`exec_row_logic/logic_row.py`) compares the primary-key columns of `self.row` against every row in a list, to answer "is this parent already in the do-not-adjust list?":

```python
def _is_in_list(self, logic_rows: List) -> bool:
    result = False
    if logic_rows is not None:
        meta = self.table_meta
        pkey_cols = meta.primary_key.columns
        for each_logic_row in logic_rows:
            same_row = True
            for each_column in meta.primary_key.columns:
                col_name = each_column.name
                if getattr(self.row, col_name) != getattr(each_logic_row.row, col_name):
                    same_row = False
                    break
            if same_row:
                result = True
    return result
```

It never checks that `each_logic_row` belongs to the **same table** as `self`. Two call paths legitimately put rows of a *different* table in the list it's checking against:

- `before_flush` appends every client-deleted row of the flush to a `do_not_adjust_list`, regardless of table.
- `LogicRow._cascade_delete_children()` passes `[self]` (the deleted parent) as the `do_not_adjust_list` to each cascade-deleted child's own adjustment — but that child may `Rule.sum`/`Rule.count` into a **second**, unrelated parent table too.

`adjust_from_deleted_child` calls `_is_in_list` on the parent it's about to adjust, passing that list straight through. Two failure modes, depending on whether the two tables' primary-key column names happen to collide:

- **Different names** (e.g. `Order.id_order` vs `Product.id_product`): `getattr(<Order instance>, "id_product")` raises `AttributeError`, since `meta` here is `Product`'s metadata (columns named `id_product`), being applied to a row that is actually an `Order`.
- **Same name** (e.g. both `id`, as in the original `nw` sample this list mechanism was written for, back in issue #8 / 1.5.3): no exception — `getattr(order_row, "id")` and `getattr(product_row, "id")` both resolve, and whenever the two ids happen to be numerically equal, `_is_in_list` reports `True`. The parent is then silently treated as "already accounted for" and its adjustment is skipped, leaving the sum wrong with no error at all.

Every table having a primary key literally named `Id` (the `nw` convention) is exactly the condition that hid this for as long as it did.

&nbsp;

## The fix

```diff
             for each_logic_row in logic_rows:
+                if each_logic_row.table_meta is not meta:
+                    continue
                 same_row = True
```

Rows belonging to a different table can never be "the same row" as `self`, so they're skipped before any column comparison is attempted — cheaper than the AttributeError-prone path, and correct regardless of whether the two tables' primary-key column names happen to collide.

&nbsp;

## Regression suite

`examples/cascade_delete_multi_parent/` — `Order` (`id_order`) cascade-deletes to `OrderLine` (`id_line`), which sums `qty` into **both** `Order.qty_total` and `Product.qty_sold` (`id_product`) — deliberately different primary-key column names, matching the issue's repro, so unfixed code fails loudly (`AttributeError`) rather than silently.

- `test_cascade_delete_adjusts_unrelated_parent_table` — deletes the `Order`; the cascade deletes its `OrderLine`, which must still decrement `Product.qty_sold`. Against unfixed code this raises `AttributeError: 'Order' object has no attribute 'id_product'` (the cascade's `do_not_adjust_list=[self]` is the deleted `Order`, checked against `Product`'s primary-key column name).
- `test_non_cascade_delete_of_another_row_does_not_block_adjustment` — no cascade involved: deletes an unrelated second `Order` and an `OrderLine` in the same commit, confirming `before_flush`'s flush-wide `do_not_adjust_list` doesn't cross-contaminate between tables either.

Both pass with the fix; the first fails with `AttributeError` against unfixed code (confirmed). `run_tests.py` gives `ALL PASSED` with the fix in place.

&nbsp;

## Context

See [GitHub issue #38](https://github.com/valhuber/LogicBank/issues/38) for the original repro script and diff. The `do_not_adjust_list` mechanism itself dates to issue #8 (1.5.3), tested against the `nw` sample where every primary key happens to be named `Id` - which is why the same-name silent-skip half of this bug was never observed there.
