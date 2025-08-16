import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_add_emp")
    exit(0)
else:  # failing to find rules
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    """
        Regression test - multi-relns between same 2 tables tests
    """

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        # failed 8/16/2025 since defaults are setting ReportsTo to 0 (which is invalid), so all_defaults=False
        new_employee = models.Employee(LastName='Obama', Salary=100000, WorksFor=1, OnLoan=2, IsCommissioned=0)  # project_id (fk, not id) triggers clone

        session.add(new_employee)
        session.commit()

        print("\nadd_employee, update completed\n\n")

        works_for = new_employee.Works_for_dept
        assert works_for.Name == "Sales", f'Expected Sales, got {works_for.Name}'
        assert works_for.SalaryTotal == 283000, f'Expected SalaryTotal 283000, got {works_for.SalaryTotal}'
        assert works_for.WorksForCount == 3, f'Expected WorksForCount == 3, got {works_for.WorksForCount}'

        on_loan = new_employee.On_loan_dept
        assert on_loan.OnLoanCount == 1, f'Expected OnLoanCount == 1, got {on_loan.OnLoanCount}'

        print("\n...add_emp, ran to completion\n\n")
