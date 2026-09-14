---
title: Multi-Relationship Aggregate Bug — Investigation Notes
Description: Root-cause trail for GitHub issue #20 — Rule.sum ignores child_role_name for multiple relationships to the same parent when models use back_populates
Source: logic_bank/rule_type/aggregate.py, logic_bank/rule_type/sum.py, logic_bank/rule_type/count.py
Usage: AI assistants read this before touching aggregate.py / sum.py / count.py / rule_bank_withdraw.py child_role_name logic
version: 4.1
changelog:
  - 4.1 (Jun 2026) - Resolved the final open thread: "parent refs / insert-link" identified precisely as LogicRow.link() (logic_bank/exec_row_logic/logic_row.py) - used by the Allocation extension and manual audit-copy patterns. Distinguished from GitHub issue #6 (closed, separately, in this session - an unrelated isinstance/nodal-name bug in the same method, already fixed in the codebase before this round). link() gained a child_role_name parameter (same pattern as Copy); existing no-disambiguator ambiguous case still correctly raises, message reworded to "Ambiguous Relationship" for consistency with Sum/Count/Copy. New test_link_disambiguation.py (3 tests) - confirmed fail-without/pass-with the fix. 21 tests total in examples/multi_relns/, full repo suite zero regressions. All identified multi-relationship directions are now fixed.
  - 4.0 (Jun 2026) - FIXED AND TESTED both remaining child<->parent directions. (a) get_referring_children() (rule_bank_withdraw.py) - the dict-reset-inside-the-loop bug (same shape as issue #20, on the cascade/live-Rule.formula side) - moved the reset to once-before-the-loop. rules_bank.py now declares Rule.formula on BOTH roles (works_for_dept_name_live + on_loan_dept_name_live); 4 new/updated tests in test_formula_cascade.py prove both cascade independently (previously only the last-declared role ever did). (b) Rule.copy gained a child_role_name parameter (logic_bank.py + copy.py), mirroring Sum/Count's pattern - Copy.__init__ honors it directly, only falling back to the ambiguity-detecting loop when absent (still correctly raises "Ambiguous Relationship" there, by design). Fixed a landmine found while testing: the ambiguity exception message referenced {self} via __str__(), which itself reads self._from_parent_role - not yet set at the point the exception fires, so it raised a misleading AttributeError instead of the intended message; switched to get_derived_attribute_name(). rules_bank.py now declares Rule.copy(child_role_name="works_for_dept"); test_copy_ambiguous.py rewritten to test correct resolution (both roles) plus the still-correct no-child_role_name fail-fast. 18 tests total in examples/multi_relns/ (up from 14), full repo suite zero regressions.
  - 3.1 (Jun 2026) - Fixed and tested the null-optional-FK crash too (separate bug from issue #20, found while building the suite). All 5 adjust_from_* sites in aggregate.py now distinguish "FK is validly null" (skip, via new _fk_is_null() helper) from "FK is non-null but parent missing" (still raises, unchanged). Caught and fixed an early-return bug in adjust_from_updated_reparented_child that was skipping the old-parent decrement. New test_null_optional_fk.py (3 tests). Full suite: zero regressions.
  - 3.0 (Jun 2026) - FIX LANDED AND VERIFIED. sum.py: Sum now honors explicit child_role_name before falling back to get_child_role_name() (mirrors Count's existing precedence). aggregate.py get_child_role_name(): matches back_populates/key in addition to legacy backref, and the previously-unconditional found_attr fallthrough is now correctly scoped to the no-child_role_name branch only. New examples/multi_relns/ suite (own gold db, 3 departments/3 employees, 5 test files, 11 test methods covering all 6 test-plan cases) - confirmed FAILS (2/11) without the fix, PASSES (11/11) with it. Full repo suite (python3 run_tests.py) - zero regressions, all 9 example dirs pass. NOTE: building the suite surfaced a new, separate, unfixed bug - a null optional parent FK (on_loan_id=None) crashes the aggregate adjustor outright (AttributeError, aggregate.py:100) - documented as a deliberate non-goal in db/create_db.py, not yet filed.
  - 2.6 (Jun 2026) - Added 3 test cases missing from Val's original sketch: (4) reparenting - same-role-different-parent AND different-role moves, asserting all 3 departments touched; (5) multiple aggregates on the same role adjusted together in one transaction, intersecting the ParentRoleAdjustor coalescing mechanism; (6) delete as its own dedicated case (separate code path, do_not_adjust_list), not assumed-covered by update tests
  - 2.5 (Jun 2026) - Decided: dedicated examples/multi_relns/ folder (own DB, own test data), Dept/Employee as model/guide not a dependency. Pinpointed exact gap in test_add_emp.py - it only asserts on one side (works_for), never checks the other Department (on_loan) - that's likely why it passes despite exercising the affected Rule.sum. New rule for the suite: every multi-role test must assert on ALL parent instances involved, matching the discipline of the GitHub issue repro (checks both store1 and store2).
  - 2.4 (Jun 2026) - Concretized Val's test plan (Dept/Employee sums+counts both roles, Employee with both copy and live-reference attrs). Ran examples/nw/tests/test_add_emp.py against current (bugged) source - confirmed it PASSES despite asserting on the affected Rule.sum (SalaryTotal) - bug is declaration/usage-pattern-dependent, not universal; existing test is insufficient evidence either way, dedicated regression test still needed. Flagged open question: extend nw's gold DB or new dedicated example dir.
  - 2.3 (Jun 2026) - Added third direction: live parent-to-child cascade (Rule.formula referencing row.<role>.<attr>). Confirmed GL's own CE (logic_bank_api.md) documents copy-vs-formula semantics but never addresses role disambiguation. Found a same-shape bug in get_referring_children() (rule_bank_withdraw.py:195, resets referring_children list inside the per-relationship loop) plus Val's own pre-existing TODO at logic_row.py:680 flagging this exact untested scenario. Not yet reproduced with a runnable repro - flagged as "likely broken," not confirmed.
  - 2.2 (Jun 2026) - Added Rule.copy (no disambiguation param at all, raises literal TODO on ambiguity - earlier-stage, not buggy) and parent-refs/insert-link (open thread, not fully traced) to the picture. Added summary table of child_role_name support state across Sum/Count/Copy/parent-refs. Trimmed duplicate pre-confirmation narrative.
  - 2.1 (Jun 2026) - Added SQLAlchemy 1.x-straddle-to-2.0 background (Val's note): aggregate.py:224 is the ONE remaining `backref` reference anywhere in logic_bank/ (grep-confirmed), a fossil from the straddling period. Confirmed examples/nw models the Department/Employee multi-relationship case identically to the issue's repro (pure back_populates, no backref) - not a GL-vs-LB modeling mismatch. Identified why nw's own tests never caught this: its multi-relationship rules are all Rule.count (unaffected), never Rule.sum (affected)
  - 2.0 (Jun 2026) - CONFIRMED via https://github.com/valhuber/LogicBank/issues/20 (reporter: alejandromyto). Independently-derived root cause matched exactly; issue additionally identifies that Count is unaffected (honors explicit child_role_name before falling back to get_child_role_name()) while Sum is affected (always calls get_child_role_name() when as_sum_of is an InstrumentedAttribute, overwriting the explicit child_role_name) — sharper fix target than originally proposed
  - 1.0 (Jun 2026) - Initial root-cause trail from Val's recollection + code reading: get_child_role_name() fallthrough bug
---

# Multi-Relationship Aggregate Bug — Investigation Notes

## ✅ Status: All directions fixed and verified, including the "parent refs" thread

| Direction | Mechanism | Status |
|---|---|---|
| Child aggregates up to parent | `Rule.sum` / `Rule.count` | ✅ Fixed (issue #20) |
| Parent FK validity (adjacent bug, found while testing) | aggregate adjustor, null optional FK | ✅ Fixed |
| Child copies from parent (snapshot) | `Rule.copy` | ✅ Fixed (gained `child_role_name`) |
| Parent cascades live to child | `Rule.formula` referencing `row.<role>.<attr>` | ✅ Fixed (`get_referring_children()`) |
| Manual programmatic link (Allocation, audit-copy patterns) | `LogicRow.link()` | ✅ Fixed (gained `child_role_name`) — see also [issue #6](https://github.com/valhuber/LogicBank/issues/6), closed separately, an unrelated `isinstance`/nodal-name bug in the same method |

`examples/multi_relns/` now has 21 tests across 7 files, all passing; full repo suite (`python3 run_tests.py`) shows zero regressions across all 9 example directories.

&nbsp;

### Issue #20 scope (child→parent aggregates)

**Code changes:**
- `logic_bank/rule_type/sum.py` — `Sum.__init__` now checks `child_role_name` first (same precedence `Count` already had), only calling `get_child_role_name()` as a fallback.
- `logic_bank/rule_type/aggregate.py` — `get_child_role_name()`'s ambiguous-role-name branch now matches `back_populates` and `key` (not just legacy `backref`), and the `found_attr = each_attr` fallthrough that previously ran on every iteration regardless of branch is now correctly scoped to the no-`child_role_name` (single-relationship) branch only.

**New regression suite:** `examples/multi_relns/` — own gold DB (`Department`/`Employee`, 3 departments, 3 employees seeded with varied works_for/on_loan combinations), own rules (`Rule.sum` + `Rule.count` on both roles, one `Rule.formula` live-reference), 5 test files / 11 test methods covering all 6 cases from the test plan below. Verified:
- **Without the fix:** 2 of 11 tests fail (the `Rule.sum` collapse-onto-wrong-role symptom, reproduced cleanly)
- **With the fix:** 11 of 11 pass
- **Full repo suite** (`python3 run_tests.py`): zero regressions — all 9 example directories (including `examples/nw`) pass

**A second, separate bug surfaced while building the suite — also now fixed and tested:** a null optional parent FK (e.g. `Employee.on_loan_id = None`, meaning "not currently on loan to anyone") used to crash the aggregate adjustor outright — `AttributeError: 'NoneType' object has no attribute '<column>'` (insert/delete/update-in-place paths) or incorrectly raise `ConstraintException("Unable to Adjust Missing Adopting Parent")` (reparent path, which conflated "FK is validly null" with "FK points at a row that doesn't exist" — a real data-integrity case that correctly should keep raising).

- **Fix:** all 5 `adjust_from_*` call sites in `aggregate.py` now check `parent_logic_row.row is None` (or `previous_parent_logic_row.row is None`) and, when the underlying FK column is itself null (new `Aggregate._fk_is_null()` helper, checks `local_remote_pairs` on the relationship), reset the adjustor's field back to `None` and skip — rather than proceeding to `getattr()`/`setattr()` on a `None` row, or (reparent case) raising. The reparent path's existing raise is preserved for the genuine integrity-violation case (FK is non-null but doesn't resolve to a real parent row) — only the legitimately-null-FK case was changed.
- **One bug found and fixed while fixing this:** an early `return` in `adjust_from_updated_reparented_child`'s new-parent-null branch incorrectly skipped the unrelated old-parent (`previous_parent_logic_row`) decrement block later in the same method — caught by `test_update_employee_to_null_on_loan_id` asserting the *old* department's count actually decremented, not just "no crash."
- **Tests:** `examples/multi_relns/tests/test_null_optional_fk.py` — insert/update-to-null/delete cases, 3 tests. Confirmed: 3 errors without the fix, 0 with it. Full repo suite: zero regressions.

### `Rule.copy` and live `Rule.formula` cascade — also now fixed

**`Rule.copy`:** gained a `child_role_name` parameter (`logic_bank.py` + `copy.py`), mirroring `Sum`/`Count` — `Copy.__init__` honors it directly when supplied, falling back to the original ambiguity-detecting loop (still correctly raises `"Ambiguous Relationship"`, by design, when no disambiguator is given). One landmine found and fixed while testing: the ambiguity exception's message referenced `{self}` via `__str__()`, which itself reads `self._from_parent_role` — not yet set at the point the exception fires — so it raised a misleading `AttributeError` instead of the intended message. Fixed by using `get_derived_attribute_name()` instead. `rules_bank.py` now declares `Rule.copy(..., child_role_name="works_for_dept")`; `test_copy_ambiguous.py` tests correct resolution on both roles plus the still-correct no-`child_role_name` fail-fast (4 tests).

**`get_referring_children()` cascade bug** (`rule_bank_withdraw.py`, "A third direction" section below): fixed — the dict-reset that was happening *inside* the per-relationship loop now happens once, before the loop, so referring-children entries from all `ONETOMANY` relationships on a parent class accumulate instead of the last one clobbering the rest. `rules_bank.py` now declares `Rule.formula` on **both** roles (`works_for_dept_name_live` + `on_loan_dept_name_live`); `test_formula_cascade.py` (4 tests) proves both cascade independently — confirmed the `works_for` side specifically failed without the fix (it was declared second-to-last and was the one being silently dropped).

&nbsp;

---

## Confirmed: GitHub Issue #20

[github.com/valhuber/LogicBank/issues/20](https://github.com/valhuber/LogicBank/issues/20) — "Rule.sum ignores child_role_name for multiple relationships to the same parent when models use back_populates (not backref)" (reporter: alejandromyto, LogicBank 1.31.02, SQLAlchemy 2.0, models generated by API Logic Server).

Independently root-caused in this session (see below) before reading the issue — matched exactly. The issue report adds one sharper finding this session's analysis missed: **`Count` is not affected, only `Sum` is**, which narrows the fix.

### The reproduction (self-contained, no GL/ALS needed)

Two stores, one `Transfer` row with `origin_id`/`dest_id` both FK → `Store.id` (two relationships, same parent class, `back_populates` style — exactly how ALS generates SQLAlchemy 2.0 models):

```python
Rule.sum(derive=Store.transfer_out, as_sum_of=Transfer.qty, child_role_name="transfers_out")
Rule.sum(derive=Store.transfer_in,  as_sum_of=Transfer.qty, child_role_name="transfers_in")
```

**Expected:** `store1.transfer_out=5, store2.transfer_in=5` after a 5-unit transfer from store 1 → store 2.
**Actual:** both sums collapse onto the same (last-seen) relationship: `store2.transfer_out=5, store2.transfer_in=5` — store 1 gets nothing, store 2 gets double-counted onto both columns. With `insert_parent=True` this additionally raises `Missing Parent: <the other role>` on insert.

### Why `Count` escapes this but `Sum` doesn't — `count.py:35-43` vs `sum.py:32-37`

```python
# count.py — child_role_name wins outright if supplied; get_child_role_name() is a fallback only
if child_role_name is not None and child_role_name != "":
    self._child_role_name = child_role_name
else:
    ...
    self._child_role_name = self.get_child_role_name(child_attrs=child_attrs)
```

```python
# sum.py — get_child_role_name() always runs when as_sum_of is an InstrumentedAttribute,
# UNCONDITIONALLY OVERWRITING whatever child_role_name was explicitly passed in
elif isinstance(as_sum_of, InstrumentedAttribute):
    ...
    self._child_role_name = self.get_child_role_name(child_attrs=child_attrs)
```

So even before `get_child_role_name()`'s internal `backref`-vs-`back_populates` mismatch comes into play, `Sum` was already discarding the caller's explicit disambiguator. `Count`'s precedence check (explicit value wins, fallback only when absent) is the correct pattern — `Sum` should mirror it.

### Suggested fix (from the issue, refined)

1. **Primary fix — give `Sum` the same precedence `Count` already has:** only call `get_child_role_name()` when `child_role_name` was not supplied, mirroring `count.py:35-43`.
2. **Secondary/defense-in-depth fix — `get_child_role_name()` itself should match `back_populates` too, not just `backref`:**
   ```python
   if self._child_role_name in (each_attr.backref, each_attr.back_populates):
       found_attr = each_attr
   ```
   Still needs the fallthrough-assignment fix (see below) even with this — fixing only the comparison without also scoping the unconditional `found_attr = each_attr` assignment leaves the "last relationship wins when nothing matches" failure mode for the genuinely-no-`child_role_name` ambiguous case... though that case already raises `"Ambiguous Relationship"` via the `self._child_role_name == ""` branch, so this is lower-priority once fix #1 lands.

### Background: the `backref` fossil — SQLAlchemy 1.x → 2.0 migration

**Val's note:** LogicBank was originally written against pre-2.0 SQLAlchemy, which modeled relationships differently (the legacy `backref=` kwarg, declared on one side only, auto-generating the reverse accessor). 2.0 changed this to require both sides declared explicitly via `back_populates=`. LB went through a period of trying to **straddle both styles** — "a bad idea" — before settling on 2.0-only (`pyproject.toml` now pins `sqlalchemy>=2.0.48`).

**`aggregate.py:224`'s `each_attr.backref == self._child_role_name` is the one remaining fossil from that straddling era** — confirmed via `grep -rn "backref" logic_bank/`: it is the **only** `backref` reference left anywhere in `logic_bank/`. Everything else in the codebase (the dependency pin, every example model, `rule_bank_withdraw.py:87`'s own `child_role_name = each_relationship.back_populates`) is already 2.0-only. This one comparison simply never got migrated when the rest of the straddle was torn out.

### Are the relationships modeled the same in LB's own examples vs. the issue's repro? **Yes — confirmed.**

`examples/nw/db/models.py:124-125, 304-305` (`Department.EmployeeOnLoanList`/`EmployeeWorksForList` ↔ `Employee.On_loan_dept`/`Works_for_dept`, two relationships to the same parent table) use **pure `back_populates=` + `foreign_keys=`, zero `backref=`** — identical style to the issue's `Store`/`Transfer` repro. So this isn't a GL-vs-LB modeling mismatch; both sides already converged on 2.0-only `back_populates`. The bug is purely in `aggregate.py`'s un-migrated comparison, not in any divergent relationship-modeling assumption between the two codebases.

**Why `examples/nw`'s own test suite never caught this:** nw's `Department`/`Employee` multi-relationship rules (`examples/nw/logic/logic.py:85-86`) are both `Rule.count` (`OnLoanCount`, `WorksForCount`) — and per the confirmed root cause above, **`Count` is unaffected**, only `Sum` is. nw has been exercising the *safe* half of this exact relationship pattern for years without ever exercising the broken half. A `Rule.sum` analog over the same `Department`/`Employee` multi-relationship pair would have caught this in this repo's own test suite — worth adding as a regression test alongside the fix.

### `Rule.copy` — confirmed: not buggy, simply never finished (further behind than Sum/Count, not differently broken)

> **✅ Now fixed** — see "Status" section at the top. `Rule.copy` gained a `child_role_name` parameter; this section is kept as the original investigation record (the *why* it needed fixing), not the current state.

Checked `logic_bank/rule_type/copy.py` per Val's recollection ("role added to aggregates, copy, and parent refs") — **`Rule.copy()` has no `child_role_name`/role disambiguation parameter at all.** Compare signatures:

```python
# logic_bank.py
def sum(derive: Column, as_sum_of: any, where: any = None, child_role_name: str = "", insert_parent: bool = False): ...
def count(derive: Column, as_count_of: object, where: any = None, child_role_name: str = "", insert_parent: bool=False): ...
def copy(derive: Column, from_parent: any): ...    # <<< no child_role_name / role param at all
```

`Copy.__init__` (`copy.py:20-39`), when `from_parent` is an `InstrumentedAttribute` and there are 2+ relationships from the child to the same parent class, hits its own ambiguity loop — which has no disambiguator to consult, so it just raises outright:

```python
if each_parent_class_name == self._parent_class_name:
    if found_attr is not None:
        raise Exception("TODO / copy - disambiguate relationship")   # literal TODO, never implemented
    found_attr = each_attr
```

So `Rule.copy` is in an *earlier* state than `Sum`/`Count`, not a buggy one: the single-relationship case works (matches `aggregate.py`'s original, deliberate single-relationship shortcut), and the multi-relationship case fails loudly with a `TODO` placeholder exception rather than silently resolving wrong. **This is the safer of the two failure modes** (loud beats silent), but it means `Rule.copy` cannot express the multi-relationship case at all today — there's no equivalent of `child_role_name=` to add to a `Rule.copy()` call even as a workaround.

### "Parent refs" — `LogicRow._get_parent_logic_row()` and `_get_parent_role_def()` (`exec_row_logic/logic_row.py`)

> **✅ Now fixed** — the insert/link helper turned out to be `LogicRow.link()`. See "Status" section at the top. This section is kept as the original investigation record (the close read that found it was *not yet* fully traced, and the next-session follow-up that closed it).

These take an explicit `role_name: str` parameter directly (`logic_row.py:248`, `:323`) — they're the *consumer* side, trusting whatever role name was already resolved upstream by the caller (e.g. `aggregate.py`'s `_parent_role_name`, or copy-rule iteration at `logic_row.py:296-309` which iterates `copy_rules.items()` keyed by role). They are not where ambiguity gets resolved, and are not bugged in the way `aggregate.py` is.

The **insert/link helper** (`LogicRow.link()`, around `logic_row.py:331-378`, used when inserting/linking a new child row to a parent) resolves a role name itself via `each_relationship.back_populates` (2.0-only, no `backref` fossil here) — and **did** have ambiguity handling: `if parent_role_name is not None: raise Exception("TODO - disambiguate relationship...")`, same fail-fast shape as `Copy`'s original. **Confirmed unrelated to [GitHub issue #6](https://github.com/valhuber/LogicBank/issues/6)** (closed separately this session) — issue #6 was an `isinstance(child, each_relationship.entity.class_)` vs. nodal-name bug in the *same method*, already fixed in the codebase before this round of work; the `"TODO - disambiguate"` exception survived that fix untouched, and is what was actually fixed here (gained `child_role_name=`, mirroring `Copy`).

&nbsp;

## A third direction: live parent→child cascade (`Rule.formula` referencing `row.<role>.<attr>`)

**Val's prompt that surfaced this:** child tables can reach a parent attribute two ways — `Rule.copy` (snapshot, already covered above) and `Rule.formula(as_expression=lambda row: row.<parent_role>.<attr>)` (**live reference** — parent changes propagate/cascade to the child). GL's own CE (`docs/training/logic_bank_api.md:651-684`) documents the snapshot-vs-live *semantic* choice clearly (when to use `Rule.copy` vs `Rule.formula`) — but **is completely silent on role-name disambiguation for either direction**. It always shows single-relationship examples (`row.order.ready`, `row.hs_code_rate.surtax_rate`) — never a case with 2+ relationships to the same class. So no, the gap is not addressed there.

This matters because live-reference cascade is the **reverse direction** from the `Sum`/`Count`/`Copy` bugs documented above (which are child-aggregates-up-to-parent, or child-copies-from-parent). Cascade is parent-attribute-change-propagates-down-to-children, and it has its own, structurally identical disambiguation problem — found by tracing `_parent_cascade_attribute_changes_to_children()` (`logic_row.py:666-716`):

### Bug, same shape as issue #20: `get_referring_children()` — `rule_bank_withdraw.py:172-219`

> **✅ Now fixed** — see "Status" section at the top. The dict reset moved to once-before-the-loop. This section is kept as the original investigation record.

```python
for each_parent_relationship in parent_relationships:  # eg, order has parents cust & emp, child orderdetail
    if each_parent_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:
        parent_role_name = each_parent_relationship.back_populates
        parent_rules.referring_children[parent_logic_row.name] = []   # <<< BUG: resets to [] every iteration
        ...
        parent_rules.referring_children[parent_logic_row.name].append(
            (child_class_name, child_role_name, rule_terms[2], parent_role_name))
```

`parent_rules.referring_children[parent_logic_row.name] = []` sits **inside** the `for each_parent_relationship` loop, keyed only by `parent_logic_row.name` (the parent class name) — not by `parent_role_name`. So if a parent class has 2+ `ONETOMANY` relationships (e.g. `Department.EmployeeWorksForList` and `Department.EmployeeOnLoanList`, both → `Employee`), **each iteration wipes out whatever the previous iteration appended** — only the last relationship's referring-children entries survive the loop. Same "last one wins, silently" shape as the aggregate-side bug, just on the cascade/propagation side instead.

The match itself (lines 205-219) is textual — it scans each child formula's source text (`rule_text.split()`) for a token starting with `"row." + parent_role_name`, so it **can** correctly distinguish which parent role a given child formula references. That part isn't the problem; the dict being clobbered before it's ever consumed is.

### Downstream, also unverified: `cascade_dict` keyed by child role — `logic_row.py:692-715`

Even if the above were fixed, `_parent_cascade_attribute_changes_to_children()`'s `cascade_dict` is keyed by `each_child_role_name` (line 700-702): `if each_child_role_name not in cascade_dict: cascade_dict[each_child_role_name] = (...)`. If two different referring-children tuples ever shared the same child role name but different parent role/attribute (an edge case, but possible once #1 above stops suppressing it), the second would be silently dropped — first-one-wins instead of cascading both.

**Val's own comment, verbatim, line 680:** `Todo: test cascade to multiple children using same parent role name, in alternating order` — i.e., you flagged this exact scenario as untested at the time, not confirmed broken. Given the bug found in `get_referring_children()` above, it's now reasonable to suspect it actually *is* broken, not just untested — but this hasn't been verified with a runnable repro the way issue #20 was.

**Status:** ✅ Fixed and confirmed with a runnable test (`test_formula_cascade.py`'s `test_renaming_works_for_parent_cascades_only_works_for_side` — failed without the fix, passes with it). The `cascade_dict` keyed-by-child-role concern above did not manifest as a separate bug once the producer-side fix landed — `examples/multi_relns`'s two `Rule.formula` rules target different child roles already (the `Employee` class only has one row per role pairing), so this specific edge case (two referring-children tuples sharing a child role but differing parent role/attribute) remains theoretically possible but unexercised; worth a dedicated test if a concrete scenario for it is found.

&nbsp;

## Summary: state of `child_role_name`/role support by rule type (post-fix)

| Rule type | Disambiguation param? | Multi-relationship behavior | Status |
|---|---|---|---|
| `Rule.count` | `child_role_name=` | **Correct** — explicit value takes precedence over `get_child_role_name()` | ✅ Working (always was) |
| `Rule.sum` | `child_role_name=` | **Fixed** — now mirrors `Count`'s precedence; `get_child_role_name()` also fixed (matches `back_populates`, fallthrough scoped correctly) | ✅ Fixed (issue #20) |
| `Rule.copy` | `child_role_name=` (new) | **Fixed** — `Copy.__init__` honors it directly; no-`child_role_name` ambiguous case still correctly raises (by design) | ✅ Fixed |
| `LogicRow.link()` (manual programmatic link, used by Allocation/`nw_copy.py`) | `child_role_name=` (new) | **Fixed** — same pattern as `Copy`; no-`child_role_name` ambiguous case still correctly raises, message reworded from `"TODO - disambiguate"` to `"Ambiguous Relationship"` for consistency. NOT the same as issue #6 (closed separately — that was an `isinstance`/nodal-name bug in the same method, unrelated, already fixed before this session) | ✅ Fixed |
| `Rule.formula` live cascade (parent attr change → child re-derive), `row.<role>.<attr>` | n/a (role is just the literal accessor in the lambda/string) | **Fixed** — `get_referring_children()`'s dict reset moved outside the per-relationship loop | ✅ Fixed |
| Null optional parent FK (any aggregate, insert/update/delete) | n/a | **Fixed** — `adjust_from_*` methods now distinguish "FK validly null" (skip) from "FK non-null but parent missing" (still raises) | ✅ Fixed (separate bug, found while testing #20) |

&nbsp;

## Verified workaround (from the issue, works today without a code change)

```python
s_out = Rule.sum(derive=Store.transfer_out, as_sum_of=Transfer.qty, child_role_name="transfers_out")
s_in  = Rule.sum(derive=Store.transfer_in,  as_sum_of=Transfer.qty, child_role_name="transfers_in")
s_out._child_role_name = "transfers_out"   # overwrite post-construction, bypassing get_child_role_name()
s_in._child_role_name  = "transfers_in"
```

&nbsp;

---

## Background (from Val)

Most of the time, there's exactly one relationship between two tables. Sometimes there are two — e.g. a `Department` has both "works-for" and "on-loan" `Employee`s (`Employee.WorksFor` and `Employee.OnLoan`, both FKs to `Department.Id` — see the comparison vs `examples/nw` in `basic_demo_sample.md`).

LogicBank's original design (honestly) **took a shortcut**: it presumed the single-relationship case, with code that deliberately fails fast (`"Ambiguous Relationship"`) when it detects more than one relationship to the same parent table and no disambiguator was given.

Later, support for the multi-relationship case was added by threading a **`role`** parameter (`child_role_name=`) through aggregates (`Rule.sum`, `Rule.count`), `Rule.copy`, and parent refs. **Val did not remember how far this got** — resolved above: `Count` got it right, `Sum` regressed it (issue #20), `Copy` never got the parameter at all (still raises a literal `TODO`), and the parent-refs/insert-link path remains an open thread (see table above, last row).

### Still open: `get_parent_role_from_child_role_name()` (`aggregate.py:53-56`)

Ignores both its parameters and unconditionally returns `self._parent_role_name`, the single mutable field set once by `rule_bank_withdraw.aggregate_rules()` (line 102) per rule object. Currently harmless for `Sum`/`Count` since `child_role_name=` already produces a separate rule object per role — but worth a second look once the primary fix lands, to confirm it stays harmless rather than becoming the next fossil.

## Solution includes tests

We need a test in addition to the code, using the Dept example:

* test db with data
* Dept has sums/counts of onLoan and worksFor — tests alter & validate
* Emp has both a copied and referenced attr — tests alter & validate (e.g. is propagated for references, not copies)
* tests should be part of the test suite

### Why `test_add_emp.py` (existing) doesn't already cover this — checked, confirmed insufficient

`examples/nw/tests/test_add_emp.py` already exists, is explicitly labeled `"Regression test - multi-relns between same 2 tables tests"`, and already asserts on `Department.SalaryTotal` (line 51) — which is a `Rule.sum(..., child_role_name="EmployeeWorksForList")`, the exact rule type broken by issue #20. **Ran it against the current (bugged) source in this checkout — it passes.**

This means the bug does not manifest in this test's specific scenario (one new Employee with `WorksFor=1, OnLoan=2` — two *different* target departments). That's evidence the bug is real but **declaration/usage-pattern-dependent** — it doesn't necessarily corrupt every multi-relationship `Rule.sum`, only specific shapes (the issue's repro uses `Transfer.origin_id`/`dest_id` both able to point at *the same* `Store` in either role, plus two sums on the *same parent class* sharing the *same child summed field* `qty` — closer to a self-referencing pattern than `Department`/`Employee`). **Do not treat `test_add_emp.py` passing as evidence the bug doesn't exist** — it's evidence this particular test doesn't happen to trigger it, which is exactly why a dedicated, issue-#20-shaped regression test is needed rather than relying on this one.

### Decision: dedicated example folder — `examples/multi_relns/` (or similar)

Agreed: this is its own complex area and deserves its own self-contained example, matching the existing convention (`examples/banking`, `examples/payment_allocation`, `examples/referential_integrity`, `examples/copy_children` — each with its own DB, models, logic, tests). The new folder gets its **own small DB and test data**, not a retrofit of nw's general-purpose dataset. `examples/nw`'s `Department`/`Employee` is the **model/guide** for shape (copy what's useful, don't feel bound to it) — not something this new suite depends on or extends in place.

### The precise gap in `test_add_emp.py` that the new suite must not repeat

`test_add_emp.py` already has a same-shaped scenario (one new Employee with `WorksFor=1, OnLoan=2`, i.e. **both FKs populated on the same row** — every Employee row already has both roles active simultaneously, this part is not the gap). The gap is **what it asserts on**: it only checks `works_for` (Department 1)'s aggregates (line 49-52) — it never checks what happened to `on_loan` (Department 2) from that same employee/transaction. That's almost certainly why it passes despite exercising the affected `Rule.sum`: a collapse-onto-the-wrong-role bug is only *observable* if you assert on both sides and confirm each got the correct, distinct value — the same discipline the GitHub issue's repro uses (it explicitly checks **both** `store1` and `store2` after one transfer, and that's exactly what makes the bug visible: `store2` ends up with both `transfer_out` and `transfer_in` set, `store1` gets nothing).

**Rule for the new test suite: every multi-role scenario must assert on *all* parent instances involved, not just one.** A test that only checks the role it expects to be correct will pass even when the engine silently misattributes the adjustment elsewhere.

### Test plan, concretized

1. **`Sum`/`Count` regression (Dept/Employee-style schema, own DB):**
   - Seed two (or more) Departments; employees with `WorksFor`/`OnLoan` pointing at *different* departments per employee, including at least one employee where they differ (to make a misattributed adjustment land somewhere observably wrong)
   - Give **both** roles a `Rule.sum` (today's nw only sums `WorksFor`; mirror it onto `OnLoan` too) and **both** roles a `Rule.count`
   - Alter (insert/update/delete/reparent) Employee rows touching both roles, in the same transaction and across separate transactions
   - **Assert on both Departments' aggregates after every alteration** — not just the one expected to be right (see gap above)

2. **`Rule.copy` vs `Rule.formula` (live reference) regression — new, neither currently tested for multi-relationship:**
   - Give the child class both a **copied** attr and a **referenced/live** attr from the *same* multi-relationship parent pair
   - Alter a parent attribute after the child is created
   - Assert: the **copied** attribute does NOT change (snapshot) — the **referenced/formula** attribute DOES change (live propagation) — and each picks up the value from the *correct* role's parent, not the other one
   - Exercises both gaps documented above: `Copy`'s missing disambiguator (raises `TODO` on ambiguity today — test may need to start as an expected-exception test until `Copy`'s fix lands) and the `get_referring_children()` cascade bug (`rule_bank_withdraw.py:195`)

3. **Test data / DB:** own gold DB + seed data, sized to the scenario only (small, per Val's ask) — not nw's broader dataset. Follow the existing pattern (`tests.copy_gold_over_db()`-style gold-DB-copy-per-test) rather than building schema ad hoc in each test file.

### Additional cases identified — not in Val's original sketch, added per "correct software, not minimal tests"

4. **Reparenting (role-changing update), not just insert/delete/value-update:** `Aggregate.adjust_from_updated_reparented_child` (`aggregate.py:174-209`) is a distinct code path — it adjusts **two** parent rows in one go (`parent_logic_row` gaining the child, `previous_parent_logic_row` losing it). Your "alter" case should explicitly include:
   - Same role, different parent instance (e.g. Employee moves from Department A's `WorksFor` to Department B's `WorksFor`) — tests whether the *role* stays correctly resolved across a reparent
   - Different role, same or different parent (e.g. Employee moves from `WorksFor` to `OnLoan`) — tests whether reparenting across roles (not just across parent instances within one role) is handled
   - Both must assert on **all three** departments potentially touched (old parent, new parent, and the untouched other-role parent) — per the "assert on all sides" rule above

5. **Multiple aggregates on the same role, adjusted together in one transaction:** the `ParentRoleAdjustor` "exactly one parent update per role" coalescing (Logic-Walkthrough wiki; also the mechanism behind the Kolk Oil performance story) operates per-role. Need a test where, e.g., `Sum.SalaryTotal` and `Count.WorksForCount` both target `EmployeeWorksForList`, and **one transaction changes both** (an Employee's salary changes AND they move into/out of that role) — confirming the coalesced single-update-per-role still lands in the correct role's bucket and isn't corrupted by the multi-relationship resolution bug. This is the sharpest intersection between issue #20 and the adjustor mechanics.

6. **Delete, as its own case — not assumed-covered by update tests:** `adjust_from_deleted_child` (`aggregate.py:107-130`) is a separate code path with its own `do_not_adjust_list` parameter (used to suppress adjustment for rows being deleted as part of a cascade, vs. a standalone delete). Needs its own dedicated case: delete an Employee touching one role, assert the *other* role's Department is correctly untouched, and assert the deleted-role's Department is correctly decremented — don't assume insert/update coverage implies delete correctness.