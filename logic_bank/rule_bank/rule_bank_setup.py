from datetime import datetime

from sqlalchemy import event, MetaData
from sqlalchemy.engine import Engine

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.exec_trans_logic.listeners import before_flush, before_commit
from sqlalchemy.orm import session
import logging


def setup(a_session: session):
    """
    Create the RuleBank

    Register before_flush listeners

    """
    rules_bank = RuleBank()
    event.listen(a_session, "before_flush", before_flush)
    event.listen(a_session, "before_commit", before_commit)

    rules_bank.orm_objects = {}
    rules_bank._at = datetime.now()
    return rules_bank

def setup_early_row_event_all_classes(early_row_event_all_classes: callable):
    ll = RuleBank()
    ll._early_row_event_all_classes = early_row_event_all_classes


def set_referring_children(rule, dependency: list):
    pass


def compute_formula_execution_order_for_class(class_name: str):
    """
    compute formula._exec_order per formula._dependencies
    """
    formula_list = rule_bank_withdraw.get_formula_rules(class_name)
    formula_list_dict = {}
    for each_formula in formula_list:
        formula_list_dict[each_formula._column] = each_formula
    exec_order = 0
    blocked = False
    while not blocked and exec_order < len(formula_list):
        blocked = True
        for each_formula_name in formula_list_dict:
            each_formula = formula_list_dict[each_formula_name]
            refers_to = ""
            if each_formula._exec_order == -1:
                for each_referenced_col_name in each_formula._dependencies:
                    if each_referenced_col_name in formula_list_dict:
                        referenced_formula = formula_list_dict[each_referenced_col_name]
                        if referenced_formula._exec_order == -1:  # ref'd col done?
                            if each_referenced_col_name != each_formula_name:
                                refers_to = referenced_formula._column
                                break  # can't do me yet - ref'd col may also have rules but not yet loaded
                if refers_to == "":
                    exec_order += 1
                    each_formula._exec_order = exec_order
                    blocked = False
        if blocked:
            cycles = ""
            cycle_count = 0
            for each_formula_name in formula_list_dict:
                each_formula = formula_list_dict[each_formula_name]
                if each_formula._exec_order == -1:
                    if cycle_count > 0:
                        cycles += ", "
                    cycle_count += 1
                    cycles += each_formula._column
            raise Exception("Mapped Class[" + class_name + "] blocked by circular dependencies:" + cycles)


def compute_formula_execution_order() -> bool:
    """
    Determine formula execution order based on "row.xx" references (dependencies),
    (or raise exception if cycles detected).
    """
    rules_bank = RuleBank()
    for each_key in rules_bank.orm_objects:
        compute_formula_execution_order_for_class(class_name=each_key)

    logic_logger = logging.getLogger("logic_logger")
    logic_logger.debug("\nThe following rules have been activated\n")
    list_rules = rules_bank.__str__()
    loaded_rules = list(list_rules.split("\n"))
    for each_rule in loaded_rules:
        logic_logger.debug(each_rule)
    logic_logger.debug("")
    return True
