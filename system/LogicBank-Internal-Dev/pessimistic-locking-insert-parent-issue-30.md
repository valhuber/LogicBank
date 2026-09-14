---
title: "pessimistic Locking Loses the Parent Created by insert_parent" — GitHub Issue #30 (Fixed)
Description: Under trans_update_locking="pessimistic", _get_parent_logic_row skipped the fast in-memory relationship read unconditionally and went straight to a locking DB read - missed a parent insert_parent had just created earlier in the SAME transaction (not yet flushed), silently dropping the adjustment and unlinking the child's FK
Source: logic_bank/exec_row_logic/logic_row.py (LogicRow._get_parent_logic_row)
Usage: Read before touching the use_locking_read computation, or any of the 5 adjust_from_* call sites in aggregate.py that pass for_update=True. Companion doc to insert-parent-partial-null-fk-issue-29.md (#29) and dragons-deferred-adjustment.md (a different, older same-transaction-ordering hazard in the adjustment machinery). See also internal_dev/locking_strategy.md (ApiLogicServer-src) for trans_update_locking design rationale.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by making use_locking_read conditional on the relationship already holding a PERSISTENT (already-flushed) parent, via inspect(...).key. Regression suite examples/pessimistic_insert_parent/ (subprocess-per-mode, since RuleBank is a process-wide singleton).
---

# `pessimistic` Locking Loses the Parent Created by `insert_parent`

## TL;DR

[GitHub issue #30](https://github.com/valhuber/LogicBank/issues/30): with `trans_update_locking="pessimistic"`, `LogicRow._get_parent_logic_row` skips the fast in-memory relationship read (`getattr(row, role_name)`) entirely whenever `for_update=True`, going straight to a locking DB read (`with_for_update().populate_existing().get()`). That's correct when the parent already exists in the database — the whole point of pessimistic locking is to re-fetch-and-lock rather than trust a possibly-stale cached value.

It's **wrong** when `insert_parent=True` just created that parent **earlier in the same transaction**: the new parent is set on the relationship (`_is_inserted_parent()` did `setattr(self.row, role_name, inserted_parent_row.row)`), but it hasn't been flushed to the database yet — no identity key, not visible to a `SELECT ... FOR UPDATE`. The locking read finds nothing and returns `None`. Two silent failures follow, both with no exception:

1. **The adjustment is dropped.** The `adjust_from_*` call site (`aggregate.py`) sees `parent_logic_row.row is None`, treats it as "legitimately no parent, nothing to adjust," and skips. The just-inserted parent keeps its aggregate default instead of picking up the child's contribution.
2. **The child gets unlinked from its own just-inserted parent.** `_get_parent_logic_row` then does `setattr(row, role_name, parent_row)` with `parent_row=None` — which (per the FK-column-wiping side effect documented in `insert-parent-partial-null-fk-issue-29.md` / `composite_key_issue.md`) nulls the child's FK column(s), even for a single-column FK in this case, since the relationship setter is unconditionally re-run with the new (null) value.

With `trans_update_locking="ignored"` (the default), the same rule is correct — the fast in-memory path is used and correctly finds the pending parent.

**In 1.34.0 and later**, the [#26](https://github.com/valhuber/LogicBank/issues/26) fix compounds this: `adjust_from_inserted_child` sees no parent and calls `_is_inserted_parent()` again, inserting the parent a **second** time — `IntegrityError: UNIQUE constraint failed`.

**Fixed:** `use_locking_read` now also checks whether the relationship's current value is a genuinely **persistent** (already-flushed) object, via `inspect(..., raiseerr=False).key`. A pending/just-inserted parent (no identity key yet), or an unset relationship, now falls through to the normal `getattr(row, role_name)` path — exactly what `ignored` mode already did correctly. Only a truly persistent parent triggers the locking DB read.

&nbsp;

## The concrete scenario

```python
Rule.sum(derive=Stock.sold, as_sum_of=SaleLine.qty, insert_parent=True)
```

`Stock(product_id)` — no `Stock(10)` exists yet. `SaleLine(product_id=10, qty=3)` is inserted; `insert_parent` must create `Stock(10)` in the same transaction and set its `sold` to 3.

```
$ pip install logicbank==1.33.0
  ignored      Stock(10).sold = 3 after the line that inserts it (expected 3), 5 after a second line (expected 5)
               first line saved with product_id = 10 (expected 10)  ok
  pessimistic  Stock(10).sold = 0 after the line that inserts it (expected 3), 2 after a second line (expected 5)
               first line saved with product_id = None (expected 10)  WRONG

$ pip install logicbank==1.34.0
  ignored      ok (same as above)
  pessimistic  insert FAILED  expected Stock(10).sold = 3
    IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: stock.product_id
```

It reproduces on SQLite because the loss comes from `populate_existing().get()` going to the database, not from the `FOR UPDATE` clause itself (SQLite drops that clause; the round-trip and identity-map bypass still happen). Confirmed on MariaDB too, with real project rules, per the issue.

&nbsp;

## The fix

```diff
--- a/logic_bank/exec_row_logic/logic_row.py
+++ b/logic_bank/exec_row_logic/logic_row.py
@@ _get_parent_logic_row
-        use_locking_read = for_update and RuleBank().trans_update_locking == "pessimistic"
+        use_locking_read = for_update and RuleBank().trans_update_locking == "pessimistic" \
+            and getattr(inspect(vars(row).get(role_name), raiseerr=False), "key", True) is not None
```

Reading `vars(row).get(role_name)` (rather than `getattr(row, role_name)`) avoids triggering a lazy load that could itself hit the database. Three cases for `inspect(vars(row).get(role_name), raiseerr=False)`:
- **Unset relationship** (`vars(row).get(role_name)` is `None`, the normal case for a parent not yet navigated to): `inspect(None, raiseerr=False)` returns `None`, and `getattr(None, "key", True)` falls back to its default, `True` — so `use_locking_read` stays `True`. Correct: an unset relationship means "go look it up," which is exactly what the locking read does. Verified directly: `inspect(None, raiseerr=False)` → `None`; `getattr(None, "key", True)` → `True`.
- **Pending** (inserted but not yet flushed) mapped object: `inspect(obj).key` is `None` (no identity key assigned yet) → `use_locking_read` becomes `False` → falls through to `getattr(row, role_name)`, correctly returning the pending parent. This is the case the fix targets.
- **Persistent** (already-flushed) mapped object: `inspect(obj).key` is its actual identity key (not `None`) → `use_locking_read` stays `True` → the locking read proceeds, as intended.

A parent inserted **concurrently by another transaction** (genuinely racing, not same-transaction) still fails visibly on the primary key when this transaction flushes — the fix only changes behavior for a parent this same transaction itself just created, not for real cross-transaction concurrency, so the race-closing guarantee `concurrent_adjust` (#25) tests for is unaffected.

&nbsp;

## Why `concurrent_adjust` (#25) didn't catch this

`concurrent_adjust`'s scenario is two *separate* transactions racing to update the *same, already-existing* `Customer.balance` — pessimistic locking's actual job. It never exercises `insert_parent`, so the "parent created earlier in the same transaction, not yet flushed" state this issue depends on never arises there. Re-ran `concurrent_adjust`'s full suite (`test_for_update_sql.py`, `test_interleaved_race.py`) after this fix — both still pass, confirming the fix doesn't weaken the genuine cross-transaction locking guarantee.

&nbsp;

## Regression suite

`examples/pessimistic_insert_parent/` (Stock/SaleLine, single-column FK — deliberately simpler than #29's composite key, to isolate the locking interaction on its own). Since `RuleBank` is a process-wide singleton (`logic_bank/rule_bank/rule_bank.py`), a second `LogicBank.activate()` call with a different `trans_update_locking` in the same process would reuse the first activation's state — so, matching the issue's own repro script, each locking mode runs in its own subprocess (`_worker_pessimistic_insert_parent.py`, invoked once per mode). Two tests: `test_ignored_mode_baseline` and `test_pessimistic_mode_keeps_insert_parent_adjustment` (the actual regression — asserts the `sold` adjustment survives and the FK stays linked, across both a first insert-triggering line and a second line against the now-persistent parent).

Confirmed `test_pessimistic_mode_keeps_insert_parent_adjustment` fails against unfixed code with the exact `IntegrityError: UNIQUE constraint failed: stock.product_id` from the issue (the 1.34.0/current-`main` symptom), and passes with the fix applied. Full suite (`run_tests.py`, all 20 example directories) re-confirmed green.

&nbsp;

## Context

Found by `alejandromyto` enabling `pessimistic` on an ApiLogicServer/GenAI-Logic project pinned to 1.33.0: its test suite failed in flows that create a parent through `insert_parent` and then check it (stock rows from purchases/adjustments/transfers), and a `Rule.count`-backed constraint accepted a duplicate because the count was silently wrong. A sales-line scenario failed the same way but wasn't caught, since that project's test only checked the order header. See [GitHub issue #30](https://github.com/valhuber/LogicBank/issues/30) for the original repro script and diff.
