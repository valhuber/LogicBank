import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_reparent")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Reparenting (role-changing update) - Aggregate.adjust_from_updated_reparented_child
    (logic_bank/rule_type/aggregate.py) adjusts TWO parent rows in one go: the new parent
    gaining the child, and the previous parent losing it. Test plan case 4 from
    system/LogicBank-Internal-Dev/multi-relationship-bug.md.

    Every assertion checks ALL departments touched, including the untouched other-role
    parent, per the "assert on all sides" rule established earlier in that doc.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_reparent_same_role_different_parent(self):
        """ Move Alice's works_for from Sales(1) to Marketing(3) - same role, different parent instance.
        Sales must lose Alice's contribution, Marketing must gain it, and Alice's UNCHANGED on_loan
        role (Engineering) must be untouched throughout.
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        alice.works_for_id = 3  # Sales -> Marketing
        session.commit()

        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_mkt = session.query(models.Department).filter(models.Department.id == 3).one()

        # Sales loses Alice (was works_for_count=2/2500, now just Carol: 1/1500)
        assert dept_sales.works_for_count == 1, f'Expected Sales works_for_count=1 (Carol only), got {dept_sales.works_for_count}'
        assert dept_sales.works_for_salary_total == 1500, \
            f'Expected Sales works_for_salary_total=1500 (Carol only), got {dept_sales.works_for_salary_total}'

        # Marketing gains Alice
        assert dept_mkt.works_for_count == 1, f'Expected Marketing works_for_count=1 (Alice), got {dept_mkt.works_for_count}'
        assert dept_mkt.works_for_salary_total == 1000, \
            f'Expected Marketing works_for_salary_total=1000 (Alice), got {dept_mkt.works_for_salary_total}'

        # Alice's on_loan role (Engineering) is untouched by the works_for reparent
        assert dept_eng.on_loan_count == 2, f'Expected Engineering on_loan_count=2 (Bob, Alice - unchanged), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 3000, \
            f'Expected Engineering on_loan_salary_total=3000 (unchanged), got {dept_eng.on_loan_salary_total}'

        # Sanity: Sales' on_loan side (Carol) also untouched by Alice's works_for move
        assert dept_sales.on_loan_count == 1, f'Expected Sales on_loan_count=1 (Carol - unchanged), got {dept_sales.on_loan_count}'

    def test_reparent_across_roles(self):
        """ Move Alice from on_loan=Engineering(2) to on_loan=Sales(1) - i.e., she's no longer on loan
        to Engineering, now on loan to her own Sales department. Engineering's on_loan side must lose
        her contribution, Sales' on_loan side must gain it, and Alice's works_for role (Sales) - already
        pointing at the same department she's now on_loan to - must independently retain its own count/sum.
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        alice.on_loan_id = 1  # Engineering -> Sales
        session.commit()

        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()

        # Engineering's on_loan side loses Alice (was Bob+Alice=2/3000, now just Bob: 1/2000)
        assert dept_eng.on_loan_count == 1, f'Expected Engineering on_loan_count=1 (Bob only), got {dept_eng.on_loan_count}'
        assert dept_eng.on_loan_salary_total == 2000, \
            f'Expected Engineering on_loan_salary_total=2000 (Bob only), got {dept_eng.on_loan_salary_total}'

        # Sales' on_loan side gains Alice (was just Carol: 1/1500, now Carol+Alice: 2/2500)
        assert dept_sales.on_loan_count == 2, f'Expected Sales on_loan_count=2 (Carol, Alice), got {dept_sales.on_loan_count}'
        assert dept_sales.on_loan_salary_total == 2500, \
            f'Expected Sales on_loan_salary_total=2500 (Carol 1500 + Alice 1000), got {dept_sales.on_loan_salary_total}'

        # Sales' works_for side (Alice, Carol) is a DIFFERENT role/bucket on the SAME department -
        # must remain exactly as before, not merged with or doubled by the on_loan change
        assert dept_sales.works_for_count == 2, f'Expected Sales works_for_count=2 (unchanged), got {dept_sales.works_for_count}'
        assert dept_sales.works_for_salary_total == 2500, \
            f'Expected Sales works_for_salary_total=2500 (unchanged), got {dept_sales.works_for_salary_total}'
