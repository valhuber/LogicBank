---
title: "1.34.0 Regression — insert_parent With a Partially Null Composite FK" — GitHub Issue #29 (Fixed)
Description: The #26 fix made Aggregate.adjust_from_inserted_child call _is_inserted_parent whenever no parent is found, without checking whether the child's composite FK was only PARTIALLY set (legitimately, permanently) rather than fully-but-late - inserted the parent with a null key column and crashed the flush
Source: logic_bank/rule_type/aggregate.py (Aggregate.adjust_from_inserted_child), logic_bank/exec_row_logic/logic_row.py (LogicRow._get_parent_logic_row)
Usage: Read before touching insert_parent handling in either file, or _is_foreign_key_null / _is_inserted_parent. Companion doc to composite_key_issue.md (ApiLogicServer-src) and the #26 fix (2d82734) this issue follows up on.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed via two coordinated changes (aggregate.py guard + logic_row.py short-circuit) - either alone is insufficient. Regression suite examples/insert_parent_partial_null_fk/.
---

# 1.34.0 Regression: `insert_parent` With a Partially Null Composite FK

## TL;DR

[GitHub issue #29](https://github.com/valhuber/LogicBank/issues/29): the fix for [#26](https://github.com/valhuber/LogicBank/issues/26) made `Aggregate.adjust_from_inserted_child` call `_is_inserted_parent()` whenever no parent is found for an `insert_parent=True` aggregate, on the premise that by the time the aggregate adjustment runs, the child's foreign key is *complete* — either set at construction, or by an `early_row_event` that runs before Row Logic. That premise holds for a **late-set-but-eventually-complete** key (`examples/insert_parent_late_key`, the #26 regression case). It does **not** hold for a composite key that is **legitimately, permanently partially null** — e.g. a free-text sales line with `product_id` null but `store_id` set. The new #26 call site didn't check for this case, so:

- The parent gets inserted anyway, with a `None` value in one of its composite-key columns, and the flush fails: `NOT NULL constraint failed: stock.product_id` (SQLite) / `Field 'product_id' doesn't have a default value` (MySQL).

The intended behavior was **already documented and implemented** elsewhere for exactly this case: `LogicRow._is_foreign_key_null()` treats *any* null column in a composite FK as "no parent to load" — the whole point of that method is to distinguish "legitimately no parent" from "parent reference that can't be resolved." The #26 call site simply didn't consult it before deciding to insert.

**Before 1.34.0** (i.e. before the #26 fix), the same scenario hit a *different*, older bug: the line was saved, but its non-null FK column (`store_id`) was silently wiped to `None` — a symptom of the same underlying "no parent found → `setattr(row, role_name, None)` nulls composite FK columns as a side effect" mechanism documented in `composite_key_issue.md` (ApiLogicServer-src). So this scenario has *never* worked correctly; #26 changed its failure mode from silent data loss to a loud crash, but didn't fix it.

**Fixed** via two coordinated changes — the issue is explicit that *either alone is insufficient*:

1. `Aggregate.adjust_from_inserted_child` (`rule_type/aggregate.py`) now also checks `not child_logic_row._is_foreign_key_null(relationship)` before calling `_is_inserted_parent()` — a partially-null FK never attempts to insert a parent.
2. `LogicRow._get_parent_logic_row` (`exec_row_logic/logic_row.py`) now short-circuits to a null parent (without attempting a query) when it detects a partially null composite FK — avoiding both a malformed query and the FK-column-wiping side effect of `setattr(row, role_name, None)` that the pre-1.34.0 behavior suffered from.

&nbsp;

## Why this is distinct from `examples/insert_parent_late_key` (#26)

| | `insert_parent_late_key` (#26) | This issue (#29) |
|---|---|---|
| FK state at construction | Fully null (not yet set) | Partially null |
| FK state by the time the aggregate adjusts | **Fully set** (an `early_row_event` set the missing column) | **Still partially null** — permanently, by design |
| Correct behavior | Insert the parent | Do NOT insert a parent; there is none |
| Failure before the respective fix | Silent: FK columns wiped to `None` | Silent (pre-1.34.0) or loud crash (1.34.0+) |

The #26 fix's premise — "if we get here with no parent found, the FK must be complete by now" — is true for the late-set case and false for the partially-null case. The two scenarios look identical at the point `adjust_from_inserted_child` runs (no parent found, `insert_parent=True`); the only way to tell them apart is to actually check `_is_foreign_key_null()`.

&nbsp;

## The concrete scenario

```python
Rule.sum(derive=Stock.sold, as_sum_of=SaleLine.qty, insert_parent=True)
```

`Stock(product_id, store_id)` composite natural key. `SaleLine.product_id` is nullable (free-text lines have no product); `SaleLine.store_id` is always set.

```
$ pip install logicbank==1.34.0
  line with product:    Stock(10, 2).sold = 3  expected 3 (parent inserted)     ok
  line without product: insert FAILED  expected the line saved and no parent inserted
    IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: stock.product_id

$ pip install logicbank==1.33.0
  line with product:    Stock(10, 2).sold = 3  expected 3 (parent inserted)     ok
  line without product: saved with store_id = None, stock rows = 1  expected store_id = 2, 1 stock row  WRONG
```

&nbsp;

## The fix

**1. `aggregate.py`, `Aggregate.adjust_from_inserted_child`** — add the `_is_foreign_key_null` check before attempting `_is_inserted_parent`:

```diff
                 if self.insert_parent:
                     child_mapper = object_mapper(parent_adjustor.child_logic_row.row)
                     relationship = child_mapper.relationships.get(self._parent_role_name)
                     if relationship is not None and \
+                            not parent_adjustor.child_logic_row._is_foreign_key_null(relationship) and \
                             parent_adjustor.child_logic_row._is_inserted_parent(relationship):
```

**2. `logic_row.py`, `LogicRow._get_parent_logic_row`** — short-circuit before querying, when a composite FK is partially (but not fully) null:

```diff
             parent_key = {}
             for each_child_col, each_parent_col in role_def.local_remote_pairs:
                 parent_key[each_parent_col.name] = getattr(row, each_child_col.name)
+            if len(role_def.local_remote_pairs) > 1 and None in parent_key.values():
+                # partially null composite FK: there is no parent to load, link or insert
+                old_parent = self._make_copy(None)
+                return LogicRow(row=None, old_row=old_parent, ins_upd_dlt="*",
+                                nest_level=1 + self.nest_level,
+                                a_session=self.session, row_sets=self.row_sets)
             parent_class = role_def.entity.class_
```

(`len(...) > 1` scopes this to composite keys only — a single-column FK that's null is the ordinary, already-correctly-handled "no parent" case; `None in parent_key.values()` with only one key means *fully* null, not *partially* null, and the existing code path already handles that correctly via the normal query-returns-None path.)

**Why both changes are needed:** the `aggregate.py` guard alone stops the *second* parent-insert attempt, but `_get_parent_logic_row`'s own query (`parent_query.get(parent_key)`, called with a `None` in the key dict) still runs first and either errors or returns `None` in a way that trips the FK-column-wiping `setattr(row, role_name, None)` side effect from the #26 fix. The `logic_row.py` short-circuit alone stops that side effect, but without the `aggregate.py` guard, `adjust_from_inserted_child` would still see "no parent" and still attempt `_is_inserted_parent()`, inserting a parent with a null key column.

&nbsp;

## Regression suite

`examples/insert_parent_partial_null_fk/` (Stock/SaleLine, matching the issue's own repro shape). Two tests:
- `test_full_key_still_inserts_parent` — baseline, confirms a fully-set composite FK still triggers `insert_parent` correctly (i.e. this fix doesn't regress the #26 case).
- `test_partially_null_key_saves_line_without_inserting_parent` — the actual regression: asserts the line saves with `store_id` intact and `product_id` still `None`, and that no `Stock` row is inserted at all.

Confirmed the second test fails against unfixed code with the exact `NOT NULL constraint failed: stock.product_id` error from the issue, and passes with the fix applied. Full suite (`run_tests.py`, all 20 example directories including `insert_parent`, `insert_parent_late_key`, and `concurrent_adjust`) re-confirmed green after the fix.

&nbsp;

## Context

Found by `alejandromyto` upgrading an ApiLogicServer/GenAI-Logic project from 1.33.0 to 1.34.0: its test suite caught the failed insert, and the project was pinned back to 1.33.0 pending this fix. See [GitHub issue #29](https://github.com/valhuber/LogicBank/issues/29) for the original repro script and diff.
