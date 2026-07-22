---
title: Dependency Scanning for Formulas and Constraints
Description: How LogicBank determines which attributes a Formula/Constraint depends on, for all three specification styles (as_exp, as_expression, calling) — and a real gap in coverage
Source: logic_bank/rule_type/abstractrule.py (parse_dependencies), logic_bank/rule_type/formula.py, logic_bank/rule_type/constraint.py
Usage: AI assistants read this before changing get_rule_text() / parse_dependencies() / get_referenced_attributes() on Formula or Constraint, or before assuming calling= functions are excluded from dependency analysis
version: 1.0
---

# Dependency Scanning for Formulas and Constraints

## How it works

`Formula` and `Constraint` both support three ways to specify logic: `as_exp` (string), `as_expression` (lambda), and `calling` (named function). All three are scanned for dependencies the same way:

1. `get_rule_text()` (`formula.py:92-99`, `constraint.py:60-66`) produces the **source text** of the rule — for `calling=`, this is `inspect.getsource(self._function)`, i.e. the actual Python source of the function body.
2. `AbstractRule.parse_dependencies()` (`abstractrule.py:67-89`) splits that text into whitespace/paren-separated tokens and treats any token starting with `"row."` as a dependency (`row.parent.attr` tokens also update parent-referring-children tracking).

So **`calling=` functions are scanned**, exactly like `as_exp`/`as_expression` — this is not a gap. Example (`examples/nw/logic/logic.py:88-91`):

```python
def units_in_stock(row: Product, old_row: Product, logic_row: LogicRow):
    result = row.UnitsInStock - (row.UnitsShipped - old_row.UnitsShipped)
    return result
Rule.formula(derive=Product.UnitsInStock, calling=units_in_stock)
```

`row.UnitsInStock` and `row.UnitsShipped` are correctly picked up as dependencies of this formula.

## Real gap #1: `old_row.` references are invisible

`parse_dependencies` only matches tokens starting with `"row."` — never `"old_row."`. In the example above, `old_row.UnitsShipped` on the same line is **not** recorded as a dependency, even though `row.UnitsShipped` on the same line is. This applies uniformly regardless of whether the source came from `calling=`, `as_exp`, or `as_expression` — it's not `calling=`-specific.

Practical impact: if a rule's *only* reference to some attribute is via `old_row.X` (no `row.X` anywhere), the dependency graph won't know this rule depends on `X`, which could affect pruning/ordering decisions that rely on `get_referenced_attributes()`.

## Real gap #2: scanning is textual, not AST/call-graph based

The scan is a naive substring/token match over the function's own source — it does not follow calls into helper functions. If a `calling=` function delegates real attribute access to a helper (`return compute(row)` instead of `return row.X + row.Y`), or aliases `row` to another variable name before accessing attributes (`r = row; ... r.X`), those dependencies are missed, because only the top-level function's literal source text is inspected — nothing it calls is walked.

**Documented workaround** (ratified, see [spurious-parent-dependency.md](spurious-parent-dependency.md)): because the scan reads `inspect.getsource()`'s complete text — comments included — a `# deps: row.parent.attr` comment directly in the `calling` function's body satisfies the scan exactly as if the reference appeared in executable code, restoring both pruning and parent-cascade registration. This is now the documented, supported fix for this gap (see the `Rule.formula` docstring in `logic_bank.py`), not merely an accident to route around some other way.

## Related: spurious dependencies from non-relationship chains (GitHub issue #21)

The mirror-image problem: a chained `row.X.Y` token where `X` is a real column (not a relationship) — e.g. `row.code.zfill(8)` — used to be wrongly registered as a *parent* dependency purely by node-counting, causing either a runtime crash on update or an activation-time failure for the entire rule set. Fixed via `AbstractRule._is_relationship_node()` — see [spurious-parent-dependency.md](spurious-parent-dependency.md) for the full root cause and fix.

## Where to look if extending this

- `logic_bank/rule_type/abstractrule.py::parse_dependencies` — the tokenizer itself
- `logic_bank/rule_type/formula.py::get_rule_text` / `Formula.get_referenced_attributes`
- `logic_bank/rule_type/constraint.py::get_rule_text` / `Constraint.get_referenced_attributes`
