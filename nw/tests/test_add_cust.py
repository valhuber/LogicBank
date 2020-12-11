import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank*", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_add_cust")
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
        self.session = None
        self.engine = None

        tests.setUp(test=self, file=__file__)
        pass

    def tearDown(self):
        tests.tearDown(test=self, file=__file__)

    def test_run(self):
        # first delete, so can add
        delete_cust = self.session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").delete()
        print("\nadd_cust, deleting: " + str(delete_cust) + "\n\n")
        self.session.commit()

        # Add a Customer - works
        new_cust = models.Customer(Id="$$New Cust", Balance=0, CreditLimit=0)
        self.session.add(new_cust)
        self.session.commit()

        verify_cust = self.session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").one()

        print("\nadd_cust, verified: " + str(verify_cust) + "\n\n")

        from sqlalchemy.sql import func
        qry = self.session.query(models.Order.CustomerId, func.sum(models.Order.AmountTotal))\
            .filter(models.Order.CustomerId == "ALFKI", models.Order.ShippedDate == None)
        qry = qry.group_by(models.Order.CustomerId)
        for _res in qry.all():
            print(_res)

        print("\nadd_cust, completed: " + str(verify_cust) + "\n\n")
        self.assertTrue(True)
