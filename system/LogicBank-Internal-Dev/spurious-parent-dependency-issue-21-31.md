---
title: parse_dependencies Registered Spurious Parent References — Root Cause and Fix (GitHub issue #21)
Description: A 3+-node row.X.Y token was registered as a parent dependency whether or not X was an actual relationship - a chained method call on a plain column (row.code.zfill(8)) or a paren-stripping artifact from a sub-query (row.id_customer).scalar()) parsed identically to a real parent reference (row.customer.name). Fixed by checking the middle node against the mapper's real relationships before keeping the dependency. Also documents the `# deps:` comment convention for calling= formulas whose parent access happens inside a helper function.
Source: logic_bank/rule_type/abstractrule.py (AbstractRule.parse_dependencies, _is_relationship_node), logic_bank/rule_bank/rule_bank_setup.py (find_missing_attributes), logic_bank/exec_row_logic/logic_row.py (_get_parent_role_def)
Usage: Read before touching parse_dependencies, _is_relationship_node, or find_missing_attributes. Read before deciding whether a calling= Formula needs a `# deps:` comment.
version: 1.0
changelog:
  - 1.0 (Jul 2026) - Reported as GitHub issue #21 by alejandromyto, with a self-contained, accurate repro and root-cause analysis (correctly identified as "the unfinished half of #14" - the node-count check #14 added never verifies the middle node is a real relationship). Confirmed both repro cases against main before fixing. Fixed via AbstractRule._is_relationship_node(): a 3+-node token is only kept as a dependency if the middle node is an actual SQLAlchemy relationship. Regression suite: examples/spurious_parent_dependency/. Separately, ratified (documented, did not change code for) the `# deps:` comment convention the issue also raised.
---

# parse_dependencies Registered Spurious Parent References

## TL;DR

