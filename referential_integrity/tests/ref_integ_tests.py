import sys

import logic_bank_utils.util as logic_bank_utils

from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_type.parent_check import ParentCheck

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from referential_integrity.tests import restore_db_from_gold  # careful - this must follow fix-path, above
restore_db_from_gold()

import referential_integrity.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.util import row_prt, prt, ConstraintException
from referential_integrity.logic import session  # opens db, activates logic listener <--

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

"""
    Test 1 - insert child row with invalid key, verify fails
"""
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


"""
    Test 2 - update child row with invalid key, verify fails
"""
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


"""
    Test 3 - update child row with null key, verify ok
"""
print("\nBegin Test 3 - update child row with null key, verify ok")

child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
child.parent_1 = None
session.commit()

print("\n" + prt("Null parent succeeded as expected."))

print("\nref_integ_tests, update completed\n\n")


"""
    Test 4 - update child row with new valid parent, verify ok
"""
test4 = True
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


"""
    Test 6 - delete parent row - cascade delete
"""
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


"""
    Test 7 - delete parent row - cascade nullify
"""
print("\nBegin Test 7 - delete parent row - cascade nullify")

children_orphan = session.query(models.ChildOrphan).filter(models.ChildOrphan.child_key == "c2.2").all()

assert len(children_orphan) > 0, "Cascade Nullify Failed"  # failing, pending Logic Bank RI support

print("\n" + prt("Cascade nullify succeeded as expected."))

print("\nref_integ_tests, update completed\n\n")

print("\nref_integ_tests, ran to completion\n\n")
