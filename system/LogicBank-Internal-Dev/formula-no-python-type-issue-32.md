---
title: "Rule.formula Raises NotImplementedError on a Column With No python_type" — GitHub Issue #32 (Fixed)
Description: Formula.execute read the column's SQLAlchemy type.python_type unconditionally whenever a recomputed value equaled the old value, to detect and reset a stray float - crashing the flush for column types (e.g. MySQL BIT) that don't implement python_type, on SQLAlchemy versions where the default raises NotImplementedError instead of returning object
Source: logic_bank/rule_type/formula.py (Formula.execute)
Usage: Read before touching Formula.execute's float-reset branch or assuming every SQLAlchemy column type implements .type.python_type.
version: 1.0
changelog:
  - 1.0 (Sep 2026) - Initial writeup. Fixed by moving the type inspection inside the float guard. Regression suite examples/formula_no_python_type/.
---

# `Rule.formula` Raises `NotImplementedError` on a Column With No `python_type`

## TL;DR

[GitHub issue #32](https://github.com/valhuber/LogicBank/issues/32): `Formula.execute` (`rule_type/formula.py`) reads the column type before looking at whether it's even relevant:

```python
else:
    inspector = sqlalchemy.inspect(logic_row.row)
    mapper = inspector.mapper
    old_value_type = str(type(old_value))
    col_type = mapper.columns[self._column].type.python_type    # <-- read unconditionally
    if 'float' in old_value_type and 'Float()' not in str(col_type):
```

This `else` branch runs whenever the freshly-computed value equals the old value — i.e. the formula is a no-op for this flush. The comment above it explains its actual purpose: loaded test data might have accidentally stored a `float` in a column that should be `Numeric`, and this branch resets the type. But `col_type = ... .type.python_type` executes on *every* no-op recompute, not just when `old_value` is a float — and `TypeEngine.python_type` raises `NotImplementedError` for column types that don't implement it (MySQL `BIT` is the concrete case in the issue) on SQLAlchemy versions prior to 2.1, where the default implementation raised rather than returning `object`.

So any commit that recomputes such a column to the value it already had crashes the flush. For a boolean-shaped column that's the common path: two different inputs both derive to `True`.

**Fixed:** move the type inspection inside the `'float' in old_value_type` guard — the only case that needs it. A no-op recompute of a non-float column now skips the `inspect`/`mapper`/`python_type` lookup entirely.

&nbsp;

## The concrete scenario

```python
def is_active(row, old_row=None, logic_row=None):
    """Active while the code starts with A"""
    code = row.code
    return bool(code) and code.startswith('A')

Rule.formula(derive=Item.is_active, calling=is_active)
```

with `Item.is_active` a MySQL `BIT(1)` column. Updating `code` from `'A1'` to `'A2'` — a dependency of the formula — still derives `True`:

```
insert code=A1:  is_active = 1  expected 1                                ok
update code=A2:  commit FAILED with NotImplementedError, expected is_active = 1
Traceback (most recent call last):
  ...
  File ".../logic_bank/rule_type/formula.py", line 79, in execute
    col_type = mapper.columns[self._column].type.python_type
  File ".../sqlalchemy/sql/type_api.py", line 649, in python_type
    raise NotImplementedError()
NotImplementedError
```

The exception escapes the flush; in an API context that's a 500 with an empty body and a traceback in `type_api.py`, not something the application constraint layer ever sees.

This is version-dependent: SQLAlchemy 2.1 changed `TypeEngine.python_type`'s default to return `object` instead of raising (`versionchanged:: 2.1`), so the crash only reproduces on SQLAlchemy `>=2.0.48,<2.1` — which is the range this project's `pyproject.toml` actually targets. Anyone testing against a newer SQLAlchemy alone would not see it fail.

&nbsp;

## The fix

```diff
-        else:                                                           # In loading test data, 
-            inspector = sqlalchemy.inspect(logic_row.row)               # the loaded data might be wrongly float,    
-            mapper = inspector.mapper                                   # which can fail in constraints.
-            old_value_type = str(type(old_value))                       # So, if the old value is Float,
-            col_type = mapper.columns[self._column].type.python_type    # and the column is Numeric...
-            if 'float' in old_value_type and 'Float()' not in str(col_type):
-                setattr(logic_row.row, self._column, value)
-                logic_row.log(f'Formula reset type {self._column}')     # reset the type to be Numeric, not Float
+        else:                                                           # In loading test data,
+            old_value_type = str(type(old_value))                       # the loaded data might be wrongly float,
+            if 'float' in old_value_type:                               # which can fail in constraints.
+                inspector = sqlalchemy.inspect(logic_row.row)           # So, if the old value is Float,
+                mapper = inspector.mapper
+                col_type = mapper.columns[self._column].type.python_type    # and the column is Numeric...
+                if 'Float()' not in str(col_type):
+                    setattr(logic_row.row, self._column, value)
+                    logic_row.log(f'Formula reset type {self._column}')     # reset the type to be Numeric, not Float
```

With the fix, the update case is a clean no-op:

```
insert code=A1:  is_active = 1  expected 1                                ok
update code=A2:  is_active = 1  expected 1  ok
```

Also worth noting: `_all_defaults` (`exec_row_logic/logic_row.py`, ~line 1016) reads `.type.python_type` the same unconditional way, reachable only with `all_defaults=True`. Not touched here (not covered by the issue's repro or this fix), but the same class of failure would apply to it on the same SQLAlchemy range if that path is exercised against a `python_type`-less column. `get_default_for_type` already wraps its own read in a `try/except`.

&nbsp;

## Regression suite

`examples/formula_no_python_type/` (`Item.is_active`, a MySQL `BIT(1)` column derived from `Item.code`). Table is created with raw DDL (`BIT` has no SQLite compiler) rather than `Base.metadata.create_all`, matching the issue's own repro shape. Two tests: `test_insert_sets_derived_value` (baseline) and `test_update_with_unchanged_derived_value_does_not_raise` (the actual regression — an update that changes a dependency but not the derived value). Confirmed the second test fails with the exact `NotImplementedError` from the issue against unfixed code (on SQLAlchemy 2.0.54; not reproducible on 2.1+, see above), and passes with the fix applied.

&nbsp;

## Context

See [GitHub issue #32](https://github.com/valhuber/LogicBank/issues/32) for the original repro script (`repro_formula_no_python_type.py`), which drives the same scenario without any test framework or ApiLogicServer involved.
