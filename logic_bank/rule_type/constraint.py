import inspect
from typing import Callable, Sequence

from sqlalchemy.orm.attributes import InstrumentedAttribute

import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.util import ConstraintException


class AbstractConstraint(AbstractRule):
    """
    Shared implementation for Constraint (checked per-row, mid-cascade,
    during before_flush) and CommitConstraint (checked once, after the
    transaction's cascade has settled, during after_flush).

    Subclasses differ only in *when* execute() is invoked (see
    exec_row_logic/logic_row.py's _constraints() vs. exec_trans_logic/
    listeners.py's after_flush) - the validate/error_msg/calling/
    as_condition shape and evaluation logic are identical.
    """

    _function = None

    def __init__(self, validate: object,
                 error_msg: str,
                 calling: Callable = None,
                 as_condition: object = None,  # str or lambda boolean expression
                 error_attributes: Sequence[InstrumentedAttribute] = None):
        super(AbstractConstraint, self).__init__(validate)
        # self.table = validate  # setter finds object
        self._error_msg = error_msg
        self._as_condition = as_condition
        self._calling = calling
        self.error_attributes = error_attributes
        if calling is None and as_condition is None:
            msg = str(type(self).__name__) + " " + str(self) + " requires calling or as_expression"
            ll = RuleBank()
            if ll.constraint_event:
                ll.constraint_event(message=msg, logic_row=None, constraint=None)
            raise ConstraintException(msg)
        if calling is not None and as_condition is not None:
            msg = str(type(self).__name__) + " " + str(self) + " either calling or as_expression"
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
        return f'{type(self).__name__} Function: {str(self._function)} '

    def get_referenced_attributes(self) -> list[str]:
        referenced_attributes = list()
        rule_text = self.get_rule_text()
        if 'row.CreditLimit)' in rule_text:
            pass  # good breakpoint
        self.parse_dependencies(rule_text)
        for each_attribute in self._dependencies:
            referenced_attributes.append(f'{self.table}.{each_attribute}: constraint')
        return referenced_attributes

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
            AbstractRule.execute(self, logic_row)
            row = logic_row.row
            msg = eval(f'f"""{self._error_msg}"""')
            from sqlalchemy import exc
            # exception = exc.DBAPIError(msg, None, None)  # 'statement', 'params', and 'orig'
            logic_row.log(f'{type(self).__name__} Failure: {msg}')
            logic_row.row_sets.print_used()
            ll = RuleBank()
            if ll.constraint_event:
                ll.constraint_event(message=msg, logic_row=logic_row, constraint=self)
            raise ConstraintException(msg)
        else:
            raise RuntimeError(f'{type(self).__name__} did not return boolean: {str(self)}')
        logic_row.log_engine(f'{type(self).__name__} END {str(self)} on {str(logic_row)}')


class Constraint(AbstractConstraint):
    """
    Checked per-row, inline, during before_flush's row cascade (see
    exec_row_logic/logic_row.py's _constraints(), called from insert/
    update/delete). Runs every time the row is touched this transaction,
    including mid-cascade - so it cannot express a min-cardinality rule
    like "Order must have Items": the Order's own insert is processed
    before its Items exist, so the check fails on a state that was never
    meant to be final. Use CommitConstraint for that case.
    """
    pass


class CommitConstraint(AbstractConstraint):
    """
    Checked once per touched row, after this transaction's cascade has
    fully settled (exec_trans_logic/listeners.py's after_flush) - unlike
    Constraint, it is not re-run on every mid-cascade touch, so it can
    express min-cardinality rules like "Order must have Items" that are
    only meaningful once all of a transaction's inserts/deletes are done.

    Example
        # ensure every Order has at least one OrderDetail
        Rule.count(derive=Order.ItemCount, as_count_of=OrderDetail)
        Rule.commit_constraint(validate=Order,
                        as_condition=lambda row: row.ItemCount > 0,
                        error_msg="Order {row.Id} must have at least one item")

    Not run for rows deleted this transaction (nothing left to validate).
    Runs after the flush has been sent to the DB, so - like
    AfterFlushRowEvent - it must not alter the row; it's a read-only check.
    """
    pass
