from __future__ import annotations
from typing import List, TypeVar, Dict
from logic_bank import engine_logger
# from logic_bank.rule_type.abstractrule import AbstractRule  # causes circular import.
from logic_bank.util import prt
from datetime import datetime

# https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class TableRules(object):
    """
    Rules and dependencies for a mapped class, with attributes:
        * rules: List['AbstractRule'] - Sums, Constraints, Formulas etc for this mapped class
        * referring_children: Dict[parent_role_name, List[parent_attr_name]] - for cascade
    """

    def __init__(self):
        self.rules = []  # type: List['AbstractRule']
        self.referring_children = None  # type: None | Dict[str, List[str]]
        """ parent_role_name, parent_attribute_names[]
        set in rule_bank_withdraw """
        self._decl_meta = None


class RuleBank(metaclass=Singleton):  # FIXME design review singleton
    """
    Attributes:

    orm_objects Dict[mapped_class_name: str, List[TableRules]]

    _metadata, _base, _engine from sqlalchemy
    """

    orm_objects = {}  # type: Dict[str, TableRules]
    """ Dict[mapped_class: str, List[TablesRules]] -- rules for a table """
    _at = datetime.now()
    _early_row_event_all_classes = None
    """ a single even handler (function) called for all inserts, updates and deletes """

    def __init__(self):
        self._metadata = None
        self._session = None
        self.constraint_event = None
        self.invalid_rules : list[str] = []  # rule-load failures during activation

    def deposit_rule(self, a_rule: 'AbstractRule'):
        if a_rule._load_error is not None:
            self.invalid_rules.append(a_rule._load_error)
        if hasattr(a_rule, "table"):
            if a_rule.table not in self.orm_objects:
                self.orm_objects[a_rule.table] = TableRules()
            table_rules = self.orm_objects[a_rule.table]
            table_rules._decl_meta = a_rule._decl_meta
            table_rules.rules.append(a_rule)
            engine_logger.debug(prt(str(a_rule)))
        else:
            pass # engine_logger.debug(prt(f"Invalid rule not loaded: {str(a_rule)}"))

    def get_all_rules(self):
        all_rules = []
        for each_key in self.orm_objects:
            table_rules = self.orm_objects[each_key]
            for each_rule in table_rules.rules:
               all_rules.append(each_rule)
        return all_rules

    def __str__(self):
        result = f"Rule Bank[{str(hex(id(self)))}] (loaded {self._at})"
        for each_key in self.orm_objects:
            result += f"\nMapped Class[{each_key}] rules:"
            table_rules = self.orm_objects[each_key]
            for each_rule in table_rules.rules:
                result += f'\n  {str(each_rule)}'
        return result


