---
title: RowEvent/CommitRowEvent Mutations Bypassed Rule Checking — Root Cause, Empirical Confirmation, and Activation-Time Guard
Description: row.attr = value inside a Rule.row_event or Rule.commit_row_event callback was silently persisted but never re-triggered Formula/Sum/Count derivation or Constraint/CommitConstraint checking for that row - confirmed empirically, now caught at LogicBank.activate() time via a textual scan (LBActivateException), with an allow_row_mutation=True escape hatch
Source: logic_bank/exec_trans_logic/listeners.py (before_flush's Commit Logic Phase), logic_bank/exec_row_logic/logic_row.py (_row_events(), end of update()/insert()), logic_bank/rule_type/row_event.py (AbstractRowEvent._check_row_mutation, RowEvent, CommitRowEvent)
Usage: Read before touching AbstractRowEvent, RowEvent, CommitRowEvent, or the _ROW_ATTR_ASSIGNMENT scan in row_event.py. Read before deciding whether a row_event/commit_row_event handler needs allow_row_mutation=True.
version: 2.0
changelog:
  - 2.0 (Jul 2026) - Implemented the guard: activation-time textual scan (same inspect.getsource() approach Formula/Constraint already use) on RowEvent/CommitRowEvent's calling= source, raising LBActivateException on a detected `row.<attr> =` write, with allow_row_mutation=True as an explicit opt-out. Also corrected scope: RowEvent has the SAME bug as CommitRowEvent (fires at _row_events(), after the cascade, not before it - the earlier v1.0 only covered CommitRowEvent). EarlyRowEvent confirmed exempt (fires before the cascade, mutation is its documented purpose). AfterFlushRowEvent confirmed NOT to have the "silently corrupts data" version of this bug - SQLAlchemy drops attribute mutations made during after_flush entirely (not persisted, not even marked dirty) since the flush/SQL has already been emitted by then; out of scope for this guard, a different (weaker) footgun. Regression suite: examples/commit_event_mutation_scan/.
  - 1.0 (Jul 2026) - Raised as a "have I always worried about this correctly?" question during CommitConstraint design work. Confirmed empirically with a standalone repro (not from a reported bug or failing test) - no example/test in this repo or in build_and_test/genai-logic/samples/nw_sample currently exercised this path, so it had never been caught in practice. Documented as an open gap; not fixed at the time.
---

# RowEvent/CommitRowEvent Mutations Bypassed Rule Checking

## TL;DR

`Rule.row_event` and `Rule.commit_row_event` handlers both run *after* a row's `Formula`/`Sum`/`Count`/`Constraint`/`CommitConstraint` processing has already completed for that flush. If a handler did `row.some_column = value` there, SQLAlchemy's flush (which hadn't happened yet) picked up the mutated attribute and **persisted it** — but there was no second pass over that row's logic. The mutated value was never re-derived-from, never re-derived anything downstream, and never got checked against `Constraint` or `CommitConstraint`. Confirmed empirically with standalone repros.

**Fixed** (v2.0): `LogicBank.activate()` now textually scans a `RowEvent`/`CommitRowEvent`'s `calling=` source for a `row.<attr> =` assignment and raises `LBActivateException` if found — same activation-time-failure channel as a malformed `Formula`/`Constraint`. `allow_row_mutation=True` is an explicit opt-out for a deliberate, understood mutation (e.g., writing a plain column nothing derives from or constrains).

&nbsp;

## Scope: which event types were actually affected

| Type | Fires | Mutation safe? |
| :--- | :--- | :--- |
| `EarlyRowEvent` | `_early_row_events()` — **before** the row's own cascade | **Yes** — this is its documented purpose (defaulting, etc). Not scanned. |
| `RowEvent` | `_row_events()`, end of `update()`/`insert()` — **after** `_formula_rules`/`_adjust_parent_aggregates`/`_constraints` | **No** — same bug as CommitRowEvent. Scanned. |
| `CommitRowEvent` | `listeners.py`'s Commit Logic Phase, after ALL rows' cascades — still inside `before_flush`, before the actual SQL flush | **No** — the original reported case. Scanned. |
| `AfterFlushRowEvent` | `listeners.py`'s `after_flush`, after the actual SQL flush | **N/A** — SQLAlchemy silently *drops* the mutation (see below); not a data-corruption risk, a different footgun. Not scanned. |

The v1.0 draft of this doc only named `CommitRowEvent`. That was an oversight — `RowEvent`'s `_row_events()` call happens after the exact same cascade steps (`logic_row.py`: `_formula_rules()` → `_adjust_parent_aggregates()` → `_constraints()` → ... → `_row_events()`), so it has the identical bug, just one phase earlier in the same flush. Caught and corrected before implementing the fix.

&nbsp;

## Why `AfterFlushRowEvent` is different, not just "also affected"

Empirically confirmed (standalone SQLAlchemy repro, not LogicBank-specific): mutating a row attribute inside an `after_flush` listener does **not** raise, but the mutation is **silently discarded** — the object isn't even marked dirty afterward, because SQLAlchemy's change-tracking has already captured its committed-state snapshot for that flush by the time `after_flush` runs (the actual `UPDATE`/`INSERT` SQL has already been sent). A follow-up `session.commit()` doesn't pick it up either. So `AfterFlushRowEvent` mutation is "your write silently did nothing," not "your write silently bypassed your rules and got persisted anyway" — a real footgun, but a different one, and out of scope for this guard.

&nbsp;

## Where the bug happened (call sequence, before the fix)

`listeners.py`'s `before_flush`:

```python
for each_instance in a_session.dirty:      # row logic for existing dirty rows
    ...
    logic_row.update(reason="client")      # -> ... -> _constraints() -> ... -> _row_events()  <-- RowEvent here

for each_instance in row_sets.client_inserts:  # row logic for new rows
    ...
    logic_row.insert(reason="client")          # -> ... -> _constraints() -> _row_events()  <-- RowEvent here too

"""
Commit Logic Phase
"""
for each_logic_row_key in processed_rows:  # CommitRowEvent - AFTER all rows' cascades
    ...
    each_row_event.execute(each_logic_row)  # <-- and here
```

Neither `_row_events()` nor the Commit Logic Phase loop has an equivalent of `logic_row.update()`'s cascade — `AbstractRowEvent.execute()` just calls the user's function with `(row, old_row, logic_row)` and returns. The actual flush (SQL `UPDATE`/`INSERT`) happens *after* `before_flush` returns, driven by whatever SQLAlchemy finds dirty at that point — including anything either event type just changed. So the mutated value was written, silently, without going through the rule engine.

&nbsp;

## Empirical confirmation (pre-fix)

**1. A mutation was silently persisted:**
```python
def mutate_in_commit_event(row, old_row, logic_row):
    row.notes = 'MUTATED BY COMMIT EVENT'

Rule.commit_row_event(on_class=Order, calling=mutate_in_commit_event)
```
Insert an `Order` with `notes='original'`, commit. Reload from a fresh session: `notes == 'MUTATED BY COMMIT EVENT'`.

**2. The mutation did NOT get checked against an existing Constraint:**
```python
Rule.constraint(validate=Order, as_condition=lambda row: row.item_count != 999,
                error_msg="item_count must not be 999, got {row.item_count}")

def mutate_count_in_commit_event(row, old_row, logic_row):
    row.item_count = 999   # would violate the Constraint above, if re-checked

Rule.commit_row_event(on_class=Order, calling=mutate_count_in_commit_event)
```
Insert an `Order` (Constraint satisfied at insert time), commit → commit succeeded, no `ConstraintException`. Reload: `item_count == 999`, persisted despite violating a rule that would reject that exact value everywhere else in the system.

Both are now `LBActivateException` at `activate()` time instead, unless `allow_row_mutation=True` is passed.

&nbsp;

## What the codebase actually did before the fix (why this hadn't bitten anyone in practice)

Audited every `commit_row_event`/`row_event`/`after_flush_row_event`/`early_row_event_all_classes` registration in this repo's `examples/` and in `build_and_test/genai-logic/samples/nw_sample/logic` (including `logic_discovery/`). None mutated an already-processed row's attribute from inside a `RowEvent`/`CommitRowEvent`. Every real usage was one of:

- **Read-only** — logging, Kafka/n8n webhook sends, `session.query()` (`congratulate_sales_rep`, `fn_customer_workflow`/`fn_employee_workflow`/`fn_order_workflow`, `send_order_to_shipping`, `do_not_ship_empty_orders` in `nw_sample/logic_discovery/order_place/check_credit.py` — which hand-rolls a min-cardinality check via `raise ConstraintException(...)` instead of mutating anything, since `CommitConstraint` didn't exist yet).
- **Inserting new child rows** via `logic_row.insert()` / `new_logic_row().link().insert()` — `transfer_funds` (`examples/banking`), `add_employee_via_link` (`examples/multi_relns`). Safe: a *fresh* `LogicRow`'s own `.insert()` runs the full cascade for that new row. Note the textual scan does NOT flag `new_logic_row().row.attr = value` — that's a write to a *different* variable's `.row`, not the event's own `row` parameter (see "How the scan avoids false positives" below).
- **Mutations inside `early_row_event`/`early_row_event_all_classes`** — these fire *before* the row's own cascade, so mutations there are naturally subject to the rest of its own logic. This is the correct place to default/mutate a row's own attributes from an event.

So the gap was real and confirmed, but latent in this codebase — nothing here needed the fix to trip over the bug. The point of implementing the guard proactively is closing the door before a real project's `commit_row_event`/`row_event` handler does this by accident.

&nbsp;

## The fix

`row_event.py`:

```python
_ROW_ATTR_ASSIGNMENT = re.compile(r'(?<![.\w])row\.\w+\s*=(?!=)')

def _find_row_mutation(calling: Callable) -> str:
    """ inspect.getsource() textual scan - same approach/limitations as
    Formula/Constraint's dependency scan (dependency-scanning.md): won't see
    mutations hidden in a called helper function, only literal `row.<attr> =`
    in the scanned source. Returns the offending line, or "" if none found. """
    ...

class AbstractRowEvent(AbstractRule):
    _mutates_row_after_cascade = False  # True only for RowEvent, CommitRowEvent

    def __init__(self, on_class, calling=None, allow_event_nesting=False, allow_row_mutation=False):
        super().__init__(on_class)
        ...
        if self._mutates_row_after_cascade and not allow_row_mutation:
            self._check_row_mutation(calling)   # sets self._load_error on match
        ll.deposit_rule(self)   # RuleBank.deposit_rule() appends _load_error to
                                 # rule_bank.invalid_rules -> activate() raises LBActivateException
```

**How the scan avoids false positives:** the regex `(?<![.\w])row\.\w+\s*=(?!=)` requires `row` to be a standalone identifier — `(?<![.\w])` rejects a preceding `.` or word character, so `new_emp_logic_row.row.name = ...` (a *different* variable's `.row` attribute) does not match, only a bare `row.attr = ...` referring to the handler's own `row` parameter does. `(?!=)` excludes `==`/`<=`/`>=`/`!=` (comparisons, not assignments). This was caught by the initial regex (`\brow\.\w+\s*=`, using only a leading `\b`) false-positiving on `examples/multi_relns/tests/test_link_disambiguation.py`'s `add_employee_via_link`, which does `new_emp_logic_row.row.name = ...` — the safe "mutate a freshly-constructed row before inserting it" pattern — before the lookbehind fix.

**Reuses the existing rule-load-error channel**, not a new exception type: `AbstractRule._load_error` (set to `None` by `AbstractRule.__init__`, already used for a bad `validate=` class name) is set by `_check_row_mutation()`; `RuleBank.deposit_rule()` already appends any non-`None` `_load_error` to `rule_bank.invalid_rules`, and `LogicBank.activate()` already raises `LBActivateException(rule_bank.invalid_rules, missing_attributes)` if that list is non-empty. No new plumbing needed end-to-end.

&nbsp;

## Regression tests

`examples/commit_event_mutation_scan/` (new, minimal — single `Order` table, no relationships, in-memory SQLite; the thing under test is `LogicBank.activate()` itself, not a commit cascade):

- `test_commit_row_event_mutation_raises` / `test_row_event_mutation_raises` — a `row.attr = value` handler on each type raises `LBActivateException`.
- `test_early_row_event_mutation_allowed` — same mutation via `EarlyRowEvent` activates cleanly and the default actually applies on commit.
- `test_read_only_commit_row_event_allowed` — a handler that only reads `row.attr` activates cleanly.
- `test_new_row_insert_pattern_allowed` — the `new_logic_row().row.attr = ...` / `.insert()` pattern (matching `add_employee_via_link`'s real shape) activates cleanly and the inserted row is correctly persisted.
- `test_allow_row_mutation_opt_out` — `allow_row_mutation=True` bypasses the scan and the mutation is persisted (as it always was, pre-fix).
- `test_old_row_reference_not_flagged` — reading/comparing `old_row` isn't mistaken for a `row.` write.

Full repo suite (`python3 run_tests.py`) — zero regressions, all 12 example dirs pass, including the pre-existing `examples/multi_relns/tests/test_link_disambiguation.py` (the real-world case that exposed the false-positive during implementation).
