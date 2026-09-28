---
title: "Pessimistic Locking Loses Same-Flush Adjustments and Nulls a Relationship-Linked FK" — GitHub Issues #36, #37 (Fixed)
Description: With trans_update_locking="pessimistic", LogicRow._get_parent_logic_row's locking read (a) unconditionally overwrote an already-adjusted, not-yet-flushed parent with the stale DB value on every subsequent child in the same flush (#36), and (b) built its parent key only from the child's FK column, which SQLAlchemy has not yet populated for a parent assigned through the relationship - silently nulling the child's own FK (#37)
Source: logic_bank/exec_row_logic/logic_row.py (LogicRow._get_parent_logic_row, LogicRow._refresh_locked_parent), logic_bank/exec_trans_logic/row_sets.py (RowSets.locked_parents)
Usage: Read before touching _get_parent_logic_row, its use_locking_read/populate_existing() path, or RowSets - especially together with pessimistic-locking-insert-parent-issue-30.md, which fixed the sibling case (a parent NOT yet in the database at all).
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed #36 via LogicRow._refresh_locked_parent + RowSets.locked_parents (skip populate_existing() after a parent's first locking read in the flush). Fixed #37 via a fallback to the related object when the FK-derived parent_key is still None. Regression suites examples/pessimistic_multi_child_adjust/, examples/pessimistic_relationship_parent/.
---

# Pessimistic Locking Loses Same-Flush Adjustments and Nulls a Relationship-Linked FK

## TL;DR

Two related bugs in the same method, both only visible with `trans_update_locking="pessimistic"`, both silent (no exception, wrong data):

