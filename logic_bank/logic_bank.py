from typing import Callable, Sequence
from sqlalchemy import Column
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
from logic_bank.rule_type.row_event import EarlyRowEvent, RowEvent, CommitRowEvent, AfterFlushRowEvent
from logic_bank.rule_type.sum import Sum
from logic_bank import engine_logger
import functools
import logging
import traceback
import os
from .exceptions import LBActivateException
from .rule_bank.rule_bank import RuleBank

logic_logger = logging.getLogger("logic_logger")


def failsafe(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """
            Wrapper for LoigcBank Rules
            - report logicbank activation errors
            - continue in case $LOGICBANK_FAILSAFE is set
        """
        if make_inactive := True:  # set to True to activate failsafe        
            return func(*args, **kwargs)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tb = traceback.extract_stack()
            for frame in tb:
                if '/logic/' in frame.filename: # project errors (typically in declare_logic.py)
                    logic_logger.error(f"Rule error: {frame.filename}, Line: {frame.lineno}")
                    break
            else:
                logic_logger.error(f"Rule error in unknown file")
            logic_logger.error(f"LogicBank activate error occurred: {e}" )
            if os.getenv("LOGICBANK_FAILSAFE") == "true":
                return None
            raise e

    return wrapper


class LogicBank:
    """
    1. Declare rules, e.g.

        declare_logic():
            Rule.sum(derive=Order.AmountTotal, as_sum_of=OrderDetail.Amount)  # discover with code completion

    2. Activate them:

        LogicBank.activate(session=session, activator=declare_logic)  # register LogicBank listeners to SQLAlchemy

    3. Execute them:

        session.commit()  # LogicBank listeners execute rules relevant for submitted changes

    .. _Rule Summary:
   
   https://apilogicserver.github.io/Docs/Logic/
   
   https://github.com/valhuber/LogicBank/wiki/Rule-Summary

    """

    @staticmethod
    def activate(session: session, activator: callable, constraint_event: callable = None):
        """

        #### Usage (e.g., als - highly recommended)
        
            See `api_logic_server_run -> Config/server_setup -> activate_logicbank`,\n\t\t\tafter opening database to activate logic:

            `LogicBank.activate(session=session, activator=declare_logic.declare_logic, constraint_event=constraint_handler)`

        #### Operation (file: `logic_bank.py`):

            - Calls `rule_bank_setup.setup(session)` to set up the `RuleBank` and register SQLAlchemy listeners

            - Calls your activator to load rules into `RuleBank` (not executed yet)

            - Calls `rule_bank_setup.compute_formula_execution_order()` for dependencies

            - Raises exception if cycles detected, or invalid rules per missing attr references

        #### Subsequent rule execution starts in `exec_row_logic/LogicRow.py on session.commit()`
                
            - `exec_trans_logic/listeners.py` handles the SQLAlchemy events (after_flush etc.) to get changed rows; for each, it calls....

            - `exec_row_logic/LogicRow.py#update()`, which executes the rule_type objects (in TableRules)

        Use constraint_event to log / change class of constraints, for example
            '''
            def constraint_handler(message: str, constraint: Constraint, logic_row: LogicRow):
                error_attrs = ""
                if constraint:
                    if constraint.error_attributes:
                        for each_error_attribute in constraint.error_attributes:
                            error_attrs = error_attrs + each_error_attribute.name + " "
                exception_message = "Custom constraint_handler for: " + message +\
                                    ", error_attributes: " + error_attrs
                logic_row.log(exception_message)
                raise MyConstraintException(exception_message)
            '''

        Arguments:
            session: SQLAlchemy session
            activator: user function that declares rules (e.g., Rule.sum... in als `logic/declare_logic.py`)
            constraint_event: optional user function called on constraint exceptions
        """
        rule_bank = rule_bank_setup.setup(session)
        if constraint_event is not None:
            rule_bank.constraint_event = constraint_event
        try:
            activator()  # in als, called from server_setup - this is logic/declare_logic.py#declare_logic()
        except Exception as e:
            rule_bank.invalid_rules.append(e)

        if debug_show_attributes :=True:
            rules_bank = RuleBank()
            rule_count = 0
            logic_logger.debug(f'\nThe following rules have been loaded')
            list_rules = rules_bank.__str__()
            loaded_rules = list(list_rules.split("\n"))
            for each_rule in loaded_rules:  # rules with bad derive= etc not loaded - no TableRule to own them
                logic_logger.debug(str(each_rule))
                rule_count += 1

        missing_attributes = rule_bank_setup.compute_formula_execution_order()
        if len(rule_bank.invalid_rules) > 0 or len(missing_attributes) > 0:
            #raise Exception(rule_bank.invalid_rules, missing_attributes)  # compare - this logs the errors
            if more_debug := False:
                for each_invalid_rule in rule_bank.invalid_rules:
                    logic_logger.info(f'Invalid Rule: {each_invalid_rule}')
                for each_missing_attribute in missing_attributes:
                    logic_logger.info(f'Missing Attribute: {each_missing_attribute}')
            raise LBActivateException(rule_bank.invalid_rules, missing_attributes)

        rules_bank = RuleBank()
        rule_count = 0
        logic_logger.debug(f'\nThe following rules have been activated')
        list_rules = rules_bank.__str__()
        loaded_rules = list(list_rules.split("\n"))
        for each_rule in loaded_rules:
            logic_logger.debug(each_rule)
            rule_count += 1

        logic_logger.info(f'Logic Bank {rule_bank_setup.__version__} - {rule_count} rules loaded')


class Rule:
    """Invoke these functions to declare rules.

    Rules are *not* run as they are defined,
    they are run when you issue `session.commit()'.

    .. _Rule Summary:
        https://github.com/valhuber/LogicBank/wiki/Rule-Summary

    Use code completion to discover rules and their parameters.
    """

    @failsafe
    @staticmethod
    def sum(derive: Column, as_sum_of: any, where: any = None, child_role_name: str = "", insert_parent: bool=False):
        """
        Derive parent column as sum of designated child column, optional where

        Example
            # derive the customer balance as the sum of the unshipped order amounttotals

            Rule.sum(derive=models.Customer.Balance, as_sum_of=models.Order.AmountTotal,
                where=lambda row: row.ShippedDate is None)

        Optimized to eliminate / minimize SQLs: Pruning, Adjustment Logic

        Automated dependency management: fires iff changes to pk, summed field, where

        Args:
            derive: name of parent <class.attribute> being derived
            as_sum_of: name of child <class.attribute> being summed
            child_role_name: parent's child accessor attribute (required only for disambiguation)
            where: optional where clause, designates which child rows are summed


        """
        return Sum(derive, as_sum_of, where, child_role_name, insert_parent)

    @failsafe
    @staticmethod
    def count(derive: Column, as_count_of: object, where: any = None, child_role_name: str = "", insert_parent: bool=False):
        """
        Derive parent column as count of designated child rows

        Example
            # derive the customer UnPaidOrders as the count of the unshipped orders

            Rule.count(derive=models.Customer.UnPaidOrders, as_count_of=models.Order,
                   where=Lambda row: row.ShippedDate is None)

        Optimized to eliminate / minimize SQLs: Pruning, Adjustment Logic

        Args:
            derive: name of parent <class.attribute> being derived
            as_count_of: name of child <class> being counted
            child_role_name: parent's child accessor attribute (required only for disambiguation)
            where: optional where clause, designates which child rows are counted
        """
        return Count(derive, as_count_of, where, child_role_name, insert_parent)

    @staticmethod
    def constraint(validate: object,
                   calling: Callable = None,
                   as_condition: any = None,
                   error_msg: str = "(error_msg not provided)",
                   error_attributes=None):
        """
        Constraints declare condition that must be true for all commits

        Example
            # ensure the customer balance is less than or equal to the creditlimit

            Rule.constraint(validate=models.Customer,
                          as_condition=lambda row: row.Balance <= row.CreditLimit,
                          error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")


        Constraint failures raise ConstraintException, e.g.:
            try:
                session.commit()
            except ConstraintException as ce:
                print("Constraint raised: " + str(ce))

        @see https://apilogicserver.github.io/Docs/Logic-Type-Constraint/

        Args:
            validate: name of mapped <class>
            calling: function, passed row, old_row, logic_row (complex constraints)
            as_condition: lambda, passed row (simple constraints)
            error_msg: string, with {row.attribute} replacements
            error_attributes: list of attributes

        """
        if error_attributes is None:
            error_attributes = []
        return Constraint(validate=validate, calling=calling, as_condition=as_condition,
                          error_attributes=error_attributes, error_msg=error_msg)

    @staticmethod
    def parent_check(validate: object,
                     error_msg: str = "(error_msg not provided)",
                     enable: bool = True):
        """
        Parent Checks ensure that non-null foreign keys are present in parent class

        Example
           Rule.parent_check(validate=models.Customer, enable=True, error_msg="Missing Parent")

        Parent_check failures raise ConstraintException, e.g.:
            try:
                session.commit()
            except ConstraintException as ce:
                print("Constraint raised: " + str(ce))

        Args:
            validate: name of mapped class
            error_msg: message included in exception (can have {} syntax)
            enable: True (default) = enable, False means disable (tolerate orphans)

        Note: False not recommended - for existing databases with bad data
            Behavior is undefined for other rules (sum, count, parent references, etc)

        """
        return ParentCheck(validate=validate, error_msg=error_msg, enable=enable)

    @failsafe
    @staticmethod
    def formula(derive: Column,
                as_exp: str = None,  # string (for very short expression)
                as_expression: Callable = None,
                calling: Callable = None,
                no_prune: bool = False):
        """
        Formulas declare column value, based on current and parent rows

        Example
            # Items.Amount = Quantity * UnitPrice
            Rule.formula(derive=models.OrderDetail.Amount,
                       as_expression=lambda row: row.UnitPrice * row.Quantity)

        Unlike Copy rules, Parent changes are propagated to child row(s)

        The `calling` function must return a value (else column is nullified)

        Args:
            derive: <class.attribute> being derived
            as_exp: string (for very short expressions - price * quantity)
            as_expression: lambda, passed row (for syntax checking)
            calling: function (for more complex formula, pass row, old_row, logic_row)
            no_prune: disable pruning (rarely used, default False)
        """
        return Formula(derive=derive,
                       calling=calling, as_exp=as_exp, as_expression=as_expression,
                       no_prune=no_prune)

    @failsafe
    @staticmethod
    def copy(derive: Column, from_parent: any):
        """
        Copy declares child column copied from parent column

        Example
            # Store the Items.UnitPrice as a copy from Product.UnitPrice

            Rule.copy(derive=models.OrderDetail.UnitPrice, from_parent=models.Product.UnitPrice)

        Unlike formulas references, parent changes are *not* propagated to children

        Args:
            derive: <class.attribute> being copied into
            from_parent: <parent-class.attribute> source of copy
        """
        return Copy(derive=derive, from_parent=from_parent)

    @staticmethod
    def early_row_event(on_class: object, calling: Callable = None):
        """
        Row Events are Python functions called *before* logic
        Possible multiple calls per transaction
        Use: computing foreign keys...

        Args:
            on_class: <class> for event
            calling: function, passed row, old_row, logic_row
        """
        return EarlyRowEvent(on_class, calling)  # --> load_logic

    @staticmethod
    def early_row_event_all_classes(early_row_event_all_classes: Callable = None):
        """
        early event for all mapped classes, intended for time/date/user stamping, e.g.

        def handle_all(logic_row: LogicRow):
            row = logic_row.row
            if logic_row.ins_upd_dlt == "ins" and hasattr(row, "CreatedOn"):
                row.CreatedOn = datetime.datetime.now()
                logic_row.log("early_row_event_all_classes - handle_all sets 'Created_on"'')

        Rule.early_row_event_all_classes(early_row_event_all_classes=handle_all)

        Args:
            early_row_event_all_classes: function, passed logic_row

        """
        return rule_bank_setup.setup_early_row_event_all_classes(
            early_row_event_all_classes=early_row_event_all_classes)

    @staticmethod
    def row_event(on_class: object, calling: Callable = None):
        """
        Row Events are Python functions called *during* logic, after formulas/constraints
        Possible multiple calls per transaction
        Use: recursive explosions (e.g, Bill of Materials)

        Args:
            on_class: <class> for event
            calling: function, passed row, old_row, logic_row
        """
        return RowEvent(on_class, calling)  # --> load_logic

    @staticmethod
    def commit_row_event(on_class: object, calling: Callable = None):
        """
        Commit Row Events are Python functions *after* all row logic formulas/constraints

        Example
            Rule.commit_row_event(on_class=Order, calling=congratulate_sales_rep)

        1 call per row, per transaction

        Example use: send mail/message

        Args:
            on_class: <class> for event
            calling: function, passed row, old_row, logic_row
        """
        return CommitRowEvent(on_class, calling)  # --> load_logic

    @staticmethod
    def after_flush_row_event(on_class: object, calling: Callable = None):
        """
        After Flush Row Events are Python functions *after* all row logic formulas/constraints,
        and after rows are flushed to disk.

        Unlike commit row events, such rows will reflect DBMS-generated AutoNum values.

        Updates during after_flush are undefined; use Commit Events if updates are required.

        Example
            Rule.after_flush_row_event(on_class=models.Order, calling=send_order_to_shipping)

        1 call per row, per transaction

        Example use: send mail/message including AutoNum values

        Args:
            on_class: <class> for event
            calling: function, passed row, old_row, logic_row
        """
        return AfterFlushRowEvent(on_class, calling)  # --> load_logic

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


class DeclareRule(Rule):
    """
    Same as Rule, but makes clear these statements *declare* rules, e.g.

        declare_logic():

            DeclareRule.sum(derive=models.Order.AmountTotal, as_sum_of=OrderDetail.Amount)

    Activate them:

        LogicBank.activate(session=session, activator=declare_logic)  # registers LogicBank listeners to SQLAlchemy

    Execute them:

        session.commit()  # LogicBank listeners execute rules relevant for submitted changes

    """
    pass
