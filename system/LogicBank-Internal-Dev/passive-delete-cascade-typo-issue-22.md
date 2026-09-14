---
title: _cascade_delete_children() Passed a Nonexistent Keyword Argument to LogicRow.delete() — Root Cause and Fix (GitHub issue #22)
Description: LogicRow._cascade_delete_children() called each_child_logic_row.delete(do_not_adjust=self) - a keyword the method's signature doesn't accept (it's do_not_adjust_list, a list). TypeError on every delete of a parent whose child relationship declares BOTH cascade="all, delete" AND passive_deletes=True. Fixed with a one-line correction, matching the sibling client-delete call site's existing usage.
Source: logic_bank/exec_row_logic/logic_row.py (_cascade_delete_children, delete)
Usage: Read before touching _cascade_delete_children(), LogicRow.delete()'s signature, or do_not_adjust_list/_is_in_list plumbing.
version: 1.0
changelog:
  - 1.0 (Jul 2026) - Reported as GitHub issue #22 by alejandromyto, with an exact traceback, line numbers, and the correct one-line fix already proposed. Confirmed repro against main before fixing (TypeError, exact message match). Applied the reporter's proposed fix verbatim after confirming it matches _is_in_list()'s List[LogicRow] contract and the sibling call site in listeners.py. Regression suite: examples/passive_delete_cascade/ (new - zero prior coverage of the cascade="all, delete" + passive_deletes=True combination anywhere in the repo, which is why this shipped unnoticed).
---

# _cascade_delete_children() Passed a Nonexistent Keyword Argument

## TL;DR

`LogicRow._cascade_delete_children()` called `each_child_logic_row.delete(reason=..., do_not_adjust=self)` — but `LogicRow.delete()`'s signature is `delete(self, reason=None, row=None, do_not_adjust_list=None)`. There is no `do_not_adjust` parameter, only `do_not_adjust_list` (plural, a `List[LogicRow]`). Every delete of a parent whose child relationship declares **both** `cascade="all, delete"` **and** `passive_deletes=True` — the only combination that routes through `_cascade_delete_children()` rather than the normal client-delete path — crashed with:

```
TypeError: LogicRow.delete() got an unexpected keyword argument 'do_not_adjust'. Did you mean 'do_not_adjust_list'?
```

**Fixed**: `do_not_adjust=self` → `do_not_adjust_list=[self]`, matching the sibling client-delete call site (`listeners.py`) and `_is_in_list()`'s existing `List[LogicRow]` contract.

&nbsp;

## Why this shipped unnoticed

`passive_deletes=True` tells SQLAlchemy "don't emit DELETE statements for these children yourself — the database's `ON DELETE CASCADE` will handle it." That's an opt-in, relatively rare combination: it requires the child relationship to declare both `cascade="all, delete"` *and* `passive_deletes=True`, and the underlying FK constraint to actually have `ondelete="CASCADE"` (plus, for SQLite specifically, `PRAGMA foreign_keys=ON` on every connection — SQLite ignores FK constraints, cascades included, by default).

Grepped every example in this repo for `passive_deletes`: several models declare it (`examples/tutorial`, `examples/referential_integrity`, `examples/insert_parent`, `examples/custom_exceptions`, `examples/payment_allocation`), but `examples/referential_integrity/db/models.py` is representative of all of them — `passive_deletes=True` is present only as a **commented-out** line, with the comment itself warning "use *only* when DBMS does the cascade delete":

```python
cascade="all")  # cascade delete
# , passive_deletes=True  use *only* when DBMS does the cascade delete
```

`_cascade_delete_children()`'s own docstring references `@see nw/tests/test_dlt_order.py` — that file doesn't exist in the repo. So the one code path meant to exercise this method was never actually built, and the method itself has had zero test coverage since (at latest) whenever that docstring was written. This is a straightforward, mechanical bug in genuinely dead-until-triggered code, not a design flaw — there's no subtlety here the way there is in the "dragons" or multi-relationship bug families.

&nbsp;

## The fix

`logic_row.py`, `_cascade_delete_children()`:

```python
# before
each_child_logic_row.delete(reason="Cascade Delete to run rules on - " + child_role_name,
                            do_not_adjust=self)

# after
each_child_logic_row.delete(reason="Cascade Delete to run rules on - " + child_role_name,
                            do_not_adjust_list=[self])
```

Confirmed correct against two things already in the codebase:

1. `LogicRow.delete()`'s actual signature: `delete(self, reason=None, row=None, do_not_adjust_list=None)`.
2. `_is_in_list(self, logic_rows: List) -> bool` (used by `save_altered_parents()` to check whether a parent should be skipped for adjustment) iterates its argument as a list of `LogicRow`s — `[self]` (the parent currently being deleted) is exactly the shape it expects, and matches how `listeners.py`'s client-delete loop builds `do_not_adjust_list` incrementally (`do_not_adjust_list = []`, then `.append(logic_row)` per deleted row) for the same purpose: preventing a sum/count adjustment from being applied to a parent that is itself in the process of being deleted.

&nbsp;

## Regression tests

`examples/passive_delete_cascade/` (new — `Order`/`OrderDetail`, `cascade="all, delete"` + `passive_deletes=True` + `ondelete="CASCADE"` on the FK, `PRAGMA foreign_keys=ON` enabled per-connection for SQLite):

- `test_gold_seed_data_is_correct` — baseline, `Rule.sum`-derived `amount_total` correct for both seeded orders.
- `test_delete_parent_cascades_via_passive_deletes` — the exact repro: delete an `Order`, commit. Previously raised `TypeError`; now both the `Order` and its `OrderDetail`s are cleanly gone.
- `test_delete_one_parent_leaves_sibling_order_untouched` — deleting one `Order` doesn't affect a sibling `Order`'s `amount_total` or `OrderDetail`s, confirming `do_not_adjust_list=[self]` scopes correctly and doesn't over-suppress adjustments.

Confirmed the first two tests fail (`TypeError`) against the unfixed code and pass with the fix. Full repo suite (`python3 run_tests.py`) — zero regressions, all 14 example dirs pass.