- **[GitHub issue #36](https://github.com/valhuber/LogicBank/issues/36)**: a second child adjusting the same parent in one flush loses the first child's adjustment.
- **[GitHub issue #37](https://github.com/valhuber/LogicBank/issues/37)**: a child linked to an *existing* parent through the relationship (`Order(customer=customer)`, not by setting the FK column) gets its FK nulled and the parent is never adjusted.

Both live in `LogicRow._get_parent_logic_row` (`exec_row_logic/logic_row.py`), the method every `Rule.sum`/`Rule.count` adjustment calls with `for_update=True` under pessimistic locking. Both are now fixed; `run_tests.py` still reports `ALL PASSED` (26/26, including the two new suites).

&nbsp;

## Issue #36 — same-flush adjustment lost to `populate_existing()`

### The bug

```python
if use_locking_read:
    parent_query = parent_query.with_for_update().populate_existing()
parent_row = parent_query.get(parent_key)
```

`populate_existing()` forces the query to overwrite whatever is already in the session's identity map with the freshly-read database row — on **every** call, not just the first. When a second child of the same parent is adjusted in the same flush, the parent is already in the session carrying the first child's adjustment (an in-memory `setattr`, not yet flushed). The locking read for the second child re-fetches the parent from the database — which does not yet reflect the first child's unflushed change — and `populate_existing()` stamps that stale value straight over the pending one. No error; the first adjustment simply disappears. Two orders of 3 and 5 summed into the same customer's balance, committed together, left the balance at 5 instead of 8.

The same mechanism discards a client-side edit to the parent made in the same transaction as a new child (e.g., editing a customer's name alongside adding an order): the refresh isn't scoped to LogicBank's own adjusted columns, it's a blanket overwrite of the whole row.

With the default `trans_update_locking="ignored"`, neither the locking read nor `populate_existing()` happens, so this path isn't exercised — the bug is specific to pessimistic mode.

### The fix

Only the **first** locking read of a given parent in a flush should refresh it from the database; every subsequent read in the same flush should keep whatever is already in memory (LogicBank's adjustments, or the client's own edits) and just re-issue `with_for_update()` for the lock itself, without `populate_existing()`.

`RowSets` (`exec_trans_logic/row_sets.py`) gained a per-flush set of already-locked parent identities:

```python
self.locked_parents = set()  # identity keys of parents already read with a lock in this flush (issue #36)
```

`LogicRow` gained `_refresh_locked_parent`, called from `_get_parent_logic_row` in place of an unconditional `populate_existing()`:

```python
def _refresh_locked_parent(self, parent_class, parent_key) -> bool:
    mapper = inspect(parent_class)
    try:
        identity = mapper.identity_key_from_primary_key(
            tuple(parent_key[col.name] for col in mapper.primary_key))
    except KeyError:  # the FK points to a key that is not the primary key
        return True
    if identity in self.row_sets.locked_parents:
        return False
    self.row_sets.locked_parents.add(identity)
    parent = self.session.identity_map.get(identity)
    if parent is None or not self.session.is_modified(parent, include_collections=False):
        return True
    unchanged = [attr.key for attr in inspect(parent).attrs
                 if attr.key in mapper.column_attrs and not attr.history.has_changes()]
    self.session.refresh(parent, attribute_names=unchanged, with_for_update=True)
    return False
```

and the call site:

```python
if use_locking_read:
    parent_query = parent_query.with_for_update()
    if self._refresh_locked_parent(parent_class, parent_key):
        parent_query = parent_query.populate_existing()
parent_row = parent_query.get(parent_key)
```

Three cases:
1. **Parent not yet in the session, or in the session with no pending changes** — `_refresh_locked_parent` returns `True`, the caller does its own `populate_existing()` exactly as before (needed so a stale copy from earlier relationship navigation is replaced by the locked read).
2. **Parent already locked once this flush** — returns `False` immediately; no refresh, no `populate_existing()`. Whatever is in memory (already adjusted) stands.
3. **Parent's first locking read this flush, but it already has pending changes** (from an earlier adjustment or a client edit, in the SAME transaction, before this first locking read) — `session.refresh(..., attribute_names=unchanged, with_for_update=True)` refreshes only the columns that have **no** pending change, under the lock, and returns `False` so the caller skips its own `populate_existing()`.

Case 3 deliberately does *not* try to detect a concurrent external change to a column the client already modified before its first locking read — that's the same race #25/pessimistic-locking-concurrent-adjust already exists to close via the lock itself; a column the client changed is written through as it would be without LogicBank.

&nbsp;

## Issue #37 — relationship-linked existing parent gets its FK nulled

### The bug

```python
parent_key = {}
for each_child_col, each_parent_col in role_def.local_remote_pairs:
    parent_key[each_parent_col.name] = getattr(row, each_child_col.name)
...
parent_row = parent_query.get(parent_key)
...
setattr(row, role_name, parent_row)   # parent_row is None -> detaches the child
```

When a child is linked to its parent via the relationship attribute (`Order(customer=customer)` or `customer.OrderList.append(order)`) rather than by setting the FK column directly, SQLAlchemy does not copy the parent's key into the child's FK column until flush time. Before that, `getattr(row, each_child_col.name)` — reading the still-unset FK column — returns `None`. The locking read then queries with a `None` key, finds nothing, and the `setattr(row, role_name, None)` a few lines later (taken because `parent_row is None`) nulls the relationship — which for LogicBank's bookkeeping detaches the child from a parent that is, in fact, real and already in the database. No error; the order silently loses its customer and the balance is never adjusted.

This is the same *shape* of problem #30 fixed — a locking read finding no parent when one genuinely exists — but the opposite *cause*: #30's parent wasn't in the database yet (`insert_parent` had just created it, same transaction); #37's parent **is** in the database, it's just that the FK column hasn't been populated from the relationship yet.

### The fix

When the FK-derived key comes up empty but the relationship attribute already holds a parent object, fall back to reading the key from that object directly:

```python
parent_key = {}
for each_child_col, each_parent_col in role_def.local_remote_pairs:
    parent_key[each_parent_col.name] = getattr(row, each_child_col.name)
related = vars(row).get(role_name)  # parent assigned through the relationship: FK not set until flush (issue #37)
if related is not None and None in parent_key.values():
    for each_child_col, each_parent_col in role_def.local_remote_pairs:
        parent_key[each_parent_col.name] = getattr(
            related, role_def.mapper.get_property_by_column(each_parent_col).key)
```

`vars(row).get(role_name)` (not `getattr`) avoids triggering a lazy load and reads exactly what's already assigned on the instance. It only activates when the FK-derived key has a `None` component AND the relationship holds something — a child linked purely by FK column, or with no parent at all, takes the same path as before.

&nbsp;

## Regression suites

- `examples/pessimistic_multi_child_adjust/` (issue #36) — Customer/Order, `Rule.sum(Customer.balance, as_sum_of=Order.amount)`. Two orders for the same customer committed in one flush must both land in the balance (not just the last one); a client edit to the customer's name made alongside a third order, same transaction, must also survive. Both `ignored` and `pessimistic` modes run as separate subprocesses (`RuleBank` is a process-wide singleton — see `pessimistic-locking-insert-parent.md` for why).
- `examples/pessimistic_relationship_parent/` (issue #37) — Customer/Order, same rule. An order is linked to an *existing*, already-committed customer via `Order(customer=customer)` rather than `customer_id=`. Asserts the FK is populated and the balance is adjusted under `pessimistic`; `ignored` runs as a baseline.

Confirmed both suites fail against unfixed code (`pessimistic_multi_child_adjust`: balance stops at 5 instead of 8, or the client's name edit reverts; `pessimistic_relationship_parent`: `customer_id` comes back `None` and balance stays 0) and pass with the fixes applied. `run_tests.py` gives `ALL PASSED` (26/26) with both fixes in place.

&nbsp;

## Context

See [GitHub issue #36](https://github.com/valhuber/LogicBank/issues/36) and [GitHub issue #37](https://github.com/valhuber/LogicBank/issues/37) for the original repro scripts and suggested diffs. See also `pessimistic-locking-insert-parent.md` (issue #30, the sibling "parent not yet in the database" case) and `concurrent_adjust`/issue #25 for the locking mechanism these fixes must not weaken.
