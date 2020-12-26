import inspect
from typing import Callable

from sqlalchemy.orm.attributes import InstrumentedAttribute

import logic_bank.exec_row_logic.logic_row as LogicRow
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.derivation import Derivation


class Formula(Derivation):

    def __init__(self, derive: InstrumentedAttribute,
                 as_exp: str = None,              # for very short expressions
                 as_expression: Callable = None,  # short, with type checking
                 calling: Callable = None,        # complex formula
                 no_prune: bool = False           # never prune
                 ):
        """
        Specify rep
          * as_exp - string (for very short expressions - price * quantity)
          * ex_expression - lambda (for type checking)
          * calling - function (for more complex formula, with old_row)

        """
        super(Formula, self).__init__(derive)

        self._as_exp = as_exp
        self._as_expression = as_expression
        self._function = calling
        self._no_prune = no_prune

        self._as_exp_lambda = None   # we exec this, or _function

        valid_count = 0
        if as_exp is not None:
            self._as_exp_lambda = lambda row: eval(as_exp)
            valid_count += 1
        if as_expression is not None:
            self._as_exp_lambda = as_expression
            valid_count += 1
        if calling is not None:
            valid_count += 1
        if valid_count != 1:
            raise Exception(f'Formula requires one of as_exp, as_expression or calling')
        self._dependencies = []
        text = self.get_rule_text()
        self.parse_dependencies(rule_text=text)
        self._exec_order = -1  # will be computed in rule_bank_setup (all rules loaded)
        rb = RuleBank()
        rb.deposit_rule(self)

    def execute(self, logic_row: LogicRow):
        """
        executes EITHER:
          - as_exp_lambda(row=logic_row.row), OR
          - _function(row, old_row, logic_row)
        """
        # logic_row.log(f'Formula BEGIN {str(self)} on {str(logic_row)}')
        if self._function is not None:
            value = self._function(row=logic_row.row,
                                   old_row=logic_row.old_row, logic_row=logic_row)
        elif self._as_exp_lambda is not None:
            value = self._as_exp_lambda(row=logic_row.row)
        else:
            raise Exception("Internal Error - what to execute")
        old_value = getattr(logic_row.row, self._column)
        if value != old_value:
            setattr(logic_row.row, self._column, value)
            logic_row.log(f'Formula {self._column}')

    def get_rule_text(self):
        if self._function is not None:
            text = inspect.getsource(self._function)
        elif self._as_exp is not None:
            text = self._as_exp
        else:
            text = inspect.getsource(self._as_exp_lambda)
        return text.strip()

    def __str__(self):
        rule_text = "<function>"
        if self._function is None:
            rule_text = self.get_rule_text()
        if len(rule_text) > 50:
            rule_text = rule_text[0:49] + " [...]"
        return super().__str__() + \
               f'Formula ({self._exec_order}): {rule_text}'
