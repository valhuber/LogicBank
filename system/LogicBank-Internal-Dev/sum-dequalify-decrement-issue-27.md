---
title: "Rule.sum Decrements by the Wrong Value When a Child Stops Meeting where" — GitHub Issue #27 (Fixed)
Description: Aggregate.adjust_from_updated_child's "no longer meets where" branch decremented by the child's NEW summed value instead of the OLD one - silently wrong whenever the same update both dequalifies a child and changes the summed attribute
Source: logic_bank/rule_type/aggregate.py (Aggregate.adjust_from_updated_child)
Usage: Read before touching adjust_from_updated_child or any of the four delta-computation branches in it (where&&old_where / not-where&&not-old_where / where-only / old_where-only).
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed via one-line change (delta = -old_summed_field instead of -summed_field). Regression suite examples/sum_dequalify/.
---

# `Rule.sum` Decrements by the Wrong Value When a Child Stops Meeting `where`

## TL;DR

[GitHub issue #27](https://github.com/valhuber/LogicBank/issues/27): `Aggregate.adjust_from_updated_child` (`rule_type/aggregate.py`) has four branches depending on whether a child met the `where` clause before and after an update. The "no longer meets `where`" branch (child qualified before, doesn't now) decremented the parent by the child's **new** summed value:

```python
else:  # no longer meets where - decrement
    delta = - summed_field   # WRONG - summed_field is the NEW value
```

But what the parent's running total holds is a sum built from the child's **old** contribution. If the same update changes both the `where`-tested attribute and the summed attribute in one statement — which happens whenever the summed value is itself derived from the qualifying attribute — the parent drifts by `old - new`, silently, with no error.

**Fixed:** decrement by `old_summed_field` (already computed and defaulted to 0 earlier in the method) instead of `summed_field`.

&nbsp;

## The concrete scenario

```python
Rule.formula(derive=OrderLine.amount,
             as_expression=lambda row: row.qty * row.price * (100 - row.discount) // 100)
Rule.sum(derive=Order.undiscounted_total, as_sum_of=OrderLine.amount,
         where=lambda row: row.discount == 0)
```

A total of undiscounted line amounts. `amount` is a formula of `discount` — so changing `discount` changes both the `where` clause's answer AND the summed value in the same update.

```
insert qty=2 price=100 discount=0   (amount 200)          undiscounted_total =  200  expected  200  ok
update discount=10                  (amount 180, stops qualifying)
                                                            undiscounted_total =   20  expected    0  WRONG
update discount=0                   (amount 200, qualifies again)
                                                            undiscounted_total =  220  expected  200  WRONG
```

Walking through the buggy code: on the `discount 0 → 10` update, `summed_field` (new) is 180, but the parent's total still reflects the child's **old** contribution of 200. `delta = -180` leaves `200 - 180 = 20` instead of the correct `200 - 200 = 0`. The error compounds on the next update too (`220` instead of `200`), since the total is now permanently off by the accumulated drift.

&nbsp;

## The fix

```diff
             elif where:
                 delta = summed_field
-            else:  # no longer meets where - decrement
-                delta = - summed_field
+            else:  # no longer meets where - decrement by the value the parent still holds (old), not new
+                delta = - old_summed_field
```

`old_summed_field` is already computed and defaulted to `0` at the top of `adjust_from_updated_child` (via `get_old_summed_field()`), so no new plumbing was needed — the fix is a one-line correction to use a value the method already had in hand.

The other three branches were already correct:
- `where and old_where` (still qualifies): `delta = summed_field - old_summed_field` — correct, nets the change.
- `not where and not old_where` (never qualified): `delta = 0.0` — correct, nothing to adjust.
- `where` only, i.e. newly qualifies (`not old_where`): `delta = summed_field` — correct, the child wasn't contributing before, so the full new value is the delta.

Only the "no longer qualifies" branch had the old/new value swapped.

&nbsp;

## Why the existing test suite didn't catch it

No existing `Rule.sum` `where=` example had the summed attribute *itself* depend on the attribute the `where` clause tests. `examples/nw`'s `where=lambda row: row.ShippedDate is None` (unpaid-order balance) tests `ShippedDate`, which has no bearing on `AmountTotal` — dequalifying an order (setting `ShippedDate`) never simultaneously changes its `AmountTotal` in the same update, so this exact interaction never fired.

&nbsp;

## Regression suite

`examples/sum_dequalify/` (Order/OrderLine, matching the issue's own repro shape). `test_dequalify_decrements_by_old_value` walks the exact insert → dequalify → requalify sequence from the issue and asserts the correct totals (200 → 0 → 200) at each step. Confirmed the test fails against the unfixed code with the exact same wrong value (`20 != 0`) reported in the issue, and passes with the fix applied.

&nbsp;

## Context

Found by `alejandromyto` while porting CA Live API Creator rules to ApiLogicServer/GenAI-Logic: LAC decrements by the old value in the equivalent code path. See [GitHub issue #27](https://github.com/valhuber/LogicBank/issues/27) for the original repro script.
