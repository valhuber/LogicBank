from typing import Callable

# from logic_bank.exec_row_logic.logic_row import LogicRow <== circular import (??)
import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule


class AbstractRowEvent(AbstractRule):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None):
        super(AbstractRowEvent, self).__init__(on_class)
        self._function = calling
        ll = RuleBank()
        ll.deposit_rule(self)

    def __str__(self):
        return f'RowEvent Function: {str(self._function)} '

    def execute(self, logic_row: LogicRow):
        # logic_row.log(f'Event BEGIN {str(self)} on {str(logic_row)}')
        value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)
        # print(f'Event END {str(self)} on {str(logic_row)}')


class EarlyRowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None):
        super(EarlyRowEvent, self).__init__(on_class=on_class, calling=calling)


class RowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None):
        super(RowEvent, self).__init__(on_class=on_class, calling=calling)


class CommitRowEvent(AbstractRowEvent):
    _function = None

    def __init__(self, on_class: object,
                 calling: Callable = None):
        super(CommitRowEvent, self).__init__(on_class=on_class, calling=calling)
