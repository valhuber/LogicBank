import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_update_employee_salary")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    from logic_bank.util import prt

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):

        """ Test State Transition Logic - raise over 20%

            should fail due to credit limit exceeded (catch exception to verify)
        """

        bad_employee_raise = session.query(models.Employee).filter(models.Employee.Id == 1).one()
        bad_employee_raise.Salary = bad_employee_raise.Salary * Decimal('1.1')

        did_fail_as_expected = False

        try:
            session.commit()
        except:
            session.rollback()
            did_fail_as_expected = True

        if not did_fail_as_expected:
            self.fail("too-small should have failed constraint, but succeeded")
        else:
            print("\n" + prt("puny raise failed constraint as expected."))

        print("\nupd_employee_salary, ran to completion")
        self.assertTrue(True)
