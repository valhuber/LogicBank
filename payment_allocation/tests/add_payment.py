from decimal import Decimal

import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")


from payment_allocation.tests import setup_db  # careful - this must follow fix-path, above
setup_db()

import sqlalchemy_utils

import payment_allocation.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.util import row_prt, prt
from payment_allocation.logic import session  # opens db, activates logic listener <--

cls = sqlalchemy_utils.functions.get_class_by_table(models.Base, "Product", data=None)  # FIXME ??

# Add Order - works
pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
session.expunge(pre_cust)


"""
    Test 1 - create allocation row
"""

cust_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

new_payment = models.Payment(Amount=1000)
cust_alfki.PaymentList.append(new_payment)

session.add(new_payment)
session.commit()

post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

print("\nadd_payment, update completed\n\n")
row_prt(new_payment, "\nnew Payment Result")  #
if new_payment.Amount != Decimal(1000):
    print ("==> ERROR - unexpected new_payment.Amount: " + str(new_payment.Amount) +
           "... expected 1000")
else:
    print()

"""
    (10653 owes nothing)
    orderId OrderDate   AmountTotal AmountPaid  AmountOwed  ==> Allocated
    10692   2013-10-03  878         778         100         100
    10702   2013-10-03  330         0           330         330
    10835   2014-01-15  851         0           851         570
    10952   2014-03-16  491.20      0           491.20      *
    11011   2014-04-09  960         0           960         *
"""

logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
if post_cust.Balance == pre_cust.Balance - 1000:  # 1016 -> 16  ?? 794
    logic_row.log("Correct adjusted Customer Result")
    assert True
else:
    logic_row.log("ERROR - incorrect adjusted Customer Result")
    assert False
print("\nadd_payment, ran to completion\n\n")
