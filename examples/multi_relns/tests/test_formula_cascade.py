import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_formula_cascade")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Live parent->child cascade (Rule.formula referencing row.<role>.<attr>) - multi-relationship case.

    rules_bank.py declares TWO Rule.formula rules (on_loan_dept_name_live AND works_for_dept_name_live,
    same parent class Department, different roles). This exercises get_referring_children()'s
    multi-relationship disambiguation (rule_bank_withdraw.py) - FIXED: that function used to reset
    its accumulator dict INSIDE the per-relationship loop, so a parent class with 2+ ONETOMANY
    relationships only kept the LAST one's referring children - only one of these two formulas
    would ever cascade. See system/LogicBank-Internal-Dev/multi-relationship-bug.md "Status" section.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_live_reference_reflects_initial_parent_value_both_roles(self):
        """ Sanity: on insert, BOTH live-reference formulas pick up the correct role's parent value
        (not the OTHER role's parent, which is the failure mode if role resolution were wrong here too).
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        # Alice: works_for=Sales(1), on_loan=Engineering(2)
        assert alice.works_for_dept_name_live == 'Sales', \
            f'Expected works_for_dept_name_live=Sales, got {alice.works_for_dept_name_live}'
        assert alice.on_loan_dept_name_live == 'Engineering', \
            f'Expected on_loan_dept_name_live=Engineering, got {alice.on_loan_dept_name_live}'

    def test_renaming_on_loan_parent_cascades_only_on_loan_side(self):
        """ Rename the on_loan parent (Engineering) - on_loan_dept_name_live must cascade.
        works_for_dept_name_live (Sales, untouched) must NOT change.
        This is the THIS-PASSING-BEFORE-THE-FIX case: with only one Rule.formula declared,
        get_referring_children()'s reset-in-loop bug never had a second relationship to clobber.
        With two declared (as here), the bug previously caused NEITHER to cascade.
        """
        session = self.session
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_eng.name = 'Engineering-Renamed'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.on_loan_dept_name_live == 'Engineering-Renamed', \
            f'Expected on_loan_dept_name_live to cascade to Engineering-Renamed, got {alice.on_loan_dept_name_live}'
        assert alice.works_for_dept_name_live == 'Sales', \
            f'Expected works_for_dept_name_live unaffected by Engineering rename, got {alice.works_for_dept_name_live}'

    def test_renaming_works_for_parent_cascades_only_works_for_side(self):
        """ Mirror of the above, other role - rename the works_for parent (Sales).
        works_for_dept_name_live must cascade; on_loan_dept_name_live (Engineering, untouched) must not.
        THIS is the specific case that proves the fix: before the fix, get_referring_children()'s
        per-relationship-loop reset meant only the LAST-declared Rule.formula's role (on_loan, declared
        second in rules_bank.py) ever cascaded - works_for's cascade would have silently done nothing.
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_sales.name = 'Sales-Renamed'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.works_for_dept_name_live == 'Sales-Renamed', \
            f'Expected works_for_dept_name_live to cascade to Sales-Renamed, got {alice.works_for_dept_name_live}'
        assert alice.on_loan_dept_name_live == 'Engineering', \
            f'Expected on_loan_dept_name_live unaffected by Sales rename, got {alice.on_loan_dept_name_live}'

    def test_renaming_both_parents_cascades_both_roles_independently(self):
        """ Rename BOTH departments in the same transaction - both formulas on Alice must cascade,
        independently, to the correct new value.
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_sales.name = 'Sales-X'
        dept_eng.name = 'Engineering-X'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.works_for_dept_name_live == 'Sales-X', \
            f'Expected works_for_dept_name_live=Sales-X, got {alice.works_for_dept_name_live}'
        assert alice.on_loan_dept_name_live == 'Engineering-X', \
            f'Expected on_loan_dept_name_live=Engineering-X, got {alice.on_loan_dept_name_live}'
