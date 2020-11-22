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


""" toggle order's customer to ANATR, to verify no effect on Customer, OrderDetails """

pre_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
pre_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
session.expunge(pre_alfki)
session.expunge(pre_anatr)

print("")
test_order = session.query(models.Order).filter(models.Order.Id == 11011).one()  # type : Order
amount_total = test_order.AmountTotal
if test_order.CustomerId  == "ALFKI":
    test_order.CustomerId = "ANATR"
else:
    test_order.CustomerId = "ALFKI"
print(prt("Reparenting order - new CustomerId: " + test_order.CustomerId))
insp = inspect(test_order)
session.commit()

print("")
post_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
logic_row = LogicRow(row=post_alfki, old_row=pre_alfki, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if abs(post_alfki.Balance - pre_alfki.Balance) == 960:
    logic_row.log("Correct non-adjusted Customer Result")
    assert True
else:
    row_prt(post_alfki, "\nERROR - incorrect adjusted Customer Result")
    print("\n--> probable cause: Order customer update not written")
    row_prt(pre_alfki, "\npre_alfki")
    assert False

post_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
logic_row = LogicRow(row=post_anatr, old_row=pre_anatr, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if abs(post_anatr.Balance - pre_anatr.Balance) == 960:
    logic_row.log("Correct non-adjusted Customer Result")
    assert True
else:
    row_prt(post_anatr, "\nERROR - incorrect adjusted Customer Result")
    print("\n--> probable cause: Order customer update not written")
    row_prt(pre_anatr, "\npre_anatr")
    assert False

print("\nupd_order_customer, ran to completion")


