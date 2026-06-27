import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.multi_relns.tests.test_link_disambiguation")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.multi_relns import tests
    import examples.multi_relns.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    LogicRow.link() multi-relationship disambiguation (the "parent refs / insert-link" thread
    flagged as open in system/LogicBank-Internal-Dev/multi-relationship-bug.md). link() is used
    by manual programmatic row-creation patterns - new_logic_row().link(to_parent=...) - including
    the Allocation extension (logic_bank/extensions/allocate.py) and manual audit-copy patterns
    (examples/nw/logic/extensibility/nw_copy.py).

    NOT the same bug as GitHub issue #6 (closed - that was a separate isinstance/nodal-name bug,
    already fixed in the current code). The "TODO - disambiguate relationship" exception in the
    same method survived that fix untouched - this is what's tested/fixed here: link() gained a
    child_role_name parameter (mirroring Rule.sum/Rule.count/Rule.copy).

    Driven through a real Rule.commit_row_event (matching nw_copy.py's actual usage pattern) -
    new_logic_row()/link()/insert() need a real, engine-supplied row_sets to run the full rule
    pipeline (Rule.copy etc. fire on the linked row's insert) - a standalone LogicRow(row_sets=None)
    is only safe for link()-only checks, not a full insert().
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def _activate_link_rule(self, child_role_name):
        """ Re-activates LogicBank on self.session with rules_bank.py's rules PLUS a one-off
        commit_row_event that, when a Department is touched, manually creates+links a new
        Employee via the given child_role_name - exercising link() inside a real rule context.
        """
        from logic_bank.logic_bank import LogicBank, Rule
        from examples.multi_relns.logic.rules_bank import declare_logic as base_declare_logic

        new_employee_name = {"name": None}

        def add_employee_via_link(row, old_row, logic_row):
            if new_employee_name["name"] is None:
                return
            new_emp_logic_row = logic_row.new_logic_row(models.Employee)
            new_emp_logic_row.row.name = new_employee_name["name"]
            new_emp_logic_row.row.salary = 1700
            if child_role_name == "EmployeeOnLoanList":
                new_emp_logic_row.row.works_for_id = row.id  # satisfy NOT NULL; test is about on_loan
            new_emp_logic_row.link(to_parent=logic_row, child_role_name=child_role_name)
            new_emp_logic_row.insert(reason="test link " + child_role_name)

        def declare_logic():
            base_declare_logic()
            Rule.commit_row_event(on_class=models.Department, calling=add_employee_via_link)

        LogicBank.activate(session=self.session, activator=declare_logic,
                           aggregate_defaults=True, all_defaults=False)
        return new_employee_name

    def test_link_resolves_correct_role_works_for(self):
        """ Manually create a new Employee and link() it to Sales via the works_for role.
        Must resolve works_for_id, leaving on_loan_id untouched (None/unset).
        """
        session = self.session
        new_employee_name = self._activate_link_rule(child_role_name="EmployeeWorksForList")

        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        new_employee_name["name"] = "Grace"
        dept_sales.name = "Sales"  # trigger the commit_row_event without changing semantics
        session.commit()

        grace = session.query(models.Employee).filter(models.Employee.name == "Grace").one()
        assert grace.works_for_id == 1, f'Expected works_for_id=1 (Sales), got {grace.works_for_id}'
        assert grace.on_loan_id is None, f'Expected on_loan_id unset, got {grace.on_loan_id}'

    def test_link_resolves_correct_role_on_loan(self):
        """ Same as above, but link() to the on_loan role instead - must resolve on_loan_id,
        not works_for_id - proving child_role_name actually drives which relationship is used,
        not just "whichever happens to be visited first/last".
        """
        session = self.session
        new_employee_name = self._activate_link_rule(child_role_name="EmployeeOnLoanList")

        dept_eng = session.query(models.Department).filter(models.Department.id == 2).one()
        new_employee_name["name"] = "Henry"
        dept_eng.name = "Engineering"  # trigger the commit_row_event without changing semantics
        session.commit()

        henry = session.query(models.Employee).filter(models.Employee.name == "Henry").one()
        assert henry.on_loan_id == 2, f'Expected on_loan_id=2 (Engineering), got {henry.on_loan_id}'
        assert henry.works_for_id == 2, f'Expected works_for_id=2 (set by test to satisfy NOT NULL), got {henry.works_for_id}'

    def test_link_without_child_role_name_still_raises_on_ambiguity(self):
        """ The no-child_role_name case must still fail fast (by design) rather than silently
        guessing which relationship to use - same convention as Sum/Count/Copy's single-
        relationship-only shortcut.
        """
        from logic_bank.exec_row_logic.logic_row import LogicRow
        session = self.session
        dept_sales = session.query(models.Department).filter(models.Department.id == 1).one()
        dept_logic_row = LogicRow(row=dept_sales, old_row=dept_sales, ins_upd_dlt="*", nest_level=0,
                                  a_session=session, row_sets=None)

        new_emp_logic_row = dept_logic_row.new_logic_row(models.Employee)
        new_emp_logic_row.row.name = "Iris"

        raised = False
        try:
            new_emp_logic_row.link(to_parent=dept_logic_row)
        except Exception as e:
            raised = True
            assert "Ambiguous Relationship" in str(e), f'Expected Ambiguous Relationship error, got: {e}'

        assert raised, 'Expected link() without child_role_name against an ambiguous parent to raise'
