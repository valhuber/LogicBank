import inspect
from typing import Callable, Sequence

from sqlalchemy.orm.attributes import InstrumentedAttribute

import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.util import ConstraintException


class Constraint(AbstractRule):

    _function = None

    def __init__(self, validate: object,
                 error_msg: str,
                 calling: Callable = None,
                 as_condition: object = None,  # str or lambda boolean expression
                 error_attributes: Sequence[InstrumentedAttribute] = None):
        super(Constraint, self).__init__(validate)
        # self.table = validate  # setter finds object
        self._error_msg = error_msg
        self._as_condition = as_condition
        self._calling = calling
        self.error_attributes = error_attributes
        if calling is None and as_condition is None:
            msg = "Constraint " + str + " requires calling or as_expression"
            ll = RuleBank()
            if ll.constraint_event:
                ll.constraint_event(message=msg, logic_row=None, constraint=None)
            raise ConstraintException(msg)
        if calling is not None and as_condition is not None:
            msg = "Constraint " + str + " either calling or as_expression"
            ll = RuleBank()
            if ll.constraint_event:
                ll.constraint_event(message=msg, logic_row=None, constraint=None)
            raise ConstraintException(msg)
        if calling is not None:
            self._function = calling
        elif isinstance(as_condition, str):
            self._as_condition = lambda row: eval(as_condition)
        ll = RuleBank()
        ll.deposit_rule(self)

    def __str__(self):
        return f'Constraint Function: {str(self._function)} '

    def get_rule_text(self):
        text = self._as_condition
        if self._function is not None:
            text = inspect.getsource(self._function)
        if not isinstance(text, str):
            text = inspect.getsource(text)  # lambda
        return text

    def execute(self, logic_row: LogicRow):
        # logic_row.log(f'Constraint BEGIN {str(self)} on {str(logic_row)}')
        if self._function is not None:
            value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)
        else:
            value = self._as_condition(row=logic_row.row)

        if value:
            pass
        elif not value:
            row = logic_row.row
            msg = eval(f'f"""{self._error_msg}"""')
            from sqlalchemy import exc
            # exception = exc.DBAPIError(msg, None, None)  # 'statement', 'params', and 'orig'
            logic_row.log(f'Constraint Failure: {msg}')
            ll = RuleBank()
            if ll.constraint_event:
                ll.constraint_event(message=msg, logic_row=logic_row, constraint=self)
            raise ConstraintException(msg)
        else:
            raise RuntimeError(f'Constraint did not return boolean: {str(self)}')
        logic_row.log_engine(f'Constraint END {str(self)} on {str(logic_row)}')
