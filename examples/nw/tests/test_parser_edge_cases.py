import sys, unittest
from datetime import datetime
import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_parser_edge_cases")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests
    from examples.nw.logic import session, engine  # initializes logic_bank before AbstractRule import

    from logic_bank.rule_type.abstractrule import AbstractRule


def make_rule(expr: str) -> AbstractRule:
    """Instantiate a bare AbstractRule (no DB needed) and parse the given expression."""
    rule = AbstractRule.__new__(AbstractRule)
    rule._dependencies = []
    rule.parse_dependencies(expr)
    return rule


class TestParserEdgeCases(unittest.TestCase):
    """Unit tests for AbstractRule.parse_dependencies covering paren-stripping edge cases.

    The bug (pre-fix): after stripping a leading '(' to derive the_word, subsequent
    rstrip operations mistakenly used each_word instead of the_word, leaving the
    leading '(' in the result and causing the dependency to be missed entirely.

    Fixed by: the_word = each_word.lstrip("(").rstrip("),")
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_baseline_no_parens(self):
        """Plain row.attr references - always worked, confirms baseline."""
        rule = make_rule("lambda row: row.Balance <= row.CreditLimit")
        self.assertIn("Balance", rule._dependencies,
                      f"Balance not found in {rule._dependencies}")
        self.assertIn("CreditLimit", rule._dependencies,
                      f"CreditLimit not found in {rule._dependencies}")

    def test_single_parens_both_sides(self):
        """(row.Balance) and (row.CreditLimit) - parens on both sides of each ref.
        Old code: strip leading '(' gives the_word='row.Balance)', then
        each_word[0:len(the_word)-1] = '(row.Balanc' - dependency missed."""
        rule = make_rule("lambda row: (row.Balance) <= (row.CreditLimit)")
        self.assertIn("Balance", rule._dependencies,
                      f"Balance not found in {rule._dependencies}")
        self.assertIn("CreditLimit", rule._dependencies,
                      f"CreditLimit not found in {rule._dependencies}")

    def test_trailing_paren_comma(self):
        """(row.Balance), and (row.CreditLimit) - the '),' suffix.
        Old code: strip leading '(' gives the_word='row.Balance),', then
        each_word[0:len(the_word)-2] = '(row.Balance' - dependency missed."""
        rule = make_rule("(row.Balance), (row.CreditLimit)")
        self.assertIn("Balance", rule._dependencies,
                      f"Balance not found in {rule._dependencies}")
        self.assertIn("CreditLimit", rule._dependencies,
                      f"CreditLimit not found in {rule._dependencies}")

    def test_double_parens(self):
        """((row.Balance)) - multiple leading and trailing parens.
        Old code: strips only one leading '(' leaving '(row.Balance))' then
        strips one trailing ')' using each_word giving '((row.Balance)' - missed."""
        rule = make_rule("lambda row: ((row.Balance)) <= ((row.CreditLimit))")
        self.assertIn("Balance", rule._dependencies,
                      f"Balance not found in {rule._dependencies}")
        self.assertIn("CreditLimit", rule._dependencies,
                      f"CreditLimit not found in {rule._dependencies}")

    def test_function_call_trailing_comma(self):
        """max(row.Balance, row.CreditLimit) - 'row.Balance,' has a trailing comma.
        The token is 'row.Balance,' (no leading paren), rstrip(',') should give 'row.Balance'."""
        rule = make_rule("lambda row: max(row.Balance, row.CreditLimit) >= 0")
        self.assertIn("Balance", rule._dependencies,
                      f"Balance not found in {rule._dependencies}")
        self.assertIn("CreditLimit", rule._dependencies,
                      f"CreditLimit not found in {rule._dependencies}")
