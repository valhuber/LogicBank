import inspect
import re
from typing import Callable

# from logic_bank.exec_row_logic.logic_row import LogicRow <== circular import (??)
import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule

# matches a standalone `row.<attr> =` (assignment) - not `row.attr ==`/`<=`/`>=`/`!=`,
# not `old_row.attr =`, and not `something.row.attr =` (eg new_emp_logic_row.row.name = ...,
# a mutation of a freshly-constructed row via LogicRow.row - safe, not the event's own `row`)
_ROW_ATTR_ASSIGNMENT = re.compile(r'(?<![.\w])row\.\w+\s*=(?!=)')


def _find_row_mutation(calling: Callable) -> str:
    """
    Textual scan (same inspect.getsource() approach as Formula/Constraint's
    dependency scan - see dependency-scanning.md for its known limitations:
    won't see mutations hidden in a called helper function, only literal
    `row.<attr> =` in the scanned source) for a direct write to `row`.

    Returns the offending source line, or "" if none found.
    """
    if calling is None:
        return ""
    try:
        source = inspect.getsource(calling)
    except (OSError, TypeError):
        return ""  # e.g. built-in/C function, or source unavailable
    for each_line in source.splitlines():
        if _ROW_ATTR_ASSIGNMENT.search(each_line):
            return each_line.strip()
    return ""


class AbstractRowEvent(AbstractRule):
    _function = None
    _allow_event_nesting = False
    _mutates_row_after_cascade = False
    """ True for RowEvent/CommitRowEvent - see _check_row_mutation() """

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False,
                 allow_row_mutation: bool = False):
        super(AbstractRowEvent, self).__init__(on_class)
        self._function = calling
        self._allow_event_nesting = allow_event_nesting
        if self._mutates_row_after_cascade and not allow_row_mutation:
            self._check_row_mutation(calling)
        ll = RuleBank()
        ll.deposit_rule(self)

    def _check_row_mutation(self, calling: Callable):
        """
        RowEvent/CommitRowEvent fire AFTER this row's own Formula/Sum/Count/
        Constraint/CommitConstraint cascade has already run for this flush -
        there is no second pass. A `row.<attr> = value` here is silently
        persisted (the flush hasn't happened yet) but never re-derived-from
        or re-validated - see system/LogicBank-Internal-Dev/commit-event-mutation-gap.md.

        Sets self._load_error (picked up by RuleBank.deposit_rule -> the usual
        LBActivateException channel) if a direct `row.attr =` write is found.
        Best-effort/textual - pass allow_row_mutation=True to bypass (e.g., for
        writes to a plain, non-derived/non-constrained column).
        """
        offending_line = _find_row_mutation(calling)
        if offending_line:
            fn_name = calling.__name__ if calling else "?"
            self._load_error = (
                f"{type(self).__name__} {self.table}.{fn_name}() appears to mutate row "
                f"(\"{offending_line}\") - this event fires AFTER the row's own rule cascade, "
                f"so the mutation is persisted WITHOUT being re-derived-from or re-validated. "
                f"See system/LogicBank-Internal-Dev/commit-event-mutation-gap.md. "
                f"Pass allow_row_mutation=True if this is intentional."
            )

    def __str__(self):
        return f'RowEvent {self.table}.{self._function.__name__}() '

    def _check_and_mark_fired(self, logic_row) -> bool:
        """
        Enforce allow_event_nesting=False (default): suppress re-fire of this event
        on the same row within the same flush cycle (e.g., Allocate cascade loop).
        Uses row._lb_fired_events set — shared across all LogicRow wrappers for same row.
        Keyed by rule instance (self) — works even when _function is None (e.g., Allocate).
        Returns True if event should fire, False if suppressed.
        """
        if not hasattr(logic_row.row, '_lb_fired_events'):
            logic_row.row._lb_fired_events = set()
        if self in logic_row.row._lb_fired_events and not self._allow_event_nesting:
            fn_name = self._function.__name__ if self._function else type(self).__name__
            logic_row.log(f'Event nesting suppressed: {fn_name}')
            return False
        logic_row.row._lb_fired_events.add(self)
        return True

    def execute(self, logic_row: LogicRow):
        AbstractRule.execute(self, logic_row)
        if self._check_and_mark_fired(logic_row):
            value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)


class EarlyRowEvent(AbstractRowEvent):
    """ Fires BEFORE this row's own rule cascade (_early_row_events()) - mutating
    `row` here is safe and is this event's documented purpose; not scanned. """
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False):
        super(EarlyRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)


class RowEvent(AbstractRowEvent):
    """ Fires AFTER this row's own rule cascade (_row_events(), end of update()/insert())
    - see AbstractRowEvent._check_row_mutation(). """
    _function = None
    _mutates_row_after_cascade = True

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False,
                 allow_row_mutation: bool = False):
        super(RowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting,
                                       allow_row_mutation=allow_row_mutation)


class CommitRowEvent(AbstractRowEvent):
    """ Fires AFTER all rows' cascades, still within before_flush (Commit Logic Phase)
    - see AbstractRowEvent._check_row_mutation(). """
    _function = None
    _mutates_row_after_cascade = True

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False,
                 allow_row_mutation: bool = False):
        super(CommitRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting,
                                             allow_row_mutation=allow_row_mutation)


class AfterFlushRowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 if_condition: Callable = None,
                 when_condition: Callable = None,
                 with_args: dict = None,
                 allow_event_nesting: bool = False):
        super(AfterFlushRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)
        self.if_condition = if_condition
        self.when_condition = when_condition
        self.with_args = with_args

    def execute(self, logic_row: LogicRow):
        AbstractRule.execute(self, logic_row)
        if not self._check_and_mark_fired(logic_row):
            return
        do_event = True
        if self.if_condition is not None:
            do_event = self.if_condition(logic_row.row) == True
        elif self.when_condition is not None:
            current_row = self.when_condition(logic_row.row)
            old_row = False
            if logic_row.is_updated():
                old_row = self.when_condition(logic_row.old_row)
            do_event = current_row == True and old_row == False
        if do_event:
            if self.with_args is None:
                value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)
            else:
                value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row, with_args=self.with_args)
        # print(f'Event END {str(self)} on {str(logic_row)}')
