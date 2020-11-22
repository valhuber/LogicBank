from decimal import Decimal

import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

import nw.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.util import row_prt, prt
from nw.logic import session  # opens db, activates logic listener <--


""" Test State Transition Logic - raise over 20% """


"""
    Test 1 - should fail due to credit limit exceeded
"""

bad_employee_raise = session.query(models.Employee).filter(models.Employee.Id == 1).one()
bad_employee_raise.Salary = bad_employee_raise.Salary * Decimal('1.1')

did_fail_as_expected = False

try:
    session.commit()
except:
    session.rollback()
    did_fail_as_expected = True

if not did_fail_as_expected:
    raise Exception("too-small should have failed, but succeeded")
else:
    print("\n" + prt("puny raise failed constraint as expected."))

print("\nupd_employee_salary, ran to completion")
