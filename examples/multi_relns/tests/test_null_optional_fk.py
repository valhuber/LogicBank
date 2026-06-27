import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_null_optional_fk")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    A SEPARATE bug from issue #20, found while building this suite (see
    system/LogicBank-Internal-Dev/multi-relationship-bug.md, "Status" section).

    Employee.on_loan_id is nullable=True (an employee may have no on-loan assignment).
    A null optional parent FK currently crashes the aggregate adjustor outright on
    insert/delete/update-in-place - getattr() on a None parent_logic_row.row. This is
    NOT specific to multi-relationship schemas - it reproduces with a single relationship
    too - but it was found here because this suite's seed data originally tried using
    on_loan_id=None for "not on loan to anyone" before working around it.

    NOTE: adjust_from_updated_reparented_child (aggregate.py:190-192) already has a
    DELIBERATE, DIFFERENT guard for a related-but-distinct case: reparenting TO a new
    parent that fails to resolve raises ConstraintException("Unable to Adjust Missing
    Adopting Parent") - that's a data-integrity error (FK points at something missing)
    and should keep raising. This file is about the FK being validly NULL (no parent
    expected at all), which should silently skip the adjustment, not raise.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_insert_employee_with_null_on_loan_id(self):
        """ Insert a new Employee with on_loan_id=None ("not currently on loan to anyone").
        Must not crash, and works_for side must still be correctly adjusted.
        """
        session = self.session
        new_employee = models.Employee(id=5, name='Eve', salary=2500, works_for_id=3, on_loan_id=None)
        session.add(new_employee)
        session.commit()  # must not raise

        dept_mkt = session.query(models.Department).filter(models.Department.id == 3).one()
        assert dept_mkt.works_for_count == 1, f'Expected Marketing works_for_count=1 (Eve), got {dept_mkt.works_for_count}'
        assert dept_mkt.works_for_salary_total == 2500, \
            f'Expected Marketing works_for_salary_total=2500 (Eve), got {dept_mkt.works_for_salary_total}'
        assert dept_mkt.on_loan_count == 0, f'Expected Marketing on_loan_count=0 (Eve has no on_loan), got {dept_mkt.on_loan_count}'

    def test_update_employee_to_null_on_loan_id(self):
        """ Update an existing Employee's on_loan_id from a real department to None
        ("recalled from loan, not reassigned"). The previous on_loan department must
        decrement; must not crash.
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        alice.on_loan_id = None  # was Engineering(2)
        session.commit()  # must not raise

        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        assert dept_eng.on_loan_count == 1, f'Expected Engineering on_loan_count=1 (Bob only, Alice recalled), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 2000, \
            f'Expected Engineering on_loan_salary_total=2000 (Bob only), got {dept_eng.on_loan_salary_total}'

    def test_delete_employee_with_null_on_loan_id(self):
        """ Delete an Employee whose on_loan_id is already None. Must not crash trying
        to adjust a non-existent on_loan parent.
        """
        session = self.session
        new_employee = models.Employee(id=6, name='Frank', salary=1800, works_for_id=3, on_loan_id=None)
        session.add(new_employee)
        session.commit()

        session.delete(new_employee)
        session.commit()  # must not raise

        dept_mkt = session.query(models.Department).filter(models.Department.id == 3).one()
        assert dept_mkt.works_for_count == 0, f'Expected Marketing works_for_count=0 (Frank deleted), got {dept_mkt.works_for_count}'
