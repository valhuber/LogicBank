import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank*", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_update_employee_salary")
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

        """ Test State Transition Logic - raise over 20%

            should fail due to credit limit exceeded (catch exception to verify)
        """

        bad_employee_raise = self.session.query(models.Employee).filter(models.Employee.Id == 1).one()
        bad_employee_raise.Salary = bad_employee_raise.Salary * Decimal('1.1')

        did_fail_as_expected = False

        try:
            self.session.commit()
        except:
            self.session.rollback()
            did_fail_as_expected = True

        if not did_fail_as_expected:
            self.fail("too-small should have failed constraint, but succeeded")
        else:
            print("\n" + prt("puny raise failed constraint as expected."))

        print("\nupd_employee_salary, ran to completion")
        self.assertTrue(True)
