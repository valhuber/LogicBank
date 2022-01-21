import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

# import sa as sa
import sqlalchemy
from sqlalchemy.orm import joinedload
from sqlalchemy import event

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_upd_order_security")
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
        self.toggle_order_shipped()
        print("\nupd_order_shipped, ran to completion")
        self.assertTrue(True)

    def toggle_order_shipped(self):
        """
            toggle Shipped Date, to trigger
                * balance adjustment
                * cascade to OrderDetails
                * and Product adjustment
            also test join
        """

        # fails on post_cust with TypeError: my_load_listener() got an unexpected keyword argument 'attrs'
        # @sqlalchemy.event.listens_for(sqlalchemy.orm.Mapper, 'refresh', named=True)
        def my_load_listener(target, context):
            print("on load!")

        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()
        print(f'type(Base): {type(Base)}')  # sqlalchemy.ext.declarative.api.DeclarativeMeta
        do_listen = False
        if do_listen:
            event.listen(sqlalchemy.ext.declarative.api.DeclarativeMeta,  # models.Customer is fine
                         'load', my_load_listener)
                          # , propagate=True)  # TypeError: descriptor '__subclasses__' of 'type' object needs an argument

        pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        supers = pre_cust.__class__.__bases__
        for each_super in supers:
            print(f'pre_cust super: {type(each_super)}')
        session.expunge(pre_cust)

        print("")
        test_order = session.query(models.Order).filter(models.Order.Id == 11011).\
            join(models.Employee).options(joinedload(models.Order.SalesRep)).\
            one()
        if test_order.ShippedDate is None or test_order.ShippedDate == "":
            test_order.ShippedDate = str(datetime.now())
            print(prt("Shipping order - ShippedDate: ['' -> " + test_order.ShippedDate + "]"))
        else:
            test_order.ShippedDate = None
            print(prt("Returning order - ShippedDate: [ -> None]"))
        session.commit()

        print("")
        post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

        if abs(post_cust.Balance - pre_cust.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            assert True
        else:
            self.fail(logic_row.log("ERROR - incorrect adjusted Customer Result (not 960 delta)"))

        if post_cust.Balance == 56:
            pass
        else:
            self.fail(logic_row.log("ERROR - balance should be 56"))

        if post_cust.UnpaidOrderCount == 3 and pre_cust.UnpaidOrderCount == 4:
            pass
        else:
            self.fail(logic_row.log("Error - UnpaidOrderCount should be 3"))


