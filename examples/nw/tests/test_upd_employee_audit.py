import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_upd_employee_audit")
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
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):

        """
        Test 1 - alter City, ensure no EmployeeAudit created
        """

        print("\n\nTest 1 - alter Salary, ensure no EmployeeAudit created\n")
        test_emp = session.query(models.Employee).filter(models.Employee.Id == 1).one()
        test_emp.City = "don't audit this"
        session.commit()

        test_emp_audit = session.query(models.EmployeeAudit).all()
        if test_emp_audit:
            self.fail("Failure - audit row created for just City change")

        """
        Test 2 - alter Salary, ensure EmployeeAudit created
        """

        print("\n\nTest 2 - alter Salary, ensure EmployeeAudit created (from NWRuleExtension.nw_copy_row)")
        test_emp = session.query(models.Employee).filter(models.Employee.Id == 1).one()
        test_emp.Salary = test_emp.Salary * Decimal(1.5)
        session.commit()

        print("")
        # test_emp_audit = session.query(models.EmployeeAudit).one()
        query = session.query(models.EmployeeAudit)
        print(f"  .. test_emp_audit - did query, count = {query.count()}")
        test_emp_audit = query.one()
        print(f"  .. test_emp_audit {test_emp_audit.LastName}")
        if test_emp_audit is None:
            self.fail("Failure - audit row not created on Salary change")