`AbstractRule.parse_dependencies()` (shared by `Formula`, `Constraint`/`CommitConstraint`, and `Aggregate.where=`) extracted a 3+-node token like `row.X.Y` as a parent dependency (`X.Y`) purely by counting dots — it never checked whether `X` was an actual SQLAlchemy relationship on the mapped class. Two harmful accidents followed, both reported with accurate, minimal repros in [GitHub issue #21](https://github.com/valhuber/LogicBank/issues/21):

- **`row.code.zfill(8)`** (a `str` method call on a plain column) parsed to dependency `code.zfill`. Activation succeeded (`code` is a real column, so `find_missing_attributes` didn't flag it), but every subsequent `UPDATE` crashed: `_is_formula_pruned` → `_is_different_parent` → `_get_parent_role_def` treated `code` as a parent role name and raised `Exception("FIXME invalid role name code")`.
- **`... != row.id_customer).scalar()`** (a sub-query inside a `Constraint`'s `calling=` function) parsed to dependency `id_customer).scalar` — `parse_dependencies`'s paren-stripping only strips *leading* `(`/*trailing* `)`,`,`, so a `)` embedded mid-token survives. `id_customer)` isn't a real attribute, so `find_missing_attributes` flagged it as missing, and `LogicBank.activate()` raised `LBActivateException` — **killing activation of the entire rule set**, not just the offending rule.

Fixed: a 3+-node token is now only kept as a dependency if the middle node (`code`, `id_customer)`, `customer`, ...) is an actual relationship on the mapped class.

&nbsp;

## Why this is "the unfinished half of #14"

[GitHub issue #14](https://github.com/valhuber/LogicBank/issues/14) ("Improper Parent reference detection", fixed in 1.20.03) fixed an earlier version of the same class of bug: the algorithm presumed any `row.` token with 3 nodes was a parent reference, so `row.OrderDetailCount` (2 nodes: `row`, `OrderDetailCount`) was wrongly treated as if it had a parent role. #14's fix added a node-count check — 2 nodes means "own attribute," 3+ means "presumed parent reference."

But a node-count check alone doesn't verify the *content* is right: `row.code.zfill` and `row.id_customer).scalar` both **do** have 3 nodes, so they sailed straight through #14's fix and were treated as parent references anyway — the exact bug #14 was meant to close, just one layer deeper. `find_missing_attributes` (`rule_bank_setup.py`) even carries an explicit acknowledgment of this gap already, unresolved until now:

```python
if len(class_and_attr.split('.')) > 2:
    pass  # FIXME - parent reference, need to decode the role name --> table name
```

That `pass` meant a 3-node token's *middle* node — the thing that actually determines whether it's a real relationship — was never checked anywhere in the pipeline. `find_missing_attributes` only ever validated the *second* node (`class_and_attr.split('.')[1]`) against `mapper.all_orm_descriptors` — which is why `code.zfill` (2b's `id_customer)`) either slipped through (2a: `code` is a real column, wrong node validated) or failed for the wrong reason (2b: `id_customer)` isn't a descriptor, but the *actual* problem is that `code`/`id_customer` was never a relationship in the first place).

&nbsp;

## The fix

`abstractrule.py`:

```python
def parse_dependencies(self, rule_text: str):
    ...
    for each_word in words:
        for part in each_word.split('('):
            the_word = part.lstrip("(").rstrip("),")
            if the_word.startswith("row."):
                dependencies = the_word.split('.')
                if len(dependencies) == 2:
                    self._dependencies.append(dependencies[1])
                elif self._is_relationship_node(dependencies[1]):   # <-- new check
                    self._dependencies.append(dependencies[1] + "." + dependencies[2])
                    self.update_referenced_parent_attributes(dependencies)
                # else: not a real relationship - drop it

def _is_relationship_node(self, node_name: str) -> bool:
    decl_meta = getattr(self, '_decl_meta', None)
    if decl_meta is None:
        return False
    try:
        mapper = sqlalchemy.orm.class_mapper(decl_meta)
    except sqlalchemy.exc.SQLAlchemyError:
        return False
    return node_name in mapper.relationships
```

`self._decl_meta` (the mapped SQLAlchemy class) is already set on every rule instance by `AbstractRule.__init__`, well before `parse_dependencies()` ever runs (it's called later, from `get_referenced_attributes()`, itself called from `rule_bank_setup.find_referenced_attributes()` during `LogicBank.activate()`). `sqlalchemy.orm.class_mapper(decl_meta).relationships` gives the authoritative answer directly — no dependency on `RuleBank.get_mapper_for_class_name()`'s lazily-built, first-call-order-sensitive cache, and no dependency on `rules_bank.orm_objects` being populated for the class in question yet.

This fixes both reported cases at once: `code` and `id_customer)` are both plain columns/mangled tokens, neither is a relationship, so both tokens are now silently dropped rather than mis-registered. A genuine parent reference (`customer`, `OrderHeader`, `on_loan_dept`, etc.) passes the check exactly as before — verified against the existing `examples/nw` (`row.OrderHeader.ShippedDate`) and `examples/multi_relns` (`row.on_loan_dept.name`, `row.works_for_dept.name`) cascade tests, all still passing.

&nbsp;

## What "dropping" the dependency means (and doesn't mean)

Dropping a spurious dependency means it's no longer used for formula-pruning decisions or parent-cascade registration. It does **not** validate or fix whatever the token actually was — `row.code.zfill(8)` still executes exactly as written; only the *bookkeeping* about what it depends on changes. Consequence: a formula like this is no longer eligible for pruning based on that (bogus) dependency, so it behaves as if it always needs recomputation on that row's own update — which was already true in practice, since the dependency was never a real signal to begin with.

&nbsp;

## The `# deps:` comment convention (documented, not changed)

Issue #21 also reported a *useful* accident of the same textual-scan mechanism: for a `calling=` formula whose parent access happens inside a helper function (so `parse_dependencies` sees no literal `row.parent.attr` token in the formula's own source), the formula is wrongly pruned on updates and never re-registered as a referring child when the parent changes. `no_prune=True` only fixes the first half.

The reported, in-production workaround is a bare comment naming the dependency:

```python
def _quantity(row, old_row, logic_row):
    # deps: row.order_line.quantity row.order_line.date_served
    return _derive_quantity(row, logic_row)

Rule.formula(derive=models.Movement.quantity, calling=_quantity)
```

Because `parse_dependencies` scans the *entire* `inspect.getsource()` text — comments included — the `# deps:` line's `row.order_line.quantity`/`row.order_line.date_served` tokens are picked up exactly as if they'd appeared in executable code, satisfying both halves (pruning AND parent-cascade registration via `rule_bank_withdraw.get_referring_children`, which re-parses `get_rule_text()` including comments at parent-update time).

**This is now ratified as the documented, supported way to declare dependencies for a `calling=` formula whose actual parent access is hidden behind a helper-function call** — not merely tolerated. It relies on `parse_dependencies` continuing to scan raw source text (comments included) rather than switching to AST-based parsing; if `parse_dependencies` is ever rewritten to parse an AST instead of scanning text, this doc (and the `Rule.formula` docstring) must be revisited, since the trick depends specifically on comments being part of the scanned text. A first-class `deps=[...]` parameter on `Rule.formula` was considered as a cleaner alternative but not implemented in this pass — the comment convention costs nothing to document today and doesn't foreclose adding `deps=` later.

&nbsp;

## Regression tests

`examples/spurious_parent_dependency/` (new, minimal — `Customer`/`Item`, matching the issue's own repro schema; no gold DB needed, in-memory SQLite, the thing under test is dependency parsing / `LogicBank.activate()` itself):

- `test_case_2a_str_method_on_column_not_registered_as_dependency` — `row.code.zfill(8)` registers zero dependencies, activates cleanly, and does not crash on `UPDATE` (previously: `"FIXME invalid role name code"`).
- `test_case_2b_subquery_fragment_does_not_kill_activation` — the reported `Constraint` sub-query pattern activates cleanly (previously: `LBActivateException` killing the whole rule set).
- `test_genuine_parent_reference_still_registered` — `row.customer.name` (a real relationship) is still correctly tracked as a dependency and the formula still computes correctly on insert.

Full repo suite (`python3 run_tests.py`) — zero regressions, all 13 example dirs pass, including `examples/nw` and `examples/multi_relns`'s existing real-relationship formula-cascade tests (`row.OrderHeader.ShippedDate`, `row.on_loan_dept.name`, `row.works_for_dept.name`), confirming genuine parent-reference tracking is unaffected.
