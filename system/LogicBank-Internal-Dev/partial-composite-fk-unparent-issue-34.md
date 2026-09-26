---
title: "Clearing a Composite Foreign Key Raises \"Unable to Adjust Missing Adopting Parent\"" — GitHub Issue #34 (Fixed)
Description: Aggregate._fk_is_null required EVERY column of a composite FK to be null before treating a child as parentless - a partially-null composite FK (only the column pointing at the parent cleared, the rest the child's own data) was misread as "parent not found" and rejected on UPDATE, while the identical key was already accepted on INSERT via the engine's other any-null checks
Source: logic_bank/rule_type/aggregate.py (Aggregate._fk_is_null)
Usage: Read before touching Aggregate._fk_is_null, or any of _is_foreign_key_null / _get_parent_logic_row's null-FK handling - they must all agree on "any column null", not "all columns null".
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by flipping _fk_is_null to an any-null test, matching the rest of the engine. Regression suite examples/partial_composite_fk_unparent/.
---

# Clearing a Composite Foreign Key Raises "Unable to Adjust Missing Adopting Parent"

## TL;DR

[GitHub issue #34](https://github.com/valhuber/LogicBank/issues/34): `Aggregate._fk_is_null` (`rule_type/aggregate.py`) required **every** column of the FK to be null:

```python
for each_child_col, each_parent_col in role_def.local_remote_pairs:
    if getattr(child_row, each_child_col.name) is not None:
        return False        # <-- ANY column set means "not null"
return True
```

With a composite key that never happens. When a row stops having a parent, only the column that actually points at the parent gets cleared: the others (a tenant id, a company code, an application code) are the child's own data and stay set. `adjust_from_updated_reparented_child` then reads the partially-null key as a parent that can't be found and rejects the update:

```
logic_bank.util.ConstraintException: Unable to Adjust Missing Adopting Parent: Parent
```

The rest of the engine already agrees on the opposite answer for the same question: `_is_foreign_key_null` (used on INSERT) and the `None in parent_key.values()` short-circuit in `_get_parent_logic_row` both return true if **any** column is null. So the identical partially-null FK is accepted when the row is *inserted*, and only rejected when an *existing* row's FK is *cleared* — which is what makes the inconsistency easy to miss until someone actually reparents a row away from a parent identified by more than one column.

**Fixed:** flip `_fk_is_null` to the same any-null test the rest of the engine already uses.

&nbsp;

## The concrete scenario

A self-referencing `MenuOption` table, chained to its parent by `(app, parent_id)` — `app` also identifies the row itself and is never nulled; `parent_id` is the only column that gets nulled when an option becomes top-level. `Rule.count` sums the children onto `sub_count`:

```
after insert: parent.sub_count = 1
insert with a partially-null composite FK: accepted
FAILED: Unable to Adjust Missing Adopting Parent: Parent
```

The insert with the same shape of partially-null key (`app='A', id='R', parent_id=None`) is accepted without complaint. Only the update that clears `parent_id` on an *existing* child raises.

Self-reference is incidental to the bug — any parent identified by more than one column behaves the same.

&nbsp;

## The fix

```diff
     def _fk_is_null(child_row, role_name: str) -> bool:
-        """ True iff the FK column(s) backing role_name are null on child_row -
+        """ True iff ANY FK column backing role_name is null on child_row -
         distinguishes "no parent expected" (nullable FK, not an error) from
         "FK references a parent that can't be found" (data integrity error).
         """
         my_mapper = object_mapper(child_row)
         role_def = my_mapper.relationships.get(role_name)
         if role_def is None:
             return False
         for each_child_col, each_parent_col in role_def.local_remote_pairs:
-            if getattr(child_row, each_child_col.name) is not None:
-                return False
-        return True
+            if getattr(child_row, each_child_col.name) is None:
+                return True
+        return False
```

Single-column FKs are unaffected — "all null" and "any null" coincide when there's only one column, which is why this went unnoticed since the helper was introduced in #20 (tested against `Employee.on_loan_id`, a single nullable column). A composite key with *every* column set that still matches no row correctly continues to raise — the message is accurate for that case; this fix only changes the *partially*-null case.

With the fix:

```
after insert: parent.sub_count = 1
insert with a partially-null composite FK: accepted
after clearing the FK: parent.sub_count = 0
rows: [('P', None), ('C', None), ('R', None)]
```

&nbsp;

## Related

Same family as **#26** and **#29** ([copy-null-parent-issue-28.md](copy-null-parent-issue-28.md), [insert-parent-partial-null-fk-issue-29.md](insert-parent-partial-null-fk-issue-29.md)), but on the UPDATE path — the only one that reaches `_fk_is_null` — which is why it was left out when #29 aligned the others.

&nbsp;

## Regression suite

`examples/partial_composite_fk_unparent/` (self-referencing `MenuOption`, composite key `(app, parent_id)`, `Rule.count` over `ChildList`). Two tests: `test_insert_with_partially_null_composite_fk_is_accepted` (baseline — already worked pre-fix, since INSERT uses the any-null test) and `test_clearing_composite_fk_does_not_raise` (the actual regression — clears `parent_id` on an existing child, asserts the commit succeeds and `sub_count` adjusts to 0). Confirmed the second test fails with the exact `ConstraintException` from the issue against unfixed code, and passes with the fix applied.

&nbsp;

## Context

See [GitHub issue #34](https://github.com/valhuber/LogicBank/issues/34) for the original repro script (`repro_partial_composite_fk_unparent.py`).
