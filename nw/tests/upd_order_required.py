from datetime import datetime

from sqlalchemy import inspect

import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from nw.tests import setup_db  # careful - this must follow fix-path, above
setup_db()

import nw.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.util import row_prt, prt
from nw.logic import session  # opens db, activates logic listener <--


""" toggle Due Date, to verify no effect on Customer, OrderDetails """
""" also test join.
session.query(Customer).join(Invoice).filter(Invoice.amount == 8500).all()
"""

pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
session.expunge(pre_cust)

print("")
test_order = session.query(models.Order).filter(models.Order.Id == 11011).join(models.Employee).one()
if test_order.RequiredDate is None or test_order.RequiredDate == "":
    test_order.RequiredDate = str(datetime.now())
    print(prt("Shipping order - RequiredDate: ['' -> " + test_order.RequiredDate + "]"))
else:
    test_order.RequiredDate = None
    print(prt("Returning order - RequiredDate: [ -> None]"))
insp = inspect(test_order)
session.commit()

print("")
post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
logic_row = LogicRow(row=pre_cust, old_row=post_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if abs(post_cust.Balance - pre_cust.Balance) == 0:
    logic_row.log("Correct non-adjusted Customer Result")
    assert True
else:
    row_prt(post_cust, "\nERROR - incorrect adjusted Customer Result")
    print("\n--> probable cause: Order customer update not written")
    row_prt(pre_cust, "\npre_alfki")
    assert False

print("\nupd_order_required, ran to completion")


