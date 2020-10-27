"""
PyCharm sets PythonPath to the root folder, VSC does not by default - imports fail
Hence, add this to the launch config:
"env": {"PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"}

ref: https://stackoverflow.com/questions/53653083/how-to-correctly-set-pythonpath-for-visual-studio-code
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import inspect

cwd = os.getcwd()   # eg, /Users/val/python/pycharm/logic-bank/nw/tests
required_path_python_rules = cwd  # seeking /Users/val/python/pycharm/logic-bank
required_path_python_rules = required_path_python_rules.replace("/nw/tests", "")
required_path_python_rules = required_path_python_rules.replace("\\nw\\tests", "")
required_path_python_rules = required_path_python_rules.replace("\\\\", "\\")  # you cannot be serious

sys_path = ""
required_path_present = False
for each_node in sys.path:
    sys_path += each_node + "\n"
    if each_node == required_path_python_rules:
        required_path_present = True

if not required_path_present:
    print("Fixing path (so can run from terminal)")
    sys.path.append(required_path_python_rules)
else:
    pass
    print("NOT Fixing path (default PyCharm, set in VSC Launch Config)")

run_environment_info = "Run Environment info...\n\n"
run_environment_info += " Current Working Directory: " + cwd + "\n\n"
run_environment_info += "sys.path: (Python imports)\n" + sys_path + "\n"
run_environment_info += "From: " + sys.argv[0] + "\n\n"
run_environment_info += "Using Python: " + sys.version + "\n\n"
run_environment_info += "At: " + str(datetime.now()) + "\n\n"

print("\n" + run_environment_info + "\n\n")
from nw.tests import setup_db  # careful - this must follow fix-path, above
setup_db()

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
