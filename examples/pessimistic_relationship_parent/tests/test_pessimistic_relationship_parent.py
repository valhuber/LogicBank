import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.pessimistic_relationship_parent.tests.test_pessimistic_relationship_parent")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import subprocess

    print("\n" + sys_env_info + "\n\n")


def _run_mode(mode: str) -> dict:
    """
    Run one trans_update_locking mode in its own subprocess. RuleBank is a
    process-wide singleton (logic_bank/rule_bank/rule_bank.py) - a second
    LogicBank.activate() call in the same process, with a different
    trans_update_locking, would reuse the first activation's state.
    """
    worker = __file__.replace("test_pessimistic_relationship_parent.py",
                              "_worker_pessimistic_relationship_parent.py")
    result = subprocess.run([sys.executable, worker, mode], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "lines": lines,
    }


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #37
    (https://github.com/valhuber/LogicBank/issues/37):
    trans_update_locking="pessimistic" nulls the foreign key of a child linked
    to an EXISTING parent through the relationship (Order(customer=customer)),
    instead of adjusting the parent.

    Before the flush, SQLAlchemy has not yet copied the parent's key into the
    child's FK column. LogicRow._get_parent_logic_row built the locking read's
    parent_key entirely from that (still-None) FK column, so it queried with
    None, found no parent, and the setattr(row, role_name, None) that follows
    detached the child - with no error. #30 fixed the same path for a parent
    that is not in the database yet (just insert_parent'd in this
    transaction); this is the parent that IS in the database, with the FK
    column simply not populated yet.

    Fixed: when the FK-derived parent_key is (still) None but the relationship
    already holds a parent object (vars(row).get(role_name)), the key is taken
    from that related object instead.

    See system/LogicBank-Internal-Dev/pessimistic-locking-issues-36-37.md.
    """

    def test_ignored_mode_baseline(self):
        """ Baseline: the default (unlocked) mode must be unaffected by the fix. """
        result = _run_mode("ignored")
        self.assertEqual(result["returncode"], 0,
                         f"ignored mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_ignored_mode_baseline ran to completion\n\n")

    def test_pessimistic_mode_keeps_relationship_linked_parent(self):
        """
        The actual regression: with pessimistic locking, a child linked to an
        existing parent through the relationship must keep its FK and adjust
        the parent's balance.
        """
        result = _run_mode("pessimistic")
        self.assertEqual(result["returncode"], 0,
                         f"pessimistic mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_pessimistic_mode_keeps_relationship_linked_parent ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
