from decimal import Decimal
import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from logic_bank.rule_bank import rule_bank_withdraw  # TODO fails
from logic_bank.rule_type.parent_check import ParentCheck

print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from logic_bank.logic_bank import LogicBank
from logic_bank.util import row_prt, prt, ConstraintException
from logic_bank.exec_row_logic.logic_row import LogicRow

import examples.insert_parent.db.models as models
import traceback

def copy_db_from_gold():
    """ copy db/database-gold.db over db/database.db"""
    print("\n" + prt("restoring database-gold\n"))

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - create database.db from database-gold.db in " + basedir + "/payment_allocation/db/\n" +
          "            - from -- " + prt("") +
          "\n********************************")

    db_loc = os.path.join(basedir, "db/database.db")
    db_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=db_source, dst=db_loc)

def setup_logging():
    logic_logger = logging.getLogger('logic_logger')  # for debugging user logic
    logic_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    logic_logger.addHandler(handler)

    do_engine_logging = False
    engine_logger = logging.getLogger('engine_logger')  # for internals
    if do_engine_logging:
        engine_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
        handler.setFormatter(formatter)
        engine_logger.addHandler(handler)

setup_logging()
copy_db_from_gold()

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

db_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + db_loc
engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

from examples.insert_parent.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)

pre_parent = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "p1_1",
                                                 models.Parent.parent_attr_2 == "p1_2").one()
pre_parent_logic_row = LogicRow(row=pre_parent, old_row=pre_parent, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
children = pre_parent.ChildList
session.expunge(pre_parent)

pre_child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
pre_child_logic_row = LogicRow(row=pre_child, old_row=pre_child, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
session.expunge(pre_child)

list_ref_integ_rules = rule_bank_withdraw.rules_of_class(pre_child_logic_row, ParentCheck)
ref_integ_rule = list_ref_integ_rules[0]

test1 = False
test2 = False
test3 = False
test4 = False
test5 = False
test6 = False
test7 = False
test8 = True
test9 = True


"""
    Test 1 - Insert Parent from inserted child
"""
if test8:
    print("\nTest 1 - Insert Parent from inserted child")
    new_child = models.Child(parent_1="auto_inserted", parent_2="parent", summed = 2, child_key="new insert_parent child")

    session.add(new_child)
    did_succeed_as_expected = True
    try:
        session.commit()
    except ConstraintException as ce:
        reason = str(ce)
        print("Expected constraint caught: " + reason)
        session.rollback()
        if reason == "Missing Parent: Parent":
            did_fail_as_expected = True
        else:
            did_fail_as_expected = False
            print("But was expecting 'Missing Parent: Parent'")
    except Exception as e:
        traceback.print_exception(*sys.exc_info())
        session.rollback()
        did_succeed_as_expected = False
        # msg = sys.exc_info()[0]
        msg = e.args[0]
        print("\n\nUNEXPECTED constraint caught: " + str(msg))

    assert did_succeed_as_expected, "Test 8 failed: Insert Parent from inserted child"

    new_parent_check = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "auto_inserted" and \
                                                          models.Parent.parent_attr_2 == "parent").one()
    assert new_parent_check.child_sum == 2, "Unexpected child_sum"
    assert new_parent_check.child_count == 1, "Unexpected child_count"
    assert new_parent_check.defaulted_number== 1, "Unexpected defaulted_number"
    assert new_parent_check.defaulted_decimal == Decimal(1.50), "Unexpected defaulted_decimal"
    assert new_parent_check.defaulted_float == float(1.333), "Unexpected defaulted_float"
    # assert new_parent_check.defaulted_boolean == False, "Unexpected defaulted_boolean"

    
    print("\n" + prt("Test 1 - Insert Parent from inserted child -- passes"))
else:
    print("\nSKIPPED Test 1 insert child for missing parent")


"""
    Test 2 - Insert Parent From Adopted Child
"""
if test9:
    print("\nTest 2 - Insert Parent From Adopted Child")
    did_succeed_as_expected = True
    child = session.query(models.Child).filter(models.Child.child_key == "new insert_parent child").one()
    child.parent_1 = "auto_adopted"
    child.parent_2 = "parent"

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        did_succeed_as_expected = False
        e = sys.exc_info()[0]
        print("\nUNEXPECTED constraint caught: " + str(e))

    new_parent_check = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "auto_inserted" and \
                                                          models.Parent.parent_attr_2 == "parent").one()
    assert new_parent_check.child_sum == 0, "Unexpected child_sum"
    assert new_parent_check.child_count == 0, "Unexpected child_count"
    assert new_parent_check.defaulted_number== 1, "Unexpected defaulted_number"
    assert new_parent_check.defaulted_decimal == Decimal(1.50), "Unexpected defaulted_decimal"
    assert new_parent_check.defaulted_float == float(1.333), "Unexpected defaulted_float"

    adopted_parent_check = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "auto_adopted" and \
                                                          models.Parent.parent_attr_2 == "parent").one()
    assert adopted_parent_check.child_sum == 2, "Unexpected child_sum"
    assert adopted_parent_check.child_count == 1, "Unexpected child_count"
    assert adopted_parent_check.defaulted_number== 1, "Unexpected defaulted_number"
    assert adopted_parent_check.defaulted_decimal == Decimal(1.50), "Unexpected defaulted_decimal"
    assert adopted_parent_check.defaulted_float == float(1.333), "Unexpected defaulted_float"

    assert did_succeed_as_expected, "Test 2 - Insert Parent From Adopted Child -- FAILS"

    print("\n" + prt("Test 2 - Insert Parent From Adopted Child -- passes"))
