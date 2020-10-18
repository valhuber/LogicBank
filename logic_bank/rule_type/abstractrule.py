from __future__ import annotations
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import object_mapper

from logic_bank import engine_logger
from logic_bank.rule_bank import rule_bank_withdraw
from sqlalchemy.orm import mapperlib

# Circular imports prevent these (geesh ** 2):
# https://stackoverflow.com/questions/33837918/type-hints-solve-circular-dependency
from logic_bank.rule_bank.rule_bank import RuleBank, TableRules  # circular import
# from logic_bank.logic import Base  # circular import
# from logic_bank.rule_bank import rule_bank_setup
# from logic_bank.rule_type import log_dependency
from logic_bank.util import prt


class AbstractRule(object):

    def __init__(self, decl_meta: sqlalchemy.ext.declarative.api.DeclarativeMeta):
        #  failed -- mapped_class = get_class_by_table(declarative_base(), a_table_name)  # User class
        if not isinstance(decl_meta, sqlalchemy.ext.declarative.api.DeclarativeMeta):
            raise Exception("rule definition error, not mapped class: " + str(decl_meta))
        self._decl_meta = decl_meta
        class_name = self.get_class_name(decl_meta)
        self.table = class_name

        self._dependencies = ()
        """
        list of attributes this rule refers to, including parent.attribute
        """

    def get_class_name(self, decl_meta: sqlalchemy.ext.declarative.api.DeclarativeMeta) -> str:
        """
        extract class name from class_
        eg, OrderDetail from <class 'nw.logic.models.OrderDetail'>
        """
        nodal_name = str(decl_meta)
        nodes = nodal_name.split('.')
        class_name = nodes[len(nodes) - 1]
        class_name = class_name[0: len(class_name) - 2]
        return class_name  # FIXME design - got to be a better way

    def parse_dependencies(self, rule_text: str):
        """
        Split rule_text into space-separated words
        Set <rule>._dependencies() to all words starting with "row."
        """
        words = rule_text.split()
        for each_word in words:
            the_word = each_word
            if each_word.startswith("("):
                the_word = each_word[1:]
            if the_word.endswith(")"):
                the_word = each_word[0:len(the_word) - 1]
            if the_word.startswith("row."):  # allow Cust.CreditLimit?
                dependencies = the_word.split('.')
                if len(dependencies) == 2:
                    self._dependencies.append(dependencies[1])
                else:
                    self._dependencies.append(dependencies[1] +
                                              "." + dependencies[2])
                    self.update_referenced_parent_attributes(dependencies)

    def update_referenced_parent_attributes(self, dependencies: list):
        """
        Used by Formulas and constraints log their dependence on parent attributes
        This sets RuleBank.TableRules[mapped_class].referring_children
        dependencies is a list

        But, can't do this now, because meta_contains_role_name = False
        So, do it on the fly in logic_row (which is an ugh)
        """
        meta_contains_role_name = False
        if meta_contains_role_name is False:
            return
        else:
            meta_data = rule_bank_withdraw.get_meta_data()
            child_meta = meta_data.tables[self.table]
            parent_role_name = dependencies[1]
            foreign_keys = child_meta.foreign_keys
            for each_foreign_key in foreign_keys:  # eg, OrderDetail has OrderHeader, Product
                each_parent_class_name = each_foreign_key.name
                each_parent_role_name = each_foreign_key.key
                if parent_role_name == each_parent_role_name:  # eg, OrderHeader
                    rule_bank = RuleBank()
                    if each_parent_class_name not in rule_bank.orm_objects:
                        self._tables[rule_bank] = TableRules()
                    table_rules = self._tables[rule_bank]
                    if table_rules.referring_children is None:
                        table_rules.referring_children = {}
                    if parent_role_name not in table_rules.referring_children:
                        table_rules.referring_children[parent_role_name] = []
                    table_rules.referring_children.append(dependencies[2])
                    engine_logger.debug(prt("child parent dependency: " + dependencies[1]))
                    break
