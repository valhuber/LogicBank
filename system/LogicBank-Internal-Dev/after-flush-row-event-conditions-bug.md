---
title: AfterFlushRowEvent.if_condition / when_condition Never Evaluated — Root Cause and Fix
Description: if_condition/when_condition on Rule.after_flush_row_event were never actually evaluated - handler always fired unconditionally - plus 3 more latent bugs in the same unreachable code path, plus a cross-commit nesting-guard leak found while building the regression test
Source: logic_bank/rule_type/row_event.py (AfterFlushRowEvent), logic_bank/exec_trans_logic/listeners.py (after_flush)
Usage: Read before touching AfterFlushRowEvent, AbstractRowEvent._check_and_mark_fired, or listeners.py's after_flush phase
version: 1.0
changelog:
  - 1.0 (Jul 2026) - Reported via GenAI-Logic basic_demo project: a Kafka-publish-on-ship rule (Rule.after_flush_row_event(if_condition=lambda row: row.date_shipped is not None)) fired on every Order insert/update, not just when date_shipped was set. Traced, fixed, and regression-tested in examples/after_flush_row_event/.
---

# AfterFlushRowEvent.if_condition / when_condition Never Evaluated

## TL;DR

`Rule.after_flush_row_event(..., if_condition=lambda row: ...)` never actually called `if_condition` — the handler fired unconditionally, every time, regardless of the condition's value. The bug was reported against a real GenAI-Logic project (`basic_demo`): a Kafka-publish rule meant to fire only when `Order.date_shipped` was set instead fired on every Order insert/update. Fixing the obvious bug uncovered three more defects in the same method, all masked by the first one (the code paths were unreachable), plus a fifth, unrelated bug in the nesting-suppression guard shared by all row-event types, found only because the regression test exercised the same session-resident row across two separate commits — the exact "look up an existing Order, then ship it later" pattern the reporter's use case implied.

&nbsp;

## Bug 1 (the reported one): if_condition/when_condition never called

```python
# before (row_event.py __init__)
self.if_condition = lambda row: eval(if_condition)
self.when_condition = lambda row: eval(when_condition)
```

The public factory (`Rule.after_flush_row_event`, `logic_bank.py`) documents and type-hints both params as **callables** — `if_condition=lambda row: row.date_shipped is not None` — but the constructor treated them as **strings to `eval()`**. `eval()` on a lambda object raises `TypeError` immediately if ever invoked. It was never invoked (see Bug 2), so this was never observed.

**Fix:** store the callable directly — `self.if_condition = if_condition`.

&nbsp;

## Bug 2: dead branching in execute() — if_condition was checked for non-None, never called

```python
# before (row_event.py execute())
do_event = True
if self.if_condition is not None and self.when_condition is not None:
    pass                                    # <-- if_condition set → falls here, do_event stays True
elif self.as_condition is not None:         # <-- AttributeError bait, see Bug 3
    do_event = self._as_condition(row=logic_row.row)
elif self.when_condition is not None:
    ...
```

