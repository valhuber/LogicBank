from typing import Callable

# from logic_bank.exec_row_logic.logic_row import LogicRow <== circular import (??)
import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule


class AbstractRowEvent(AbstractRule):
    _function = None
    _allow_event_nesting = False

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False):
        super(AbstractRowEvent, self).__init__(on_class)
        self._function = calling
        self._allow_event_nesting = allow_event_nesting
        ll = RuleBank()
        ll.deposit_rule(self)

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
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False):
        super(EarlyRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)


class RowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False):
        super(RowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)


class CommitRowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 allow_event_nesting: bool = False):
        super(CommitRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)


class AfterFlushRowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None,
                 if_condition: Callable = None,
                 when_condition: Callable = None,
                 with_args: dict = None,
                 allow_event_nesting: bool = False):
        super(AfterFlushRowEvent, self).__init__(on_class=on_class, calling=calling, allow_event_nesting=allow_event_nesting)
        self.if_condition = lambda row: eval(if_condition)
        self.when_condition = lambda row: eval(when_condition)
        self.with_args = with_args

    def execute(self, logic_row: LogicRow):
        AbstractRule.execute(self, logic_row)
        if not self._check_and_mark_fired(logic_row):
            return
        do_event = True
        if self.if_condition is not None and self.when_condition is not None:
            pass
        elif self.as_condition is not None:
            do_event = self._as_condition(row=logic_row.row)
        elif self.when_condition is not None:
            current_row = self._when_condition(row=logic_row.row)
            old_row = False
            if logic_row.is_update:
                old_row = self._when_condition(row=logic_row.old_row)
            do_event = current_row == True and old_row == False
        if do_event:
            if self.with_args is None:
                value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)
            else:
                value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row, with_args=self.with_args)
        # print(f'Event END {str(self)} on {str(logic_row)}')
