import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.pessimistic_multi_child_adjust.tests.test_pessimistic_multi_child_adjust")
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
    worker = __file__.replace("test_pessimistic_multi_child_adjust.py",
                              "_worker_pessimistic_multi_child_adjust.py")
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
    Regression test for GitHub issue #36
    (https://github.com/valhuber/LogicBank/issues/36):
    trans_update_locking="pessimistic" loses a Rule.sum adjustment from an
    earlier child of the same parent, in the SAME flush.

    LogicRow._get_parent_logic_row (exec_row_logic/logic_row.py), under
    for_update=True with pessimistic locking, built its locking read as
    with_for_update().populate_existing().get(parent_key) on EVERY call. When
    a second child of the same parent is adjusted in the same flush, the
    parent is already in the session carrying the first child's adjustment,
    not yet flushed - populate_existing() unconditionally overwrote it with
    the database value, silently discarding that adjustment. The same refresh
    also discarded a client-side edit to the parent made in the same
    transaction.

    Fixed: LogicRow._refresh_locked_parent tracks (in RowSets.locked_parents)
    which parents have already had a locking read this flush. Only the FIRST
    locking read of a given parent refreshes it (and only the columns with no
    pending change, via session.refresh(..., attribute_names=..., with_for_
    update=True)); later reads in the same flush skip populate_existing()
    entirely and keep whatever LogicBank (or the client) has already changed
    in memory.

    See system/LogicBank-Internal-Dev/pessimistic-locking-issues-36-37.md.
    """

    def test_ignored_mode_baseline(self):
        """ Baseline: the default (unlocked) mode must be unaffected by the fix. """
        result = _run_mode("ignored")
        self.assertEqual(result["returncode"], 0,
                         f"ignored mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_ignored_mode_baseline ran to completion\n\n")

    def test_pessimistic_mode_keeps_both_children_adjustments(self):
        """
        The actual regression: with pessimistic locking, two orders for the
        same customer in one flush must both be reflected in the balance, and
        a client edit to the parent made alongside a third order must survive.
        """
        result = _run_mode("pessimistic")
        self.assertEqual(result["returncode"], 0,
                         f"pessimistic mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_pessimistic_mode_keeps_both_children_adjustments ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