Because `when_condition` was *always* constructed as a lambda in `__init__` (even when the caller never passed one — see Bug 1's twin: `self.when_condition = lambda row: eval(when_condition)` runs unconditionally), `self.when_condition is not None` was **always true**. So any call with `if_condition` set landed in the first branch — `pass`, leaving `do_event = True` — and `if_condition` was never actually consulted for its truth value.

**Fix:** rewrote as a proper if/elif on which parameter was actually supplied:
```python
if self.if_condition is not None:
    do_event = self.if_condition(logic_row.row) == True
elif self.when_condition is not None:
    ...
```

&nbsp;

## Bug 3: `self.as_condition` / `self._as_condition` don't exist on this class

`_as_condition` is a `Constraint` attribute (`rule_type/constraint.py`) — `AfterFlushRowEvent` never had one. This branch was unreachable (Bug 2's first branch always won when `if_condition` was set), so the `AttributeError` this would raise was never hit. Removed entirely; `if_condition` now serves the "simple predicate" case `as_condition` would have.

&nbsp;

## Bug 4: `logic_row.is_update` — wrong name, and missing `()`

```python
# before
if logic_row.is_update:
```

`LogicRow` has `is_updated(self) -> bool` (with `d`), and — critically — it's a **plain method, not a property**. `logic_row.is_update` doesn't exist at all (`AttributeError`); even the correctly-spelled `logic_row.is_updated` (no parens) would silently be a truthy bound-method object, not the boolean it looks like. This branch was also unreachable before Bug 2's fix (the `when_condition`-only path was never reached), so neither the `AttributeError` nor the truthy-bound-method trap had ever fired.

**Fix:** `if logic_row.is_updated():` — grep confirms this is the *only* call site of `is_updated` anywhere in the codebase, so this method had never been exercised correctly before.

&nbsp;

## Bug 5 (found while regression-testing, not in the original report): nesting guard leaks across commits

`AbstractRowEvent._check_and_mark_fired()` suppresses re-fire of an event "on the same row within the same flush cycle" (e.g., an `Allocate` cascade loop) by stashing a `set()` of already-fired rule instances directly on the SQLAlchemy mapped row object: `logic_row.row._lb_fired_events`. That set was **never cleared** — it lives as long as the Python row object does, not just for one flush cycle.

Concretely: insert an `Order` (commit #1) → `_lb_fired_events` gets created and populated on that `Order` instance. Later, in the *same session*, query that same `Order` back, set `date_shipped`, commit again (commit #2, a completely separate flush) → the guard sees the rule instances already in `_lb_fired_events` from commit #1 and suppresses them as "nesting," even though this is an unrelated, later transaction. Every `AfterFlushRowEvent` (and `CommitRowEvent`/`RowEvent`/`EarlyRowEvent`, which share the same guard) on that row silently stops firing forever, for the rest of the session's life.

This is exactly the reporter's real-world shape: look up an existing Order, ship it later, expect the Kafka-publish rule to fire on *that* commit. Without this fix, Bugs 1-4 alone would still leave the handler dead on any row touched more than once in the same session.

**Fix** (`listeners.py`, end of `after_flush`'s per-row loop — the last phase that consults the guard in a given flush):
```python
if hasattr(each_logic_row.row, '_lb_fired_events'):
    del each_logic_row.row._lb_fired_events
```
Clearing here (not at flush *start*) means all four row-event types' in-flush nesting suppression is unaffected — it still only clears after the flush that set it has fully finished, including the `after_flush` phase itself.

&nbsp;

## Why this stayed hidden

Bugs 1-4 are a stack of masking failures: fixing the outer one exposes the next. `if_condition`/`when_condition` had **zero existing test coverage** anywhere in the repo (grepped — the only real usage, `examples/banking/logic/rules_bank.py`, calls `after_flush_row_event` with neither parameter, so none of this code ever ran). Bug 5 is a different shape entirely — not a masking chain, but a guard designed for one purpose (suppress same-flush re-entrancy) silently overreaching into a second, unintended one (suppress cross-commit re-fire) because nothing ever cleared its state.

&nbsp;

## Regression tests

New dedicated example: `examples/after_flush_row_event/` (own gold DB, single `Order` table with `date_shipped`/`notes`, mirrors the bug report's basic_demo scenario). `logic/rules_bank.py` declares three `after_flush_row_event` rules on the same class — unconditional, `if_condition`, and `when_condition` — each appending to a module-level list so the test can assert exactly which rows triggered which handler.

`tests/test_after_flush_row_event.py`, three steps against the **same session and same row object** (to also exercise Bug 5):
1. Insert `Order`, `date_shipped=None` — unconditional handler fires; `if_condition`/`when_condition` handlers must NOT (Bug 1/2 regression).
2. Update the same row, set `date_shipped` — `if_condition` fires (now True); `when_condition` fires (False→True transition) (Bug 4/5 regression — this update is a second, separate commit on the same row instance).
3. Update the same row again, `date_shipped` unchanged (still set) — `if_condition` fires again (level-triggered, re-evaluated every time); `when_condition` must NOT fire again (edge-triggered, no False→True transition this time).

Confirmed: fails without either the `row_event.py` fix or the `listeners.py` nesting-guard-clear fix; passes with both. Full repo suite (`python3 run_tests.py`) — zero regressions, all 10 example dirs pass.
