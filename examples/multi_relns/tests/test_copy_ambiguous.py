import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_copy_ambiguous")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Rule.copy multi-relationship disambiguation - FIXED: Rule.copy() now accepts a child_role_name
    parameter (mirroring Rule.sum/Rule.count), so it can target a specific relationship when 2+
    relationships connect the child class to the same parent class.

    rules_bank.py declares:
        Rule.copy(derive=Employee.works_for_dept_name_copy, from_parent=Department.name,
                  child_role_name="works_for_dept")

    See system/LogicBank-Internal-Dev/multi-relationship-bug.md "Status" section.

    The no-child_role_name ambiguous case (still correctly raises, by design - same fail-fast as
    Sum/Count's single-relationship-only shortcut) is tested separately below, in isolation, since
    it needs its own throwaway activation rather than the shared rules_bank.py rules.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_copy_resolves_correct_role_at_insert(self):
        """ Alice: works_for=Sales(1), on_loan=Engineering(2). The copy rule targets works_for_dept -
        works_for_dept_name_copy must be Sales, NOT Engineering (which would indicate the wrong
        relationship was resolved, or the ambiguity loop fell through to the last one).
        """
        session = self.session
        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.works_for_dept_name_copy == 'Sales', \
            f'Expected works_for_dept_name_copy=Sales, got {alice.works_for_dept_name_copy}'

    def test_copy_does_not_propagate_on_parent_rename(self):
        """ Rule.copy is a snapshot - renaming the works_for parent (Sales) after the Employee
        is inserted must NOT change works_for_dept_name_copy (that's Rule.formula's job, tested
        separately in test_formula_cascade.py). Confirms copy-vs-live semantics still hold for the
        multi-relationship case, not just the single-relationship case.
        """
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_sales.name = 'Sales-Renamed'
        session.commit()

        alice = session.query(models.Employee).filter(models.Employee.id == 1).one()
        assert alice.works_for_dept_name_copy == 'Sales', \
            f'Expected works_for_dept_name_copy unchanged at Sales (snapshot), got {alice.works_for_dept_name_copy}'

    def test_copy_picks_the_role_named_by_child_role_name_not_the_other_one(self):
        """ Isolated check: declaring the SAME Rule.copy with child_role_name="on_loan_dept" instead
        resolves to the OTHER department - proves child_role_name actually drives resolution, rather
        than some other mechanism (e.g. declaration order) coincidentally producing the right answer.
        """
        import sqlalchemy
        from sqlalchemy.orm import sessionmaker
        from logic_bank.logic_bank import LogicBank, Rule
        from examples.multi_relns.db.models import Department, Employee, Base

        engine = sqlalchemy.create_engine('sqlite://')
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        def declare_logic_via_on_loan():
            Rule.copy(derive=Employee.works_for_dept_name_copy, from_parent=Department.name,
                      child_role_name="on_loan_dept")

        LogicBank.activate(session=session, activator=declare_logic_via_on_loan)
        d1 = Department(id=1, name='Sales')
        d2 = Department(id=2, name='Engineering')
        session.add_all([d1, d2])
        session.commit()
        e1 = Employee(id=1, name='Alice', salary=1000, works_for_id=1, on_loan_id=2)
        session.add(e1)
        session.commit()

        assert e1.works_for_dept_name_copy == 'Engineering', \
            f'Expected Engineering (via on_loan_dept role), got {e1.works_for_dept_name_copy}'

        session.close()
        engine.dispose()

    def test_copy_without_child_role_name_still_raises_on_ambiguity(self):
        """ The no-child_role_name case must still fail fast (by design, same as Sum/Count's
        single-relationship-only shortcut) rather than silently guessing - this is NOT a regression
        to preserve, it's the intended, documented behavior when the caller hasn't disambiguated.
        """
        import sqlalchemy
        from sqlalchemy.orm import sessionmaker
        from logic_bank.logic_bank import LogicBank, Rule
        from logic_bank.exceptions import LBActivateException
        from examples.multi_relns.db.models import Department, Employee, Base

        engine = sqlalchemy.create_engine('sqlite://')
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        def declare_logic_with_ambiguous_copy():
            Rule.copy(derive=Employee.works_for_dept_name_copy, from_parent=Department.name)

        raised = False
        try:
            LogicBank.activate(session=session, activator=declare_logic_with_ambiguous_copy)
        except LBActivateException as e:
            raised = True
            assert any('Ambiguous Relationship' in str(invalid_rule) for invalid_rule in e.invalid_rules), \
                f'Expected an Ambiguous Relationship error in invalid_rules, got {e.invalid_rules}'

        assert raised, 'Expected Rule.copy without child_role_name against an ambiguous parent to raise'

        session.close()
        engine.dispose()
