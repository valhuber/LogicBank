from typing import Callable

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import session

from logic_bank.rule_bank import rule_bank_withdraw  # reduce circular imports
from logic_bank.rule_bank.rule_bank_setup import setup, validate
from logic_bank.rule_type.constraint import Constraint
from logic_bank.rule_type.copy import Copy
from logic_bank.rule_type.count import Count
from logic_bank.rule_type.formula import Formula
from logic_bank.rule_type.row_event import EarlyRowEvent, RowEvent, CommitRowEvent
from logic_bank.rule_type.sum import Sum


class LogicBank:
    """
    Logic consists of Rules, and Python.

    Activate your logic,
    providing a function that declares your rules and Python.
    """

    def activate(session: session, activator: callable):
        """
        load rules - executed on commit

        raises exception if cycles detected

        :param session: SQLAlchemy session
        :param activator: function that declares rules (e.g., Rule.sum...)
        :return:
        """
        engine = session.bind.engine
        setup(session, engine)
        activator()
        validate(session, engine)


class Rule:
    """Invoke these functions to *define* rules.
    Rules are *not* run as they are defined,
    they are run when you issue `session.commit()'.
    Use code completion to discover rules.
    """

    @staticmethod
    def sum(derive: InstrumentedAttribute, as_sum_of: any, where: any = None):
        """
        Derive parent column as sum of designated child column, optional where

        Example
          Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
                   where=Lambda row: row.ShippedDate is None)

        Optimized to eliminate / minimize SQLs: Pruning, Adjustment Logic
        """
        return Sum(derive, as_sum_of, where)

    @staticmethod
    def count(derive: InstrumentedAttribute, as_count_of: object, where: any = None):
        """
        Derive parent column as count of designated child rows

        Example
          Rule.count(derive=Customer.UnPaidOrders, as_count_of=Order,
                   where=Lambda row: row.ShippedDate is None)

        Optimized to eliminate / minimize SQLs: Pruning, Adjustment Logic
        """
        return Count(derive, as_count_of, where)

    @staticmethod
    def constraint(validate: object, as_condition: any = None,
                   error_msg: str = "(error_msg not provided)",
                   calling: Callable = None):
        """
        Constraints declare condition that must be true for all commits

        Example
          Rule.constraint(validate=Customer, as_condition=lambda row: row.Balance <= row.CreditLimit,
                          error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
        """
        return Constraint(validate=validate, calling=calling, as_condition=as_condition, error_msg=error_msg)  # --> load_logic

    @staticmethod
    def formula(derive: InstrumentedAttribute, calling: Callable = None,
                as_expression: Callable = None, as_exp: str = None):
        """
        Formulas declare column value, based on current and parent rows

        Example
          Rule.formula(derive=OrderDetail.Amount,
                       as_expression=lambda row: row.UnitPrice * row.Quantity)

        Unlike Copy rules, Parent changes are propagated to child row(s)
        Supply 1 (one) of the following:
          * as_exp - string (for very short expressions - price * quantity)
          * ex_expression - lambda (for type checking)
          * calling - function (for more complex formula, with old_row)
        """
        return Formula(derive=derive, calling=calling, as_exp=as_exp, as_expression=as_expression)

    @staticmethod
    def copy(derive: InstrumentedAttribute, from_parent: any):
        """
        Copy declares child column copied from parent column

        Example
          Rule.copy(derive=OrderDetail.UnitPrice, from_parent=Product.UnitPrice)

        Unlike formulas references, parent changes are *not* propagated to children
        """
        return Copy(derive=derive, from_parent=from_parent)

    @staticmethod
    def early_row_event(on_class: object, calling: Callable = None):
        """
        Row Events are Python functions called before logic
        Possible multiple calls per transaction
        Use: computing foreign keys...
        """
        EarlyRowEvent(on_class, calling)  # --> load_logic

    @staticmethod
    def row_event(on_class: object, calling: Callable = None):
        """
        Row Events are Python functions called during logic, after formulas/constraints
        Possible multiple calls per transaction
        Use: recursive explosions (e.g, Bill of Materials)
        """
        RowEvent(on_class, calling)  # --> load_logic

    @staticmethod
    def commit_row_event(on_class: object, calling: Callable = None):
        """
        Row Events are Python functions called during logic, after formulas/constraints

        Example
            Rule.commit_row_event(on_class=Order, calling=congratulate_sales_rep)

        1 call per row, per transaction
        Use: send mail/message
        """
        return CommitRowEvent(on_class, calling)  # --> load_logic

