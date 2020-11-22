import os
import sys
from datetime import datetime

import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

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

print("\nadd_cust, verified: " + str(verify_cust) + "\n\n")

from sqlalchemy.sql import func
qry = session.query(models.Order.CustomerId, func.sum(models.Order.AmountTotal))\
    .filter(models.Order.CustomerId == "ALFKI", models.Order.ShippedDate == None)
qry = qry.group_by(models.Order.CustomerId)
for _res in qry.all():
    print(_res)

print("\nadd_cust, completed: " + str(verify_cust) + "\n\n")

assert True
