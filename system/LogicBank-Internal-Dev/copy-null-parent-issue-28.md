---
title: "Rule.copy Raises AttributeError on a Null Optional Parent FK" — GitHub Issue #28 (Fixed)
Description: Copy.execute assumed parent_logic_row.row was never None - crashed the whole transaction on a legitimately-null optional parent FK, instead of leaving the copied column None like the rest of the engine already does for this case
Source: logic_bank/rule_type/copy.py (Copy.execute)
Usage: Read before touching Copy.execute or assuming parent_logic_row.row is always non-None in a Rule.copy path.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed via a None guard around the getattr/setattr. Regression suite examples/copy_null_parent/.
---

# `Rule.copy` Raises `AttributeError` on a Null Optional Parent FK

## TL;DR

[GitHub issue #28](https://github.com/valhuber/LogicBank/issues/28): `Copy.execute` (`rule_type/copy.py`) did

```python
each_column_value = getattr(parent_logic_row.row, self._from_column)
```

unconditionally. When the child's foreign key is null — a legitimately-absent optional parent, e.g. a free-text order line with no product — `parent_logic_row.row` is `None`, and the insert crashes:

```
AttributeError: 'NoneType' object has no attribute 'tax_rate'
```

A null optional parent is already a *supported* case elsewhere in the engine: every `adjust_from_*` method in `aggregate.py` checks `parent_logic_row.row is None` and skips the adjustment rather than crashing. `Rule.copy` was the one rule type that didn't follow that pattern.

**Fixed:** guard both the `getattr` (reading from the parent) and the `setattr` (writing to the child) with a `None` check — if there's no parent, the copied column is simply left `None`, exactly like the aggregate path already does.

&nbsp;

## The concrete scenario

```python
Rule.copy(derive=OrderLine.tax_rate, from_parent=Product.tax_rate)
```

with `OrderLine.product_id` nullable, to support order lines with no product (a free-text line item):

```
line with product:    tax_rate = 21  expected 21                          ok
line without product: insert FAILED, expected tax_rate = None
Traceback (most recent call last):
  ...
  File ".../logic_bank/rule_type/copy.py", line 60, in execute
    each_column_value = getattr(parent_logic_row.row, self._from_column)
AttributeError: 'NoneType' object has no attribute 'tax_rate'
```

Any commit involving an `OrderLine` with `product_id=None` fails outright — not because of a constraint violation the application should see, but because `Rule.copy`'s own execution crashes before the transaction can even reach a constraint check.

&nbsp;

## The fix

```diff
     def execute(self, child_logic_row: LogicRow, parent_logic_row: LogicRow):
         AbstractRule.execute(self, child_logic_row)
-        each_column_value = getattr(parent_logic_row.row, self._from_column)
+        parent_row = parent_logic_row.row if parent_logic_row is not None else None
+        each_column_value = getattr(parent_row, self._from_column) if parent_row is not None else None
         setattr(child_logic_row.row, self._column, each_column_value)
```

The `parent_logic_row is not None` check (in addition to `parent_logic_row.row is not None`) is defensive — nothing in the current call path passes `parent_logic_row=None` itself (only `.row` can be `None`), but it matches the same defensive shape the issue's own patch used and costs nothing.

With the fix, the null-parent case correctly leaves `tax_rate` as `None`:

```
line with product:    tax_rate = 21  expected 21                          ok
line without product: tax_rate = None  expected None                      ok
```

&nbsp;

## A secondary observation from the issue (not acted on)

> With it applied, SQLAlchemy still warns `fully NULL primary key identity cannot load any object` (`LogicRow._get_parent_logic_row`), so skipping the parent lookup entirely for a known-null foreign key may be worth considering too.

This is a performance/noise observation, not a correctness bug — the lookup still correctly resolves to no parent, it's just doing a `.get()` call SQLAlchemy warns about rather than short-circuiting earlier. Left as a possible future optimization, not part of this fix; see `insert-parent-partial-null-fk-issue-29.md` for a related, but distinct, short-circuit that *was* needed for correctness in a different call path (`_get_parent_logic_row`'s own composite-FK query, not `Copy.execute`).

&nbsp;

## Regression suite

`examples/copy_null_parent/` (Product/OrderLine, matching the issue's own repro shape). Two tests: `test_copy_with_product_still_works` (baseline) and `test_copy_with_null_parent_does_not_raise` (the actual regression — asserts the commit succeeds and `tax_rate` stays `None`). Confirmed `test_copy_with_null_parent_does_not_raise` fails with the exact `AttributeError` from the issue against unfixed code, and passes with the fix applied.

&nbsp;

## Context

Found by `alejandromyto` while porting CA Live API Creator rules to ApiLogicServer/GenAI-Logic: a LAC parent copy with no parent stores null, which is what allows saving a free-text sales line with no product. See [GitHub issue #28](https://github.com/valhuber/LogicBank/issues/28) for the original repro script.
