from collections.abc import Set
from datetime import datetime
from typing import List

from sqlalchemy import event, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy import inspect

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.exec_trans_logic.listeners import before_flush, before_commit, after_flush
from logic_bank.rule_type import abstractrule
from sqlalchemy.orm import session
from sqlalchemy.orm import mapper
import logging

__version__ = "01.20.18"  # missing attrs excp with all excps, fail-save rules, full excp content, w/ fix, singleton


def setup(a_session: session):
    """
    Create the RuleBank

    Register before_flush listeners

    """
    rules_bank = RuleBank()
    rules_bank._session = a_session
    event.listen(a_session, "before_flush", before_flush)
    event.listen(a_session, "before_commit", before_commit)
    event.listen(a_session, "after_flush", after_flush)

    rules_bank.orm_objects = {}
    rules_bank.invalid_rules = []
    rules_bank._at = datetime.now()
    return rules_bank

def setup_early_row_event_all_classes(early_row_event_all_classes: callable):
    ll = RuleBank()
    ll._early_row_event_all_classes = early_row_event_all_classes


def set_referring_children(rule, dependency: list):
    pass

def find_referenced_attributes(rules_bank: RuleBank) -> list[str]:
    """ for each class, find it's rules, and union all rules get_referenced_attributes)() """
    all_referenced_attributes = list()
    all_rules = rules_bank.get_all_rules()
    for each_rule in all_rules:
        debug_rule = str(each_rule)
        if 'parent copy' in debug_rule:
            good_breakpoint = True
        referenced_attributes = each_rule.get_referenced_attributes()
        all_referenced_attributes.extend( referenced_attributes )
    return all_referenced_attributes

def find_missing_attributes(all_attributes: list[str], rules_bank: RuleBank) -> list[str]:
    missing_attributes = list()
    mapper_dict : dict[str, mapper] = None  # class_name -> mapper
    for each_attribute in all_attributes:
        if 'Employee.order_count: constraint' in each_attribute:
            good_breakpoint = True
        class_and_attr = each_attribute.split(':')[0]
        if len(class_and_attr.split('.')) > 2:
            pass  # FIXME - parent reference, need to decode the role name --> table name
        if len(class_and_attr.split('.')) < 2:
            missing_attributes.append(each_attribute)
            continue
        class_name = class_and_attr.split('.')[0]
        attr_name = class_and_attr.split('.')[1]
        if attr_name == 'unit_price':
            good_breakpoint = True
        each_mapper = rules_bank.get_mapper_for_class_name(class_name)
        if each_mapper is None:
            missing_attributes.append(each_attribute)
            continue
        if old_code := False:
            if mapper_dict is None:
                ''' beware - very subtle case
                    referenced attrs may not have rules, so no entry in rules_bank.orm_objects
                    so, we have a use SQLAlchemy meta... to get the mapper
                        from first each_attribute
                        key assumption is 1st each_attribute (rule) will be for a class *with rules*
                '''
                mapper_dict = {}
                table_rules = rules_bank.orm_objects[class_name]  # key assumption, above
                decl_meta = table_rules._decl_meta
                mappers = decl_meta.registry.mappers
                for each_mapper in mappers:
                    each_class_name = each_mapper.class_.__name__
                    if each_class_name not in mapper_dict:
                        mapper_dict[each_class_name] = each_mapper
            if class_name not in mapper_dict:
                missing_attributes.append(each_attribute)
                continue
        if 'unit_price' in each_attribute:
            good_breakpoint = True
        if attr_name not in each_mapper.all_orm_descriptors:
            missing_attributes.append(each_attribute)
    pass
    return missing_attributes


def compute_formula_execution_order_for_class(class_name: str):
    """
    compute formula._exec_order per formula._dependencies... raise excp if cycle
    """
    formula_list = rule_bank_withdraw.get_formula_rules(class_name)
    formula_list_dict = {}
    for each_formula in formula_list:
        formula_list_dict[each_formula._column] = each_formula
    exec_order = 0
    blocked = False
    while not blocked and exec_order < len(formula_list):
        blocked = True  # run thru formulas mult times, delete when dependencies cleared, verify all deleted
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
                if refers_to == "":  # success.. this formula runs at _exec_order
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


def compute_formula_execution_order() -> list[str]:
    """ Determine formula execution order based on "row.xx" references (dependencies).

    Returns:
        list[str]: list of attributes that are missing, have cyclic dependencies, or other issues  (not excp)
    """
    global version
    logic_logger = logging.getLogger("logic_logger")
    rules_bank = RuleBank()

    for each_key in rules_bank.orm_objects:
        compute_formula_execution_order_for_class(class_name=each_key)  # might raise excp

    all_referenced_attributes = find_referenced_attributes(rules_bank)  # now consider other rule attr references
    if do_print_attribute := True:
        logic_logger.debug(f'\nThe following attributes have been referenced\n')
        for each_attribute in all_referenced_attributes:
            logic_logger.debug(f'..{each_attribute}')
    missing_attributes = find_missing_attributes(all_attributes=all_referenced_attributes, rules_bank=rules_bank)
    if len(missing_attributes) > 0:
        pass # raise Exception("Missing attributes:" + str(missing_attributes))
    return missing_attributes  # string array of missing attrs, hopefully empty
