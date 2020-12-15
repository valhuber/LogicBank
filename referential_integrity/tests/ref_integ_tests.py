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
session.expunge(pre_parent)
pre_child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
pre_child_logic_row = LogicRow(row=pre_child, old_row=pre_child, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
session.expunge(pre_child)
list_ref_integ_rules = rule_bank_withdraw.rules_of_class(pre_child_logic_row, ParentCheck)
ref_integ_rule = list_ref_integ_rules[0]

"""
    Test 1 - create child row with invalid key, verify fails
"""

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
    assert did_fail_as_expected, "Ref Integ enabled, invalid FK did not raise ConstraintException"

print("\n" + prt("Invalid parent failed as expected.  Now trying update..."))


"""
    Test 2 - update child row with invalid key, verify fails
"""

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
    assert did_fail_as_expected, "Ref Integ enabled, invalid FK did not raise ConstraintException"

print("\n" + prt("Invalid parent failed as expected.  Now trying null..."))


print("\nref_integ_tests, update completed\n\n")


"""
    Test 3 - update child row with null key, verify ok
"""

child = session.query(models.Child).filter(models.Child.child_key == "c1.1").one()
child.parent_1 = None
session.commit()

print("\n" + prt("Null parent succeeded as expected."))

print("\nref_integ_tests, update completed\n\n")

print("\nref_integ_tests, ran to completion\n\n")