else:
    print("\nSKIPPED Test 2 - Insert Parent From Adopted Child")


"""
    Test 3 - Insert Parent once for two new children of the same new parent, in one transaction
    (insert_parent used to create the parent once PER child: UNIQUE constraint failed on the parent key)
"""
print("\nTest 3 - Insert Parent once for two children inserted in one transaction")
did_succeed_as_expected = True
session.add_all([models.Child(parent_1="same_flush", parent_2="parent", summed=3, child_key="same flush child 1"),
                 models.Child(parent_1="same_flush", parent_2="parent", summed=4, child_key="same flush child 2")])
try:
    session.commit()
except Exception as e:
    traceback.print_exception(*sys.exc_info())
    session.rollback()
    did_succeed_as_expected = False
    print("\nUNEXPECTED exception: " + str(e))
assert did_succeed_as_expected, "Test 3 - Insert Parent once for two children in one transaction -- FAILS"

same_flush_parents = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "same_flush",
                                                         models.Parent.parent_attr_2 == "parent").all()
assert len(same_flush_parents) == 1, f"Expected 1 parent, got {len(same_flush_parents)}"
assert same_flush_parents[0].child_count == 2, f"Unexpected child_count: {same_flush_parents[0].child_count}"
assert same_flush_parents[0].child_sum == 7, f"Unexpected child_sum: {same_flush_parents[0].child_sum}"
print("\n" + prt("Test 3 - Insert Parent once for two children in one transaction -- passes"))


"""
    Test 4 - Insert Parent for an adopted child when no parent_check rule is declared
    (the update path created a missing parent only inside parent_check; without it, reparenting a child to a
    missing parent raised "Unable to Adjust Missing Adopting Parent")
"""
print("\nTest 4 - Insert Parent From Adopted Child, without parent_check")
ref_integ_rule._enable = False
did_succeed_as_expected = True
child = session.query(models.Child).filter(models.Child.child_key == "same flush child 1").one()
child.parent_1 = "adopted_no_check"
try:
    session.commit()
except Exception as e:
    traceback.print_exception(*sys.exc_info())
    session.rollback()
    did_succeed_as_expected = False
    print("\nUNEXPECTED exception: " + str(e))
finally:
    ref_integ_rule._enable = True
assert did_succeed_as_expected, "Test 4 - Insert Parent From Adopted Child, without parent_check -- FAILS"

adopted = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "adopted_no_check",
                                              models.Parent.parent_attr_2 == "parent").all()
assert len(adopted) == 1, f"Expected 1 adopting parent, got {len(adopted)}"
assert adopted[0].child_count == 1 and adopted[0].child_sum == 3, \
    f"Unexpected adopting parent: count {adopted[0].child_count}, sum {adopted[0].child_sum}"
previous = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "same_flush",
                                               models.Parent.parent_attr_2 == "parent").one()
assert previous.child_count == 1 and previous.child_sum == 4, \
    f"Unexpected previous parent: count {previous.child_count}, sum {previous.child_sum}"
print("\n" + prt("Test 4 - Insert Parent From Adopted Child, without parent_check -- passes"))
