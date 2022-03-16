import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_dlt_order")
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

        pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        session.expunge(pre_cust)

        pre_adjusted_product = session.query(models.Product).filter(models.Product.Id == 58).one()
        session.expunge(pre_adjusted_product)

        print("\nNow delete the Order...")
        delete_order = session.query(models.Order).filter(models.Order.Id == 10643).one()
        session.delete(delete_order)
        session.commit()

        post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0,
                             a_session=session, row_sets=None)
        if (pre_cust.Balance) == post_cust.Balance:
            logic_row.log(f'Customer not adjusted properly on delete shipped order')
        else:
            msg = f'Customer adjusted improperly on delete order: {pre_cust.Balance} -> {post_cust.Balance}'
            logic_row.log(msg)
            assert False, msg
        post_adjusted_product = session.query(models.Product).filter(models.Product.Id == 58).one()
        logic_row = LogicRow(row=post_adjusted_product, old_row=pre_adjusted_product, ins_upd_dlt="*", nest_level=0,
                             a_session=session, row_sets=None)
        if post_adjusted_product.UnitsShipped == pre_adjusted_product.UnitsShipped:
            logic_row.log("Product *not* adjusted properly on delete order")
        else:
            logic_row.log("Product adjusted improperly on delete order")
            assert False, "Product adjusted improperly on delete order"

        print("\nOrder deleted - check log")
        self.assertTrue(True)
