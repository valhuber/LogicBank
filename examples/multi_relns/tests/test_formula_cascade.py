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

    rules_bank.py declares only ONE Rule.formula (Employee.on_loan_dept_name_live, via on_loan_dept).
    This is deliberate: per system/LogicBank-Internal-Dev/multi-relationship-bug.md, get_referring_children()
    (rule_bank_withdraw.py) resets its result list INSIDE the per-relationship loop, so a parent class with
    2+ ONETOMANY relationships only keeps the LAST one's referring children - declaring a second Rule.formula
    on works_for_dept would silently break cascade for one or both roles. That bug is not yet fixed
    (see "A third direction" in multi-relationship-bug.md) - this suite documents/exercises the one-role
    case that IS known to work, and is the place to extend once that fix lands.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_live_reference_reflects_initial_parent_value(self):
        """ Sanity: on insert, the live-reference formula picks up the correct role's parent value
        (not the OTHER role's parent, which is the failure mode if role resolution were wrong here too).
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        # Alice: works_for=Sales(1), on_loan=Engineering(2) - on_loan_dept_name_live must be Engineering, not Sales
        assert alice.on_loan_dept_name_live == 'Engineering', \
            f'Expected on_loan_dept_name_live=Engineering, got {alice.on_loan_dept_name_live}'

    def test_live_reference_propagates_when_parent_changes(self):
        """ Case: rename the on_loan parent (Engineering) - the live-reference formula must cascade/update.
        This is the live-vs-snapshot distinction itself (Rule.formula propagates; Rule.copy would not).
        """
        session = self.session
        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        dept_eng.name = 'Engineering-Renamed'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.on_loan_dept_name_live == 'Engineering-Renamed', \
            f'Expected on_loan_dept_name_live to cascade to Engineering-Renamed, got {alice.on_loan_dept_name_live}'

    def test_live_reference_does_not_react_to_unrelated_role_change(self):
        """ Case: rename the OTHER department (Sales, which Alice works_for but is not on_loan to).
        Alice's on_loan_dept_name_live must NOT change - confirms the cascade is scoped to the correct role,
        not firing for any change to any relationship target.
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_sales.name = 'Sales-Renamed'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.on_loan_dept_name_live == 'Engineering', \
            f'Expected on_loan_dept_name_live unaffected by Sales rename, got {alice.on_loan_dept_name_live}'
