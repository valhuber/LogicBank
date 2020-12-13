import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank*", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_dlt_order")
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
        self.toggle_order_shipped()
        pre_adjusted_product = db_session.query(models.Product).filter(models.Product.Id == 58).one()
        db_session.expunge(pre_adjusted_product)
        print("\ndlt_order, shipped... now delete")
        delete_cust = db_session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        db_session.delete(delete_cust)
        db_session.commit()

        post_adjusted_product = db_session.query(models.Product).filter(models.Product.Id == 58).one()
        logic_row = LogicRow(row=post_adjusted_product, old_row=pre_adjusted_product, ins_upd_dlt="*", nest_level=0,
                             a_session=db_session, row_sets=None)
        if post_adjusted_product.UnitsShipped == pre_adjusted_product.UnitsShipped - 40:
            logic_row.log("Product adjusted properly on delete customer")
        else:
            logic_row.log("Product adjusted improperly on delete customer")
            assert False

        print("\ndlt_order, shipped... deleted - check log")
        self.assertTrue(True)

    def toggle_order_shipped(self):
        """ toggle Shipped Date, to trigger balance adjustment """
        from nw.db import db_session

        pre_cust = db_session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        pre_adjusted_product = db_session.query(models.Product).filter(models.Product.Id == 58).one()
        db_session.expunge(pre_cust)
        db_session.expunge(pre_adjusted_product)

        print("")
        test_order = db_session.query(models.Order).filter(models.Order.Id == 11011).join(models.Employee).one()
        if test_order.ShippedDate is None or test_order.ShippedDate == "":
            test_order.ShippedDate = str(datetime.now())
            print(prt("Shipping order - ShippedDate: ['' -> " + test_order.ShippedDate + "]"))
        else:
            test_order.ShippedDate = None
            print(prt("Returning order - ShippedDate: [ -> None]"))
        db_session.commit()

        print("")
        post_cust = db_session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=db_session, row_sets=None)

        if abs(post_cust.Balance - pre_cust.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            assert True
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))

        if post_cust.Balance == 56:
            pass
        else:
            self.fail(logic_row.log("ERROR - balance should be 56"))

        if post_cust.UnpaidOrderCount == 3 and pre_cust.UnpaidOrderCount == 4:
            pass
        else:
            self.fail(logic_row.log("Error - UnpaidOrderCount should be 2"))

        post_adjusted_product = db_session.query(models.Product).filter(models.Product.Id == 58).one()
        logic_row = LogicRow(row=post_adjusted_product, old_row=pre_adjusted_product, ins_upd_dlt="*", nest_level=0,
                             a_session=db_session, row_sets=None)
        if post_adjusted_product.UnitsShipped == pre_adjusted_product.UnitsShipped + 40:
            logic_row.log("Product adjusted properly on ship order")
        else:
            self.fail(logic_row.log("Product adjusted improperly on ship order"))



