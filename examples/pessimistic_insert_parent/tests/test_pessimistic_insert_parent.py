import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.pessimistic_insert_parent.tests.test_pessimistic_insert_parent")
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
    trans_update_locking, would reuse the first activation's state. This
    mirrors GitHub issue #30's own repro script, which spawns a subprocess
    per mode for the same reason.
    """
    worker = __file__.replace("test_pessimistic_insert_parent.py", "_worker_pessimistic_insert_parent.py")
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
    Regression test for GitHub issue #30
    (https://github.com/valhuber/LogicBank/issues/30):
    trans_update_locking="pessimistic" loses the parent created by
    insert_parent, within the SAME transaction.

    LogicRow._get_parent_logic_row (exec_row_logic/logic_row.py), under
    for_update=True with pessimistic locking, used to skip the fast in-memory
    relationship read entirely and go straight to a locking DB read
    (with_for_update().populate_existing().get()). When insert_parent had just
    created the parent earlier in the SAME transaction, that parent exists only
    in memory (not yet flushed) - the locking read found nothing and returned
    None. Two silent failures followed:
      - The adjustment was skipped: the new parent got its aggregate default
        instead of the child's contribution.
      - _get_parent_logic_row then did setattr(row, role_name, None), which -
        for a composite FK - nulls the child's own FK columns as a side effect;
        even for a single-column FK (this suite's case) the child ends up
        unlinked from the parent it was just inserted with.
    In 1.34.0, the #26 fix compounds this: adjust_from_inserted_child sees no
    parent and calls _is_inserted_parent again, inserting the parent a SECOND
    time - IntegrityError: UNIQUE constraint failed.

    Fixed: use_locking_read now also checks whether the relationship already
    holds a PERSISTENT (already-flushed) parent (via inspect(...).key). A
    pending, just-inserted parent, or an unset relationship, falls through to
    the normal getattr(row, role_name) path instead of forcing a locking read -
    exactly what the "ignored" mode already did correctly.

    See system/LogicBank-Internal-Dev/pessimistic-locking-insert-parent.md.
    """

    def test_ignored_mode_baseline(self):
        """ Baseline: the default (unlocked) mode must be unaffected by the fix. """
        result = _run_mode("ignored")
        self.assertEqual(result["returncode"], 0,
                         f"ignored mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_ignored_mode_baseline ran to completion\n\n")

    def test_pessimistic_mode_keeps_insert_parent_adjustment(self):
        """
        The actual regression: with pessimistic locking, a SaleLine that
        inserts its own Stock parent (via insert_parent=True) must still see
        that parent's `sold` correctly adjusted, and must stay linked to it.
        """
        result = _run_mode("pessimistic")
        self.assertEqual(result["returncode"], 0,
                         f"pessimistic mode failed:\n{result['stdout']}\n{result['stderr']}")
        self.assertIn("ok", result["stdout"])

        print("\n...test_pessimistic_mode_keeps_insert_parent_adjustment ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
