import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_sum_count")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression tests for issue #20 (https://github.com/valhuber/LogicBank/issues/20):
    Rule.sum ignores child_role_name for 2+ relationships to the same parent class.

    Rule.count is the control - it was never affected, confirming this is a Sum-specific
    regression, not a structural problem with multi-relationship modeling itself.

    See system/LogicBank-Internal-Dev/multi-relationship-bug.md.

    IMPORTANT: every assertion below checks BOTH departments touched by a change - asserting
    on only one side is exactly how this bug went undetected in examples/nw's test_add_emp.py.

    Each test method gets its OWN fresh session/engine (see tests.new_session_from_gold) -
    this class has multiple DB-mutating methods, unlike examples/nw's one-method-per-file
    convention, so a module-level singleton session would leak state between methods.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_gold_seed_data_is_correct(self):
        """ Case 1 (baseline): gold seed data sums/counts are correct on both roles, both departments.

        Seed data: Alice(1000, works=Sales, on_loan=Eng), Bob(2000, works=Eng, on_loan=Eng),
                   Carol(1500, works=Sales, on_loan=Sales)
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_mkt = session.query(models.Department).filter(models.Department.id == 3).one()

        # Sales (id=1): Alice works_for=1, Carol works_for=1 AND on_loan=1
        assert dept_sales.works_for_count == 2, f'Expected Sales works_for_count=2, got {dept_sales.works_for_count}'
        assert dept_sales.works_for_salary_total == 2500, \
            f'Expected Sales works_for_salary_total=2500 (Alice 1000 + Carol 1500), got {dept_sales.works_for_salary_total}'
        assert dept_sales.on_loan_count == 1, f'Expected Sales on_loan_count=1 (Carol), got {dept_sales.on_loan_count}'
        assert dept_sales.on_loan_salary_total == 1500, \
            f'Expected Sales on_loan_salary_total=1500 (Carol), got {dept_sales.on_loan_salary_total}'

        # Engineering (id=2): Bob works_for=2 AND on_loan=2, Alice on_loan=2
        assert dept_eng.works_for_count == 1, f'Expected Engineering works_for_count=1 (Bob), got {dept_eng.works_for_count}'
        assert dept_eng.works_for_salary_total == 2000, \
            f'Expected Engineering works_for_salary_total=2000 (Bob), got {dept_eng.works_for_salary_total}'
        assert dept_eng.on_loan_count == 2, f'Expected Engineering on_loan_count=2 (Bob, Alice), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 3000, \
            f'Expected Engineering on_loan_salary_total=3000 (Bob 2000 + Alice 1000), got {dept_eng.on_loan_salary_total}'

        # Marketing (id=3): nobody
        assert dept_mkt.works_for_count == 0, f'Expected Marketing works_for_count=0, got {dept_mkt.works_for_count}'
        assert dept_mkt.on_loan_count == 0, f'Expected Marketing on_loan_count=0, got {dept_mkt.on_loan_count}'

        print("\n...test_gold_seed_data_is_correct ran to completion\n\n")

    def test_insert_employee_both_roles_different_departments(self):
        """ Case 1: insert a new Employee with works_for/on_loan pointing at DIFFERENT departments.
        Asserts on BOTH departments' Sum AND Count - this is the exact shape of the GitHub issue #20 repro.
        """
        session = self.session
        new_employee = models.Employee(id=4, name='Dave', salary=3000, works_for_id=2, on_loan_id=3)
        session.add(new_employee)
        session.commit()

        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_mkt = session.query(models.Department).filter(models.Department.id == 3).one()

        # Engineering gains a works_for employee (Dave) - Bob (2000) + Dave (3000) = 5000
        assert dept_eng.works_for_count == 2, f'Expected Engineering works_for_count=2, got {dept_eng.works_for_count}'
        assert dept_eng.works_for_salary_total == 5000, \
            f'Expected Engineering works_for_salary_total=5000, got {dept_eng.works_for_salary_total}'
        # Engineering's on_loan side is untouched by Dave (Dave is on_loan to Marketing, not Engineering)
        assert dept_eng.on_loan_count == 2, f'Expected Engineering on_loan_count=2 (Bob, Alice - unchanged), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 3000, \
            f'Expected Engineering on_loan_salary_total=3000 (Bob 2000 + Alice 1000 - unchanged), got {dept_eng.on_loan_salary_total}'

        # Marketing gains an on_loan employee (Dave) - its works_for side must remain 0
        assert dept_mkt.on_loan_count == 1, f'Expected Marketing on_loan_count=1 (Dave), got {dept_mkt.on_loan_count}'
        assert dept_mkt.on_loan_salary_total == 3000, \
            f'Expected Marketing on_loan_salary_total=3000 (Dave), got {dept_mkt.on_loan_salary_total}'
        assert dept_mkt.works_for_count == 0, \
            f'Expected Marketing works_for_count=0 (issue #20 would wrongly add Dave here too), got {dept_mkt.works_for_count}'
        assert dept_mkt.works_for_salary_total == 0, \
            f'Expected Marketing works_for_salary_total=0 (issue #20 would wrongly collapse Dave salary here), got {dept_mkt.works_for_salary_total}'

        print("\n...test_insert_employee_both_roles_different_departments ran to completion\n\n")

    def test_update_salary_does_not_cross_contaminate_roles(self):
        """ Case 1 variant: update Employee.salary where works_for/on_loan point at different departments;
        confirm the delta lands on the correct department for EACH role, not collapsed onto one.
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        alice.salary = 1100  # was 1000, +100
        session.commit()

        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()  # works_for
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()  # on_loan

        assert dept_sales.works_for_salary_total == 2600, \
            f'Expected Sales works_for_salary_total=2600 (2500 + 100), got {dept_sales.works_for_salary_total}'
        assert dept_eng.on_loan_salary_total == 3100, \
            f'Expected Engineering on_loan_salary_total=3100 (3000 + 100), got {dept_eng.on_loan_salary_total}'
        # cross-contamination check: the OTHER aggregate type on the SAME department should be untouched
        assert dept_sales.on_loan_salary_total == 1500, \
            f'Expected Sales on_loan_salary_total unchanged at 1500 (Carol only), got {dept_sales.on_loan_salary_total}'
        assert dept_eng.works_for_salary_total == 2000, \
            f'Expected Engineering works_for_salary_total unchanged at 2000 (Bob only), got {dept_eng.works_for_salary_total}'

        print("\n...test_update_salary_does_not_cross_contaminate_roles ran to completion\n\n")

    def test_same_department_both_roles(self):
        """ Edge case from gold seed data: Carol has works_for=Sales AND on_loan=Sales (same department,
        both roles). Confirms the two roles' aggregates on the SAME parent instance don't merge into one
        bucket or double/zero out.
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()

        assert dept_sales.works_for_count == 2, f'Expected works_for_count=2, got {dept_sales.works_for_count}'
        assert dept_sales.on_loan_count == 1, f'Expected on_loan_count=1, got {dept_sales.on_loan_count}'
        assert dept_sales.works_for_salary_total == 2500, f'Expected works_for_salary_total=2500, got {dept_sales.works_for_salary_total}'
        assert dept_sales.on_loan_salary_total == 1500, f'Expected on_loan_salary_total=1500, got {dept_sales.on_loan_salary_total}'

        print("\n...test_same_department_both_roles ran to completion\n\n")
