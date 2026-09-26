---
title: "Parent-to-Child Cascade Silently Skipped When the Parent Has No Rules of Its Own" — GitHub Issue #33 (Fixed)
Description: get_referring_children returned {} whenever the parent class itself had no declared rules, even though the dependency it needed to find lives on the CHILD's rules - so a child formula referencing a parent attribute stopped being recomputed when that attribute changed, silently, as long as the parent had no rules
Source: logic_bank/rule_bank/rule_bank_withdraw.py (get_referring_children)
Usage: Read before touching get_referring_children, or assuming a class absent from rule_bank.orm_objects has nothing worth doing in a parent-cascade path.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by registering an empty TableRules for the parent instead of returning early. Regression suite examples/cascade_parent_without_rules/.
---

# Parent-to-Child Cascade Silently Skipped When the Parent Has No Rules of Its Own

## TL;DR

[GitHub issue #33](https://github.com/valhuber/LogicBank/issues/33): a child formula that references a parent attribute (`row.Order.shipped_date`) is normally recomputed when that attribute changes on the parent — `LogicRow._parent_cascade_attribute_changes_to_children` collects the referring children via `get_referring_children` (`rule_bank/rule_bank_withdraw.py`), which starts with:

```python
def get_referring_children(parent_logic_row: LogicRow) -> dict:
    rule_bank = RuleBank()
    if parent_logic_row.name not in rule_bank.orm_objects:
        return {}                     # <-- parent has no rules of its own
    else:
        parent_rules = rule_bank.orm_objects[parent_logic_row.name]
        ...
```

`rule_bank.orm_objects` only has the classes that rules were declared **on**. When the parent class has no rules of its own, the function returns `{}` immediately — without ever reaching the part of the function that inspects the *child's* rules, which is where the dependency (`row.Order.shipped_date`) actually lives. The cascade never happens.

Nothing fails: the child keeps its stale value, and the only way to notice is comparing against what the derivation should have produced.

**What makes this easy to miss:** any unrelated rule on the parent hides it. A single `Rule.constraint`, a `commit_row_event` used for auditing — anything — puts the class into `orm_objects` and the cascade starts working again. `_is_parent_cascading`, the other half of the mechanism, does not depend on the parent having rules — it reads the `reason` string. Only this lookup does, which is why the bug can survive undetected in a project where every parent happens to have *some* rule, until one doesn't.

**Fixed:** register an empty `TableRules` for the parent instead of returning early, so the loop that inspects the child's rules always runs.

&nbsp;

## The concrete scenario

```python
def detail_shipped_date(row, old_row=None, logic_row=None):
    """Copy of the parent's shipped date"""
    return row.Order.shipped_date

Rule.formula(derive=OrderDetail.shipped_date, calling=detail_shipped_date)
```

with `Order` declaring no rules of its own:

```
insert detail:                       shipped_date = '2026-01-01'  expected '2026-01-01'         ok
parent shipped_date -> 2026-02-02:   child = '2026-01-01'  expected '2026-02-02'  STALE - cascade was skipped
```

Adding one unrelated formula on `Order` (returning its own unchanged value, changing nothing about the dependency) is enough to fix the symptom:

```
parent shipped_date -> 2026-02-02:   child = '2026-02-02'  expected '2026-02-02'  ok
```

— which is what points at the lookup, not the dependency-tracking logic itself, as the actual cause.

&nbsp;

## The fix

```diff
-from logic_bank.rule_bank.rule_bank import RuleBank
+from logic_bank.rule_bank.rule_bank import RuleBank, TableRules

 def get_referring_children(parent_logic_row: LogicRow) -> dict:
     rule_bank = RuleBank()
     if parent_logic_row.name not in rule_bank.orm_objects:
-       return {}
-    else:
-        parent_rules = rule_bank.orm_objects[parent_logic_row.name]
+        rule_bank.orm_objects[parent_logic_row.name] = TableRules()
+    parent_rules = rule_bank.orm_objects[parent_logic_row.name]
```

(with the rest of the former `else` body de-indented to match). A parent with no rules and no referring children still returns an empty dict — just via the same code path every other parent uses, one entry heavier in `orm_objects` from then on.

&nbsp;

## A gotcha when reproducing this (not a bug — noted for anyone re-deriving the repro)

The parent must be reloaded (`session.refresh(order)`) before the attribute that's about to be cascaded is updated. If it's still expired from a prior commit when you assign to it, SQLAlchemy's `old_row` snapshot for that flush ends up holding the *new* value already, and the cascade is skipped for an entirely unrelated reason (there's no detectable change from `old_row`'s point of view). Easy to conflate with this bug if you don't control for it.

&nbsp;

## Regression suite

`examples/cascade_parent_without_rules/` (`Order`/`OrderDetail`, matching the issue's own repro shape — `Order` declares no rules of its own). Two tests: `test_insert_copies_parent_shipped_date` (baseline) and `test_update_on_parent_without_rules_still_cascades` (the actual regression — updates `Order.shipped_date` after a `session.refresh`, asserts the child picks it up). Confirmed the second test fails (stale child value) against unfixed code, and passes with the fix applied.

&nbsp;

## Context

See [GitHub issue #33](https://github.com/valhuber/LogicBank/issues/33) for the original repro script (`repro_cascade_parent_without_rules.py`), including its `--with-parent-rule` flag that demonstrates the masking behavior directly.
