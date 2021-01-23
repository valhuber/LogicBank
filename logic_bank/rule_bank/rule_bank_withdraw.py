from typing import TypedDict, List

import sqlalchemy
from sqlalchemy.orm import object_mapper

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.constraint import Constraint
from logic_bank.rule_type.copy import Copy
from logic_bank.rule_type.count import Count
from logic_bank.rule_type.formula import Formula
from logic_bank.rule_type.parent_check import ParentCheck
from logic_bank.rule_type.row_event import EarlyRowEvent
from logic_bank.rule_type.sum import Sum
from logic_bank.util import get_child_class_name

"""
There really want to be instance methods on RuleBank, but circular imports...
FIXME design
"""


class RoleRules:
    """returns list of rules grouped by role, so logic can access related row only once
    (not once per rule)
    """

    def __init__(self):
        self._role_name = ""
        self._role_rules = []  # list of rule objects


class CopyRulesForTable(TypedDict):
    copy_rules: List[Copy]
    label: str


def copy_rules(logic_row: LogicRow) -> CopyRulesForTable:
    """dict(<role_name>, copy_rules[]
    """
    rule_bank = RuleBank()
    role_rules_list = {}  # dict of RoleRules
    if logic_row.name in rule_bank.orm_objects:
        for each_rule in rule_bank.orm_objects[logic_row.name].rules:
            if isinstance(each_rule, Copy):
                role_name = each_rule._from_parent_role
                if role_name not in role_rules_list:
                    role_rules_list[role_name] = []
                role_rules_list[role_name].append(each_rule)
    return role_rules_list

"""
AbstractRule Bank is a dict of <table><rule-list>, e.g.:

Table[Customer] rules:
  Constraint Function: None 
  Derive Customer.balance as Sum(OrderList.AmountTotal Where ShippedDate not None)
  Derive Customer.OrderCount as Count(Order Where ShippedDate not None)
Table[Order] rules:
  Derive Order.AmountTotal as Sum(OrderDetail.Amount Where None)
Table[OrderDetail] rules:
  Derive OrderDetail.Amount as Formula Function: None 
  Derive OrderDetail.UnitPrice as Copy(Product.UnitPrice)
"""


def aggregate_rules(child_logic_row: LogicRow) -> dict:
    """returns dict(<parent_role_name>, sum/count_rules[] for given child_table_name

    This requires we **invert** the RuleBank,
      to find sums that reference child_table_name, grouped by parent_role
    e.g., for child_logic_row "Order", we return
      ["Order", (Customer.balance, Customer.order_count...)
      ["Employee, (Employee.order_count)]
    """
    result_role_rules_list = {}  # dict of RoleRules

    child_mapper = object_mapper(child_logic_row.row)
    rule_bank = RuleBank()
    relationships = child_mapper.relationships
    for each_relationship in relationships:  # eg, order has parents cust & emp, child orderdetail
        if each_relationship.direction == sqlalchemy.orm.interfaces.MANYTOONE:  # cust, emp
            child_role_name = each_relationship.back_populates  # eg, OrderList
            if child_role_name is None:
                child_role_name = child_mapper.class_.__name__  # default TODO design review
            parent_role_name = each_relationship.key   # eg, Customer TODO design review
            parent_class_name = each_relationship.entity.class_.__name__
            if parent_class_name in rule_bank.orm_objects:
                parent_rules = rule_bank.orm_objects[parent_class_name].rules
                for each_parent_rule in parent_rules:  # (..  bal = sum(OrderList.amount) )
                    if isinstance(each_parent_rule, (Sum, Count)):
                        if each_parent_rule._child_role_name == child_role_name:
                            if parent_role_name not in result_role_rules_list:
                                result_role_rules_list[parent_role_name] = []
                            result_role_rules_list[parent_role_name].append(each_parent_rule)
                            each_parent_rule._parent_role_name = parent_role_name
    return result_role_rules_list


def rules_of_class(logic_row: LogicRow, a_rule_class: (Formula, Constraint, EarlyRowEvent, ParentCheck)) -> list:
    """withdraw rules of designated a_class
    """
    rule_bank = RuleBank()
    rules_list = []
    role_rules_list = {}  # dict of RoleRules
    if logic_row.name in rule_bank.orm_objects:
        for each_rule in rule_bank.orm_objects[logic_row.name].rules:
            if isinstance(each_rule, a_rule_class):
                rules_list.append(each_rule)
    return rules_list


def get_formula_rules(class_name: str) -> list:
    """withdraw rules of designated a_class
    """
    rule_bank = RuleBank()
    rules_list = []
    role_rules_list = {}  # dict of RoleRules
    for each_rule in rule_bank.orm_objects[class_name].rules:
        if isinstance(each_rule, Formula):
            rules_list.append(each_rule)
    return rules_list


def generic_rules_of_class(a_class: (Formula, Constraint, EarlyRowEvent)) -> list:
    """withdraw rules of the "*" (any) class
    """
    rule_bank = RuleBank()
    rules_list = []
    role_rules_list = {}  # dict of RoleRules
    if "*" in rule_bank.orm_objects:
        for each_rule in rule_bank.orm_objects["*"].rules:
            if isinstance(each_rule, a_class):
                rules_list.append(each_rule)
    return rules_list


def get_meta_data():
    rule_bank = RuleBank()
    return rule_bank._metadata


def get_session():
    rule_bank = RuleBank()
    return rule_bank._session


def get_referring_children(parent_logic_row: LogicRow) -> dict:
    """
    return RulesBank[class_name].referring_children (create if None)
    referring_children is <parent_role_name>, parent_attribute_list()
    """
    rule_bank = RuleBank()
    if parent_logic_row.name not in rule_bank.orm_objects:
       return {}
    else:
        # sigh, best to have built this in rule_bank_setup, but unable to get mapper
        # FIXME design is this threadsafe?
        table_rules = rule_bank.orm_objects[parent_logic_row.name]
        result = table_rules.referring_children
        table_rules.referring_children = {}
        parent_mapper = object_mapper(parent_logic_row.row)
        parent_relationships = parent_mapper.relationships
        for each_parent_relationship in parent_relationships:  # eg, order has parents cust & emp, child orderdetail
            if each_parent_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # cust, emp
                parent_role_name = each_parent_relationship.back_populates  # eg, OrderList
                table_rules.referring_children[parent_role_name] = []
                child_role_name = each_parent_relationship.key
                child_class_name = get_child_class_name(each_parent_relationship)  # eg, OrderDetail
                if child_class_name not in rule_bank.orm_objects:
                    pass  # eg, banking - ALERT is child of customer, has no rules, that's ok
                else:
                    child_table_rules = rule_bank.orm_objects[child_class_name].rules
                    if parent_role_name is None:
                        raise Exception("Relationship is missing 'back populates' for parent: " +
                                        parent_logic_row.__str__())
                    search_for_rew_parent = "row." + parent_role_name
                    for each_rule in child_table_rules:
                        if isinstance(each_rule, (Formula, Constraint)):  # eg, OrderDetail.ShippedDate
                            rule_text = each_rule.get_rule_text()  #        eg, row.OrderHeader.ShippedDate
                            rule_words = rule_text.split()
                            for each_word in rule_words:
                                if each_word.startswith(search_for_rew_parent):
                                    rule_terms = each_word.split(".")
                                    # if parent_role_name not in table_rules.referring_children:
                                    #    table_rules.referring_children[parent_role_name] = ()
                                    table_rules.referring_children[parent_role_name].append(rule_terms[2])
        return table_rules.referring_children
