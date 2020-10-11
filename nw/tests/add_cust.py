import os
import sys
from datetime import datetime

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
from nw.logic import session  # opens db, activates logic listener <--


# first delete, so can add
delete_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").delete()
print("\nadd_cust, deleting: " + str(delete_cust) + "\n\n")
session.commit()

# Add a Customer - works
new_cust = models.Customer(Id="$$New Cust", Balance=0, CreditLimit=0)
session.add(new_cust)
session.commit()

verify_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").one()

print("\nadd_cust, completed: " + str(verify_cust) + "\n\n")

assert True
