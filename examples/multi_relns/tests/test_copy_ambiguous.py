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
    # deliberately NOT importing examples.multi_relns.logic here - this test activates its
    # own throwaway LogicBank session with a Rule.copy added, to test ambiguity handling in
    # isolation without disturbing the shared session other test files in this directory use.
    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Rule.copy has NO child_role_name / role disambiguation parameter (unlike Rule.sum/Rule.count).
    See system/LogicBank-Internal-Dev/multi-relationship-bug.md - "Rule.copy - confirmed: not buggy,
    simply never finished". Against a multi-relationship parent (Department, reachable from Employee
    via both works_for_dept and on_loan_dept), Rule.copy(from_parent=Department.name) cannot resolve
    which relationship to use, and raises:
        LBActivateException: [Exception('TODO / copy - disambiguate relationship')]

    This test documents that CURRENT, honestly-unfinished behavior - it asserts the exception is
    raised, not that copy works. When Rule.copy gains a child_role_name parameter, this test should
    be rewritten to assert correct snapshot behavior instead (mirroring test_formula_cascade.py's
    live-reference equivalent).
    """

    def test_copy_from_ambiguous_parent_raises_todo_exception(self):
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
            assert any('disambiguate relationship' in str(invalid_rule) for invalid_rule in e.invalid_rules), \
                f'Expected a disambiguate-relationship error in invalid_rules, got {e.invalid_rules}'

        assert raised, \
            'Expected Rule.copy against an ambiguous (multi-relationship) parent to raise LBActivateException - ' \
            'if this now passes, Rule.copy has gained role-disambiguation support and this test should be ' \
            'rewritten to assert correct snapshot behavior (see module docstring).'

        session.close()
        engine.dispose()

        print("\n...test_copy_from_ambiguous_parent_raises_todo_exception ran to completion\n\n")
