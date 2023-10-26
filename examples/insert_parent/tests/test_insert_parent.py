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


"""
    Test 1 - insert child row with invalid key, verify fails
"""
if test1:
    print("\nBegin Test 1 - insert child row with invalid key, verify fails")
    new_child = models.Child(parent_1="xx", parent_2="yy", child_key="new child")

    session.add(new_child)
    did_fail_as_expected = False
    try:
        session.commit()
    except ConstraintException as ce:
        session.rollback()
        assert ref_integ_rule._enable, "Ref Integ disabled, but raised"
        did_fail_as_expected = True
        print("Expected constraint caught: " + str(ce))
    except:
        session.rollback()
        did_fail_as_expected = False
        e = sys.exc_info()[0]
        print(e)

    if ref_integ_rule._enable:
        assert did_fail_as_expected, "Test 1 failed: Ref Integ enabled, invalid FK did not raise ConstraintException"

    print("\n" + prt("Invalid parent failed as expected.  Now trying update..."))
else:
    print("\nSKIPPED Test 1 Invalid parent failed as expected.  Now trying update....")


"""
    Test 2 - update child row with invalid key, verify fails
"""
if test2:
    print("\nBegin Test 2 - update child row with invalid key, verify fails")
    child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
    child.parent_1 = "Make Me Fail"
    did_fail_as_expected = False
    try:
        session.commit()
    except ConstraintException as ce:
        session.rollback()
        assert ref_integ_rule._enable, "Ref Integ disabled, but raised"
        did_fail_as_expected = True
        print("Expected constraint caught: " + str(ce))
    except:
        session.rollback()
        did_fail_as_expected = False
        e = sys.exc_info()[0]
        print(e)

    if ref_integ_rule._enable:
        assert did_fail_as_expected, "Test 2 failed: Ref Integ enabled, invalid FK did not raise ConstraintException"

    print("\n" + prt("Invalid parent failed as expected.  Now trying null..."))


    print("\nref_integ_tests, update completed\n\n")
else:
    print("\nSKIPPED Test 2 - ef_integ_tests, update complete.")


"""
    Test 3 - update child row with null key, verify ok
"""
if test3:
    print("\nBegin Test 3 - update child row with null key, verify ok")

    child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
    child.parent_1 = None
    session.commit()

    print("\n" + prt("Null parent succeeded as expected."))

    print("\nref_integ_tests, update completed\n\n")
else:
    print("\nSKIPPED Test 3 - Null parent succeeded as expected.")


"""
    Test 4 - update child row with new valid parent, verify ok
"""
if test4:
    print("\nBegin Test 4 - update child row with new valid parent, verify ok")
    child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
    child.parent_1 = "p2_1"
    child.parent_2 = "p2_2"

    child.parent_1 = "p1_1"
    child.parent_2 = "p1_2"

    session.commit()

    print("\n" + prt("Null parent succeeded as expected."))

    print("\nref_integ_tests, update completed\n\n")
else:
    print("\nSKIPPED Test 4 - update child row with new valid parent, verify ok")


"""
    Test 5 - update parent pk, verify cascade update
"""
if test5:
    print("\nBegin Test 5 - update parent pk, verify cascade update")
    parent = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "p1_1",
                                                 models.Parent.parent_attr_2 == "p1_2").one()
    parent.parent_attr_1 = "new"
    parent.parent_attr_2 = "parent"
    session.commit()  # hmm.. even with cascade all, children orphaned (!!)
    print(str(parent))

    child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()

    assert child.parent_1 == "new", "Cascade Update Failed"  # failing, pending Logic Bank RI support

    print("\n" + prt("parent pk updated... cascade update worked"))

    print("\nref_integ_tests, update completed\n\n")
else:
    print("\nSKIPPED Test 5 - update parent pk, verify cascade update")


"""
    Test 6 - delete parent row - cascade delete
"""
if test6:
    print("\nBegin Test 6 - delete parent row - cascade delete")
    parent = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "p2_1",
                                                 models.Parent.parent_attr_2 == "p2_2").one()
    session.delete(parent)  # TODO - doc mass deletes don't work (query.delete())
    session.commit()  # even with cascade all, children orphaned (!!!)
    print(str(parent))

    children = session.query(models.Child).filter(models.Child.child_key == "c2.2").all()

    assert len(children)== 0, "Cascade Delete Failed"  # failing, pending Logic Bank RI support

    print("\n" + prt("Cascade delete succeeded as expected."))

    print("\nref_integ_tests, update completed\n\n")
else:
    print("\nSKIPPED Test 6 - delete parent row - cascade delete")

"""
    Test 7 - delete parent row - cascade nullify
"""
if test7:
    print("\nBegin Test 7 - delete parent row - cascade nullify")

    children_orphan = session.query(models.ChildOrphan).filter(models.ChildOrphan.child_key == "c2.2").all()

    assert len(children_orphan) > 0, "Cascade Nullify Failed"  # failing, pending Logic Bank RI support

    print("\n" + prt("Cascade nullify succeeded as expected."))

    print("\nref_integ_tests, update completed\n\n")

    print("\nref_integ_tests, ran to completion\n\n")
else:
    print("\nSKIPPED Test 7 - delete parent row - cascade nullify")


"""
    Test 8 - Insert Parent
"""
if test8:
    print("\nTest 8 - Insert Parent")
    new_child = models.Child(parent_1="auto_inserted", parent_2="parent", summed = 2, child_key="new parent_ins child")

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
        session.rollback()
        did_succeed_as_expected = False
        e = sys.exc_info()[0]
        print("UNEXPECTED constraint caught: " + str(e))


    assert did_succeed_as_expected, "Test 8 failed: Insert Parent"

    print("\n" + prt("Test 8 - Insert Parent -- passes"))
else:
    print("\nSKIPPED Test 8 insert child for missing parent")
