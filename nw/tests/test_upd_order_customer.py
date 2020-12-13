import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank*", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_upd_order_customer")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import nw.tests as tests  # careful - this must follow add_python_path, above

    import nw.db.models as models

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt, row_prt, ConstraintException

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(test=self, file=__file__)
        pass

    def tearDown(self):
        tests.tearDown(test=self, file=__file__)

    def test_run(self):
        from nw.db import db_session
        pre_alfki = db_session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        pre_anatr = db_session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
        db_session.expunge(pre_alfki)
        db_session.expunge(pre_anatr)

        if pre_alfki.Balance != 1016:
            self.fail("pre_alfki balance not 1016 (database-gold not copied?), value: " + str(pre_alfki.Balance))

        print("")
        test_order = db_session.query(models.Order).filter(models.Order.Id == 11011).one()  # type : Order
        amount_total = test_order.AmountTotal
        if test_order.CustomerId  == "ALFKI":
            test_order.CustomerId = "ANATR"
        else:
            test_order.CustomerId = "ALFKI"
        print(prt("Reparenting order - new CustomerId: " + test_order.CustomerId))
        db_session.commit()

        print("")
        post_alfki = db_session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_alfki, old_row=pre_alfki, ins_upd_dlt="*", nest_level=0, a_session=db_session, row_sets=None)

        if abs(post_alfki.Balance - pre_alfki.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            pass
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))

        post_anatr = db_session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
        logic_row = LogicRow(row=post_anatr, old_row=pre_anatr, ins_upd_dlt="*", nest_level=0, a_session=db_session, row_sets=None)

        if abs(post_anatr.Balance - pre_anatr.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            pass
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))

        print("\nupd_order_customer, ran to completion")
        self.assertTrue(True)


