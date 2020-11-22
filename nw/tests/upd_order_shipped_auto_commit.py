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
from nw.logic import session, engine  # opens db, activates logic listener <--


def toggle_order_shipped():
    """ toggle Shipped Date, to trigger balance adjustment """
    """ also test join.
    session.query(Customer).join(Invoice).filter(Invoice.amount == 8500).all()
    """

    pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
    session.expunge(pre_cust)

    print("")
    test_order = session.query(models.Order).filter(models.Order.Id == 11011).join(models.Employee).one()
    if test_order.ShippedDate is None or test_order.ShippedDate == "":
        # with restored db, cust[ALFKI] has bal 960 & 3 unpaid orders, Order[11011) is 960, unshipped
        test_order.ShippedDate = str(datetime.now())
        print(prt("Shipping order - ShippedDate: ['' -> " + test_order.ShippedDate + "]" +
                  " for customer balance: " + str(pre_cust.Balance) +
                  ", with UnpaidOrderCount: " + str(pre_cust.UnpaidOrderCount)))
    else:
        test_order.ShippedDate = None
        print(prt("Returning order - ShippedDate: [ -> None]"))
    insp = inspect(test_order)
    # session.commit()

    print("")
    post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
    logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

    if abs(post_cust.Balance - pre_cust.Balance) == 960:
        logic_row.log("Correct adjusted Customer Result")
        assert True
    else:
        row_prt(post_cust, "\nERROR - incorrect adjusted Customer Result")
        print("\n--> probable cause: Order customer update not written")
        row_prt(pre_cust, "\npre_alfki")
        assert False

with engine.connect().execution_options(autocommit=True) as conn:
    toggle_order_shipped()
    print("\nupd_order_shipped_auto_commit, ran to completion")

