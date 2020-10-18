from datetime import datetime

from sqlalchemy import event, MetaData
from sqlalchemy.engine import Engine

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.exec_trans_logic.listeners import before_flush, before_commit
from logic_bank.rule_bank import rule_bank_withdraw
from sqlalchemy.orm import session


def setup(a_session: session, an_engine: Engine):
    """
    Initialize the RuleBank

    """
    rules_bank = RuleBank()
    rules_bank._session = a_session
    event.listen(a_session, "before_flush", before_flush)
    event.listen(a_session, "before_commit", before_commit)


    rules_bank.orm_objects = {}
    rules_bank._at = datetime.now()

    rules_bank._engine = an_engine
    rules_bank._metadata = MetaData(bind=an_engine, reflect=True)
    from sqlalchemy.ext.declarative import declarative_base
    rules_bank._base = declarative_base()

    return


def set_referring_children(rule, dependency: list):
    pass


def validate_formula_dependencies(class_name: str):
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


def validate(a_session: session, engine: Engine):
    """
    Determine formula execution order based on "row.xx" references,
    (or raise exception if cycles detected).
    """
    list_rules = "\n\nValidate Rule Bank"
    rules_bank = RuleBank()

    for each_key in rules_bank.orm_objects:
        validate_formula_dependencies(class_name=each_key)
    list_rules += rules_bank.__str__()
    print(list_rules)
    return True

