import os
import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    os.environ['LOAD_BAD_RULES'] = 'True'
    unittest.main(module="examples.nw.tests.test_missing_attrs")  # logic loaded here
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        # set environment variable for deliberate logic loading failures
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)


    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        # first delete, so can add
        delete_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").delete()
        print("\nadd_cust, deleting: " + str(delete_cust) + "\n\n")
        session.commit()

        # Add a Customer - works
        new_cust = models.Customer(Id="$$New Cust", Balance=0, CreditLimit=0)
        session.add(new_cust)
        session.commit()

        verify_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").one()

        print("\nadd_cust, verified: " + str(verify_cust) + "\n\n")

        from sqlalchemy.sql import func
        qry = session.query(models.Order.CustomerId, func.sum(models.Order.AmountTotal))\
            .filter(models.Order.CustomerId == "ALFKI", models.Order.ShippedDate == None)
        qry = qry.group_by(models.Order.CustomerId)
        for _res in qry.all():
            print(_res)

        print("\nadd_cust, completed: " + str(verify_cust) + "\n\n")
        self.assertTrue(True)
