import sys, unittest
from datetime import datetime
import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_should_defer_chaining")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests
    from examples.nw.logic import session, engine  # opens db, activates rules

    from logic_bank.exec_row_logic.logic_row import LogicRow, ParentRoleAdjuster
    from logic_bank.exec_trans_logic.row_sets import RowSets
    import examples.nw.db.models as models


class TestShouldDeferChaining(unittest.TestCase):
    """Direct unit tests for ParentRoleAdjuster._should_defer_chaining().

    Companion to the integration-level regression test test_upd_order_reuse.py, which
    exercises the real bug (nondeterministic SQLAlchemy session.dirty order) end-to-end but
    only reproduces it about half the time. These tests fabricate RowSets state directly, so
    the *decision logic* itself - not the surrounding nondeterminism - gets a fast, deterministic
    test. See system/LogicBank-Internal-Dev/dragons-deferred-adjustment.md for full background.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def _make_parent_logic_row(self, row_sets: RowSets):
        customer = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        return LogicRow(row=customer, old_row=customer, ins_upd_dlt="upd", nest_level=0,
                        a_session=session, row_sets=row_sets)

    def test_defers_when_submitted_but_not_yet_processed(self):
        """ The exact upd_order_reuse case: parent was directly edited by the client this
        transaction (submitted) but hasn't run its own rules yet (not processed) - chaining
        must defer, since the parent's own later pass will run it.
        """
        row_sets = RowSets()
        parent_logic_row = self._make_parent_logic_row(row_sets)
        row_sets.add_submitted(parent_logic_row.row)
        # deliberately NOT calling add_processed_logic - parent not yet processed

        adjustor = ParentRoleAdjuster(parent_role_name="Customer", child_logic_row=parent_logic_row)
        assert adjustor._should_defer_chaining(parent_logic_row) is True, \
            'Expected defer=True: parent submitted but not yet processed'

    def test_does_not_defer_when_processed(self):
        """ Parent was submitted AND has already been processed this transaction (its own
        rules already ran) - safe to chain now, nothing left to wait for.
        """
        row_sets = RowSets()
        parent_logic_row = self._make_parent_logic_row(row_sets)
        row_sets.add_submitted(parent_logic_row.row)
        row_sets.add_processed_logic(logic_row=parent_logic_row)

        adjustor = ParentRoleAdjuster(parent_role_name="Customer", child_logic_row=parent_logic_row)
        assert adjustor._should_defer_chaining(parent_logic_row) is False, \
            'Expected defer=False: parent already processed this transaction'

    def test_does_not_defer_when_not_submitted_at_all(self):
        """ Parent was never directly edited by the client this transaction (only reached via
        engine-driven cascade/adjustment) - nothing else will process it, so chaining must run
        now or it never will.
        """
        row_sets = RowSets()
        parent_logic_row = self._make_parent_logic_row(row_sets)
        # deliberately NOT calling add_submitted - parent reached only via adjustment

        adjustor = ParentRoleAdjuster(parent_role_name="Customer", child_logic_row=parent_logic_row)
        assert adjustor._should_defer_chaining(parent_logic_row) is False, \
            'Expected defer=False: parent not client-submitted, nothing else will chain it'
