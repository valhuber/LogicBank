import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_upd_orderclass_required")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import nw.tests as tests  # careful - this must follow add_python_path, above

    tests.copy_gold_over_db()

    import nw.db.models as models
    from nw.logic import session, engine  # opens db, activates rules <--

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt, row_prt
    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):

        """ test class <> table name """

        pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        session.expunge(pre_cust)

        print("")
        test_order = session.query(models.OrderClass).filter(models.OrderClass.Id == 11011).join(models.Employee).one()
        if test_order.RequiredDate is None or test_order.RequiredDate == "":
            test_order.RequiredDate = str(datetime.now())
            print(prt("Shipping order - RequiredDate: ['' -> " + test_order.RequiredDate + "]"))
        else:
            test_order.RequiredDate = None
            print(prt("Returning order - RequiredDate: [ -> None]"))
        session.commit()

        print("")
        post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=pre_cust, old_row=post_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

        # logic_row.row.Balance = 10  # force failure
        if abs(post_cust.Balance - pre_cust.Balance) == 0:
            logic_row.log("Correct non-adjusted Customer Result")
            assert True
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected no difference"))

        print("\nupd_order_required, ran to completion")


