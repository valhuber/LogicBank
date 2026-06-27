---
title: "Dragons Lurk Herein" — Nondeterministic Listener Order Bug (Fixed, Load-Bearing)
Description: Why LogicRow.save_altered_parents() defers adjustment chaining when a parent row is already submitted — a subtle, intermittent (≈50% reproduction rate) wrong-answer bug from unordered SQLAlchemy dirty-row processing
Source: logic_bank/exec_row_logic/logic_row.py (save_altered_parents), logic_bank/exec_trans_logic/listeners.py
Usage: Read before touching save_altered_parents(), listeners.py's before_flush handler, or RowSets/submitted_row/processed_rows tracking. This is one of the most subtle bugs in the engine — the fix looks like unnecessary complexity unless you understand what it prevents.
version: 1.1
changelog:
  - 1.1 (Jun 2026) - Refactored the defer decision out of save_altered_parents() into a named, documented, independently-unit-tested method (_should_defer_chaining()) - removed dead enable_deferred_adjusts/debug_info scaffolding in the same pass. Fixed the bug_explore/temp_debug() reproduction hook (stale get_old_row() call signature) and verified it works correctly when scoped to test_upd_order_reuse.py specifically (it's hardcoded to that scenario, crashes if enabled against other tests). Added test_should_defer_chaining.py (3 unit tests, fabricated RowSets state).
  - 1.0 (Jun 2026) - Initial writeup from the original $readme.txt scratch notes + test_upd_order_reuse.py's docstring (preserved verbatim there, including full before/after log traces) + the "Dragons lurk herein" comment in logic_row.py. Promoted from scratch notes to a proper doc since this was a killer, hard-to-reproduce bug.
---

# "Dragons Lurk Herein" — Nondeterministic Listener Order Bug

## TL;DR

SQLAlchemy's `session.dirty` (the set of changed rows a `before_flush` listener iterates) is **not ordered**. LogicBank processes whichever row SQLAlchemy hands it first. For most transactions this doesn't matter — but for a transaction that **reparents a child to a new parent AND changes a sum/count-contributing attribute on that same child in the same commit**, processing order determines whether the adjustment lands on the *old* parent or the *new* one. About half the time, SQLAlchemy handed LogicBank the rows in the order that produced the **wrong answer** — silently, with no error, just an incorrect balance. The fix defers adjustment-chaining logic when the target parent is already mid-flight ("submitted") in the same transaction, so the adjustment always resolves against final, settled state rather than a stale intermediate one.

This is exactly the class of bug that's terrifying in a rules engine: no exception, no crash, just a `Customer.Balance` that's quietly wrong — and it only reproduced **about half the time**, since it depended on iteration order over an unordered collection.

&nbsp;

## The concrete scenario (`test_upd_order_reuse.py`)

One commit does two things to **Order 11011** simultaneously:
1. **Reparents** the order: `Order.CustomerId` changes from `ALFKI` → `ANATR`
2. **Changes a child** that feeds the order's sum: an `OrderDetail`'s `ProductId`/`Quantity` change, which changes `OrderDetail.Amount`, which feeds `Order.AmountTotal` (`Rule.sum`), which feeds `Customer.Balance` (`Rule.sum`)

Expected result: `ALFKI.Balance` decreases by the *old* order amount (960.00 → 0), `ANATR.Balance` increases by the *new*, recalculated order amount (0 → 557.50, not 960.00).

### What went wrong, concretely

SQLAlchemy's `session.dirty` returned `OrderDetail` before `Order` about half the time. When that happened:

1. `OrderDetail` processes first. Its `Amount` formula recalculates (530.00 → 127.50). This triggers an aggregate adjustment to `Order.AmountTotal`'s parent — but at this point in the flush, **`Order.CustomerId` has already been changed to `ANATR` in memory** (SQLAlchemy applied the attribute change before the listener ran), so the adjustment chain resolves the parent via the **new** FK and adjusts **`ANATR`** — using `OrderDetail`'s *old* delta, before `Order.AmountTotal`'s own sum-of-OrderDetails has even been recomputed.
2. `Order` then processes (the explicit `CustomerId` reparent). It correctly recalculates `AmountTotal` (960.00 → 557.50) and adjusts the *current* customer — also `ANATR`, since that's now the FK.
3. Net result: **`ANATR` gets adjusted twice** (once from step 1's premature OrderDetail-driven chain, once from step 2's correct reparent chain) and **`ALFKI` never gets decremented at all** — the old parent's balance is left stale.

The actual failing log line (preserved in `test_upd_order_reuse.py`'s docstring):
```
....Order[11011] {Update - Adjusting OrderHeader} AmountTotal: [960.00-->] 557.50, CustomerId: ANATR, ...
......Customer[ANATR] {Update - Adjusting Customer} Balance: [0E-10-->] -402.50, ...
                        ^-- that's it... adjusting the new (wrong) customer, works when Order goes first
```
`ANATR.Balance` going **negative** (-402.50) before later correcting to a wrong positive value is the signature of this bug — it's not a crash, it's silent double/wrong-adjustment that an assertion later catches because the test happens to check the final balance, not because anything raised.

When SQLAlchemy happened to return `Order` first instead, the same transaction produced the correct result — same code, same data, same rules, different answer, depending purely on dict/set iteration order.

&nbsp;

## The fix: defer chaining if the parent is already "submitted" this transaction

**Refactored this session** (the logic is unchanged, only the code shape): the defer decision used to live inline inside `save_altered_parents()`, alongside dead `enable_deferred_adjusts`/`debug_info` scaffolding and a debug-only `if self.child_logic_row.name == 'OrderDetailXX':` branch. It's now its own named method, `ParentRoleAdjuster._should_defer_chaining(parent_logic_row)` (`logic_bank/exec_row_logic/logic_row.py`), with the "dragons" history moved into *its* docstring (at the point of the decision, not three scrolls away):

```python
def _should_defer_chaining(self, parent_logic_row: 'LogicRow') -> bool:
    row_sets = parent_logic_row.row_sets
    is_parent_submitted = parent_logic_row.row in row_sets.submitted_row
    is_parent_row_processed = parent_logic_row.row in row_sets.processed_rows
    return is_parent_submitted and not is_parent_row_processed
```

This also makes the invariant independently unit-testable without driving a full `session.commit()` through SQLAlchemy's nondeterministic dirty-set ordering — see `examples/nw/tests/test_should_defer_chaining.py` (3 tests, fabricates `RowSets` state directly): confirmed it correctly catches a deliberately-broken version of the check (`return False` unconditionally) failing exactly the test that exercises the true case, while the other two tests — which happen to expect `False` — stay green. That asymmetry is itself informative: a fast unit test only proves what it actually asserts, which is why both this unit test *and* the slower, real `test_upd_order_reuse.py` integration test matter — neither alone is sufficient.

- **`submitted_row`** — rows the *client* explicitly changed this transaction (e.g. `test_order.CustomerId = "ANATR"` — the user's own edit, not an engine-derived side effect)
- **`processed_rows`** — rows the engine has already finished running rules for, this transaction

If the parent (`Order`, in the OrderDetail-first case) **was itself directly edited by the client this transaction but hasn't been processed yet**, the adjustment's *value* is still applied (so the running total stays numerically consistent) but the **chaining/cascade logic is deliberately skipped** — because that parent is *going to be processed anyway*, later in this same flush, as a client-submitted row. Running the chain twice (once prematurely from a child's adjustment, once correctly when the parent's own update finally runs) is exactly what produced the double-adjustment above. Deferring means: let the parent's own, later, fully-informed processing pass be the *only* place chaining happens for it.

This is why the comment calls it "dragons" rather than just documenting a parameter — the fix isn't a validation check or a null-guard (the shape of the multi-relationship bugs in `multi-relationship-bug.md`); it's a **timing/ordering decision under a fundamentally unordered iteration**, and getting the condition wrong in either direction reintroduces either this bug (too little deferral) or under-adjustment (deferring when you shouldn't, so a real engine-driven cascade silently never fires because it incorrectly assumed the client would handle it).

&nbsp;

## How to deliberately force the bad ordering — fixed and verified working (this session)

`logic_bank/exec_trans_logic/listeners.py` has a `bug_explore` hook, with its own `"do not delete"` docstring, that bypasses normal `session.dirty` iteration and forces a specific processing order via `temp_debug()`:

```python
bug_explore = None  # None to disable, [None, None] to enable
if bug_explore is not None:  # temp hack - order rows to explore bug (upd_order_reuse)
    temp_debug(a_session, bug_explore, row_sets)
```

To activate: change `bug_explore = None` to `bug_explore = [None, None]`, and set `temp_debug()`'s `order_detail_first` flag (`True` forces the bad-ordering case — `OrderDetail` before `Order` — `False` forces the other order).

**Was bit-rotted, now fixed.** When first tested this session, activating it crashed immediately: `get_old_row()` had gained a required `session` parameter at some point after this hook was last exercised, and `temp_debug()`'s 4 call sites were never updated to pass it (`TypeError: get_old_row() missing 1 required positional argument: 'session'`). Fixed by adding the missing argument to all 4 calls.

**Important — the hook is hardcoded to the `upd_order_reuse` scenario specifically, not general-purpose.** `temp_debug()` assumes the transaction has exactly one dirty `OrderDetail` and one other dirty row; running it against any *other* test (e.g. enabling `bug_explore` globally and running the full `examples/nw/tests` suite) crashes with `AttributeError: 'NoneType' object has no attribute '_sa_instance_state'`, since `bug_explore[0]`/`[1]` stay `None` for transactions that don't touch `OrderDetail`. **Only enable `bug_explore` when running `test_upd_order_reuse.py` specifically** — verified working correctly when scoped that way: forcing `order_detail_first = True` (the historically-bad ordering) with the current fix in place still produces the correct result (`ALFKI: 1016.00→56.00`, `ANATR: 0→557.50`), confirming the `_should_defer_chaining()` fix holds even under the deliberately-forced adversarial ordering.

&nbsp;

## Why this belongs in CE, not just a code comment

- It's **silent** — no exception, no log line a casual reader would flag as an error (`Balance: [0E-10-->] -402.50` looks like normal adjustment-log output unless you know what to expect).
- It's **intermittent** — reproduced about half the time in the original investigation, which is exactly the failure mode that survives code review and ad hoc testing and only surfaces in production at volume (same shape of risk as the Kolk Oil/Utah aggregate-adjustment story in `dev-architecture.md`'s Design Lineage section — different mechanism, same "looks fine until it very much isn't" character).
- It's **easy to "simplify away"** by someone who reads `save_altered_parents()`, doesn't understand why the defer-check exists, and "cleans it up" — which is exactly why this writeup exists: so a future change to this method (or to `listeners.py`'s row-iteration logic) gets read against this history first, not rediscovered the hard way.

**Rule of thumb:** any change to `_should_defer_chaining()`/`save_altered_parents()`, `RowSets`/`submitted_row`/`processed_rows`, or how `listeners.py` iterates `session.dirty` needs to be re-tested against both `examples/nw/tests/test_should_defer_chaining.py` (fast, deterministic, logic-only) and `examples/nw/tests/test_upd_order_reuse.py` (the real integration repro) — and ideally the latter run with the `bug_explore` hook forcing `order_detail_first = True`, since the bug's ~50% natural reproduction rate means a single passing run with the hook disabled proves much less than it appears to.
