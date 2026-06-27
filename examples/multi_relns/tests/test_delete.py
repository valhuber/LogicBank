import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_delete")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Delete is a separate code path from insert/update - Aggregate.adjust_from_deleted_child
    (logic_bank/rule_type/aggregate.py) has its own do_not_adjust_list parameter and is not
    assumed-covered by the insert/update tests in test_sum_count.py. Test plan case 6 from
    system/LogicBank-Internal-Dev/multi-relationship-bug.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_delete_employee_decrements_correct_role_only(self):
        """ Delete Carol (works_for=Sales, on_loan=Sales - both roles point at the SAME department).
        Both Sales buckets must decrement correctly and independently; Engineering (untouched by
        this delete) must remain exactly as it was.
        """
        session = self.session
        carol = session.query(models.Employee).filter(models.Employee.id == 3).one()
        session.delete(carol)
        session.commit()

        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()

        # Sales loses Carol from BOTH roles (works_for: 2/2500 -> 1/1000 [Alice]; on_loan: 1/1500 -> 0/0)
        assert dept_sales.works_for_count == 1, f'Expected Sales works_for_count=1 (Alice only), got {dept_sales.works_for_count}'
        assert dept_sales.works_for_salary_total == 1000, \
            f'Expected Sales works_for_salary_total=1000 (Alice only), got {dept_sales.works_for_salary_total}'
        assert dept_sales.on_loan_count == 0, f'Expected Sales on_loan_count=0 (Carol was the only one), got {dept_sales.on_loan_count}'
        assert dept_sales.on_loan_salary_total == 0, \
            f'Expected Sales on_loan_salary_total=0, got {dept_sales.on_loan_salary_total}'

        # Engineering (Bob + Alice, untouched by Carol's delete) must be unchanged
        assert dept_eng.works_for_count == 1, f'Expected Engineering works_for_count=1 (unchanged), got {dept_eng.works_for_count}'
        assert dept_eng.works_for_salary_total == 2000, \
            f'Expected Engineering works_for_salary_total=2000 (unchanged), got {dept_eng.works_for_salary_total}'
        assert dept_eng.on_loan_count == 2, f'Expected Engineering on_loan_count=2 (unchanged), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 3000, \
            f'Expected Engineering on_loan_salary_total=3000 (unchanged), got {dept_eng.on_loan_salary_total}'
