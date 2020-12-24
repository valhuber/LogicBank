import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_upd_employee_audit")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import nw.tests as tests  # careful - this must follow add_python_path, above

    tests.copy_gold_over_db()

    import nw.db.models as models
    from nw.logic import session, engine  # opens db, activates rules <--

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt, row_prt, ConstraintException

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):

        """
        Test 1 - alter Salary, ensure EmployeeAudit created
        """

        test_emp = session.query(models.Employee).filter(models.Employee.Id == 1).one()
        test_emp.Salary = test_emp.Salary * Decimal(1.5)
        session.commit()

        print("")
        test_emp_audit = session.query(models.EmployeeAudit).one()
        if test_emp_audit is None:
            self.fail("Failure - audit row not created")
