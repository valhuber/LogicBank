# insert_parent: same-flush duplicate parent, and reparent without parent_check

Found Nov 2026 building GenAI-Logic's `demo_eai` order-flow dashboard: a `daily_flow` table (PK `day`) maintained by
`Rule.count` / `Rule.sum` with `insert_parent=True` from Order, OrderB2bMessage and OrderB2bRequest.

## 1. Two new children of the same NEW parent in one flush: parent inserted twice

**Symptom:** `UNIQUE constraint failed` on the parent key. Case: the first order and the first message of a day,
inserted in one transaction (the EAI debug endpoint's simulated path), each counted into that day's `daily_flow` row.

**Cause:** `LogicRow._is_inserted_parent` always created a new parent. The parent the first child created is not yet
flushed, so `_get_parent_logic_row`'s lookup does not find it, and the second child created another.

**Fix:** `LogicRow._pending_inserted_parent` - before creating, look for a parent of that class with the child's FK
values among the rows inserted in this transaction: `session.new` (client adds) and `row_sets.processed_logic_rows`
with `ins_upd_dlt == "ins"` (rows inserted by logic, e.g. a previous insert_parent - these are NOT yet in
`session.new`).  If found, attach the child to it (restoring the FK values, as the create path does) and do not insert.

**Test:** `examples/insert_parent/tests/test_insert_parent.py`, Test 3 - two children, one new parent, one commit:
one parent, `child_count` 2, `child_sum` 7.

## 2. Reparent to a missing parent, with no parent_check rule

**Symptom:** `ConstraintException: Unable to Adjust Missing Adopting Parent` when an UPDATE moves a child to a parent
that does not exist yet, although the aggregate declares `insert_parent=True`.

**Cause:** on update, a missing parent was created only inside the `Rule.parent_check` block of
`LogicRow._check_parents_on_update` (the existing Test 2 passes because this example declares parent_check).  Without
that rule, `Aggregate.adjust_from_updated_reparented_child` raised.

**Fix:** `adjust_from_updated_reparented_child` - when the new parent is missing, its FK is not null, and this aggregate
declared insert_parent, create it with `_is_inserted_parent` (as `adjust_from_inserted_child` already does), then
re-read the parent logic row.

**Test:** Test 4 - parent_check disabled (`ref_integ_rule._enable = False`), a child moved to a missing parent: the
adopting parent is created (count 1, sum 3) and the previous parent adjusted down (count 1, sum 4).

## Running the tests against the repo code

`run_tests.py` uses `venv/bin/python` if present, else `python`.  Without a repo venv, `python` may resolve
`logic_bank` from an installed package (e.g. a GenAI-Logic Manager venv) rather than this repo: run with
`PYTHONPATH=$(pwd) python3 run_tests.py`.  Both tests fail against 1.34.04 and pass with the fix; the full suite passes.
