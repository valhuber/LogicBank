import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_upd_order_shipped_auto_commit")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        with engine.connect().execution_options(autocommit=True) as conn:
            self.toggle_order_shipped()
            print("\nupd_order_shipped_auto_commit, ran to completion")

    def toggle_order_shipped(self):
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
        # session.commit()

        print("")
        post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

        if abs(post_cust.Balance - pre_cust.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            assert True
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))


