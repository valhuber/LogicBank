from typing import Callable

from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm import session

from logic_bank.rule_bank import rule_bank_withdraw  # reduce circular imports
import logic_bank.rule_bank.rule_bank_setup as rule_bank_setup
from logic_bank.rule_type.constraint import Constraint
from logic_bank.rule_type.copy import Copy
from logic_bank.rule_type.count import Count
from logic_bank.rule_type.formula import Formula
from logic_bank.rule_type.parent_cascade import ParentCascade, ParentCascadeAction
from logic_bank.rule_type.parent_check import ParentCheck
from logic_bank.rule_type.row_event import EarlyRowEvent, RowEvent, CommitRowEvent
from logic_bank.rule_type.sum import Sum


class LogicBank:
    """
    Logic consists of Rules, and Python.

    Activate your logic by calling

        activate(session: session, activator: my_logic)

    where myLogic is a function that declares your rules and Python.
    """

    @staticmethod
    def activate(session: session, activator: callable):
        """
        register SQLAlchemy listeners

        create RuleBank, load rules - later executed on commit

        raises exception if cycles detected

        :param session: SQLAlchemy session
        :param activator: user function that declares rules (e.g., Rule.sum...)
        """

        rule_bank_setup.setup(session)
        activator()
        rule_bank_setup.compute_formula_execution_order()


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


        Constraint failures raise ConstraintException, e.g.:
            try:
                session.commit()
            except ConstraintException as ce:
                print("Constraint raised: " + str(ce))

        """
        return Constraint(validate=validate, calling=calling, as_condition=as_condition, error_msg=error_msg)

    @staticmethod
    def parent_check(validate: object,
                     error_msg: str = "(error_msg not provided)",
                     enable: bool = True):
        """
        Parent Checks ensure that non-null foreign keys are present in parent class

        Example
           Rule.parent_check(validate=Customer, enable=True, error_msg="Missing Parent")

        Use enable: False to tolerate orphans
            Not recommended - for existing databases with bad data
            Behavior is undefined for other rules (sum, count, parent references, etc)

        Parent_check failures raise ConstraintException, e.g.:
            try:
                session.commit()
            except ConstraintException as ce:
                print("Constraint raised: " + str(ce))

        """
        return ParentCheck(validate=validate, error_msg=error_msg, enable=enable)

    '''
    disabled, per ORM support (retained in case of misunderstandings)
        @staticmethod
        def parent_cascade(validate: object,
                           error_msg: str = "(error_msg not provided)",
                           relationship: str = "*",
                           action: ParentCascadeAction = ParentCascadeAction.NULLIFY):
            """
            Parent Cascade specifies processing for child rows on parent delete
    
            Example
               Rule.parent_cascade(validate=Order, relationship="OrderDetailList", action=ParentCascadeAction.DELETE)
    
            If rule or action not specified, default is ParentCascadeAction.NULLIFY
    
            Parent_cascade with ParentCascadeAction.NULLIFY can raise ConstraintException, e.g.:
                try:
                    session.commit()
                except ConstraintException as ce:
                    print("Constraint raised: " + str(ce))
    
            """
            return ParentCascade(validate=validate, error_msg=error_msg, relationship=relationship, action=action)
    '''

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

