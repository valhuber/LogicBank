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
    from logic_bank.exceptions import LBActivateException

    session = None
    engine = None
    activate_exception = None
    try:
        from examples.nw.logic import session, engine  # opens db, activates rules <--
        # activate rules:   LogicBank.activate(session=session, activator=declare_logic)
    except LBActivateException as ex:
        activate_exception = ex
        print(f'\nExpected LBActivateException: {ex.message}\n')

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        # set environment variable for deliberate logic loading failures
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)


    def tearDown(self):
        if session is not None:
            tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)
        else:
            print("\n**********************")
            print("** Test complete (no session - LBActivateException expected) for: " + __file__)
            print("** Started: " + self.started_at + " Ended: " + str(datetime.now()))
            print("**********************")

    def test_run(self):
        if activate_exception is not None:
            # Verify the expected LBActivateException was raised for bad rules
            assert len(activate_exception.invalid_rules) > 0 or len(activate_exception.missing_attributes) > 0, \
                "LBActivateException raised but no invalid_rules or missing_attributes"
            print(f'\nmissing_attrs, LBActivateException raised as expected: {activate_exception.message}\n')
            return

        # Normal path (run_tests.py without LOAD_BAD_RULES): verify session works
        delete_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").delete()
        print("\nadd_cust, deleting: " + str(delete_cust) + "\n\n")
        session.commit()

        new_cust = models.Customer(Id="$$New Cust", Balance=0, CreditLimit=0)
        session.add(new_cust)
        session.commit()

        verify_cust = session.query(models.Customer).filter(models.Customer.Id == "$$New Cust").one()
        print("\nadd_cust, completed: " + str(verify_cust) + "\n\n")
        self.assertTrue(True)
