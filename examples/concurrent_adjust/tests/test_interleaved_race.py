import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.concurrent_adjust.tests.test_interleaved_race")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.concurrent_adjust import tests
    import examples.concurrent_adjust.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Tier 1 (see internal_dev/locking_strategy.md, ApiLogicServer-src): deterministic
    interleaved-session regression test reproducing the doc's Section 3 scenario
    directly - two ordinary SQLAlchemy sessions against the same SQLite DB, sequenced
    DELIBERATELY BY THE TEST (not by real threads/timing), so this is exactly as fast
    and stable as any other LogicBank test - no sleeps, no thread races to lose.

    What this proves: the lost-update / stale-constraint-pass bug reproduces exactly
    as documented under TRANS_UPDATE_LOCKING=ignored (today's default). This is a
    regression test for the BUG itself, independent of whether Option A (pessimistic
    locking) is even installed - it does NOT prove pessimistic locking closes the race
    (that needs a live blocking read, which SQLite's with_for_update() no-op cannot
    exercise - see test_for_update_sql.py for what CAN be proven on SQLite, and
    locking_strategy.md's Tier 2 for why a live-Postgres/real-thread test is
    deliberately not built here).

    Seed data (see db/create_db.py): Customer ALFKI, balance=900, credit_limit=1000.
    Two concurrent orders of 80 each are each individually well under the remaining
    100 of headroom - the bug is that the constraint never sees the TRUE combined
    total, because each transaction evaluates it against its own private, stale read.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        pass  # each test method manages its own two sessions/engines explicitly

    def test_concurrent_orders_under_ignored_locking_silently_exceed_credit_limit(self):
        """ TRANS_UPDATE_LOCKING=ignored (default): reproduces the doc's Section 3 race.

        T1 and T2 each independently read Customer.balance=900 BEFORE either writes
        (interleaving enforced by test sequencing below, not timing). Each computes
        980 in Python, and 980 <= 1000 passes the constraint in BOTH transactions -
        neither transaction ever sees the other's change. Final stored balance is
        980 (last writer wins), not the correct 1060 - a silent constraint bypass:
        the true combined total (1060) would have been rejected, but was never
        evaluated because neither transaction's Python-side read reflected it.
        """
        # T1: independent session, reads Customer BEFORE T2 writes anything
        session1, engine1 = tests.new_session_from_gold(trans_update_locking="ignored")
        cust_t1 = session1.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t1.balance == 900, f'Expected seed balance=900, got {cust_t1.balance}'

        # T2: SEPARATE independent session/engine, ALSO reads Customer before T1 writes -
        # this is the interleaving: both transactions' reads happen before either write,
        # scripted explicitly rather than raced via threads/timing.
        session2, engine2 = tests.new_session_from_gold(trans_update_locking="ignored")
        cust_t2 = session2.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t2.balance == 900, f'Expected seed balance=900, got {cust_t2.balance}'

        # T1 writes and commits first - computes 900 + 80 = 980, passes constraint (correctly,
        # in isolation), persists.
        order_t1 = models.Order(id=2, customer_id=1, amount_total=80, date_shipped=None)
        session1.add(order_t1)
        session1.commit()
        cust_t1_after = session1.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t1_after.balance == 980, f'Expected T1 balance=980, got {cust_t1_after.balance}'

        # T2 writes and commits second - but T2's session/Python state still reflects its
        # OWN stale read (balance=900) from before T1 committed. It computes 900 + 80 = 980
        # from ITS OWN stale starting point, NOT 980 + 80 = 1060 from T1's committed value.
        # The constraint (980 <= 1000) passes - but 980 is wrong, and worse, the constraint
        # never evaluated against the true combined total (1060), which SHOULD have been
        # rejected (1060 > 1000).
        order_t2 = models.Order(id=3, customer_id=1, amount_total=80, date_shipped=None)
        session2.add(order_t2)
        session2.commit()  # succeeds - this is the bug: it should have been rejected

        cust_t2_after = session2.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t2_after.balance == 980, \
            f'BUG REPRODUCTION: T2 stored balance=980 (its own stale computation), ' \
            f'not the correct 1060 - got {cust_t2_after.balance}'

        # Ground truth: the true total of both unshipped orders (900 original + 80 + 80 = 1060)
        # is NOT what ended up persisted (980) - one order's worth of balance (80) was silently
        # lost, AND the combined total exceeds credit_limit (1000) without ever being rejected.
        true_order_total = 900 + 80 + 80  # what SHOULD be the constraint-checked total
        assert true_order_total == 1060
        assert true_order_total > cust_t1_after.credit_limit, \
            'Sanity check: the true combined total (1060) exceeds credit_limit (1000) - ' \
            'this is exactly the case the constraint exists to reject, and silently did not.'
        assert cust_t2_after.balance != true_order_total, \
            f'Persisted balance ({cust_t2_after.balance}) should differ from the true total ' \
            f'({true_order_total}) under TRANS_UPDATE_LOCKING=ignored - this IS the bug.'

        session1.close(); engine1.dispose()
        session2.close(); engine2.dispose()

        print("\n...test_concurrent_orders_under_ignored_locking_silently_exceed_credit_limit ran to completion\n\n")

    def test_pessimistic_locking_closes_the_race_even_on_sqlite(self):
        """ SURPRISE FINDING (not what locking_strategy.md's Section 5/6 predicted for this
        SAME-PROCESS reproduction shape - see the note added to that doc): under
        TRANS_UPDATE_LOCKING=pessimistic, this exact interleaving is CORRECTLY REJECTED on
        SQLite too, even though SQLAlchemy's SQLite dialect silently drops the with_for_update()
        FOR UPDATE clause itself (confirmed separately in test_for_update_sql.py).

        Root cause, confirmed by direct experiment: it is NOT with_for_update() doing this -
        it's populate_existing(), which Option A's code always pairs with with_for_update()
        (see logic_row.py's _get_parent_logic_row). populate_existing() forces SQLAlchemy to
        re-read the row from the DB and refresh the ALREADY-CACHED Python object's attributes,
        instead of silently trusting session2's stale in-memory identity-map copy (from
        session2's own earlier read, before session1 committed). This closes the race for the
        SAME-PROCESS/same-machine, sequential-sessions-sharing-a-SQLite-file shape this test
        exercises - it is NOT equivalent to genuine cross-connection row locking, and says
        nothing about two truly concurrent processes/connections against Postgres (that
        remains the no-op case per Section 5, and remains Tier 2 - documented, not built).

        Net effect for THIS specific reproduction shape: T2's commit now correctly raises
        ConstraintException (balance would be 1060, exceeding credit_limit 1000) instead of
        silently persisting the wrong value (980).
        """
        from logic_bank.util import ConstraintException

        session1, engine1 = tests.new_session_from_gold(trans_update_locking="pessimistic")
        cust_t1 = session1.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t1.balance == 900

        session2, engine2 = tests.new_session_from_gold(trans_update_locking="pessimistic")
        cust_t2 = session2.query(models.Customer).filter(models.Customer.id == 1).one()
        assert cust_t2.balance == 900

        order_t1 = models.Order(id=2, customer_id=1, amount_total=80, date_shipped=None)
        session1.add(order_t1)
        session1.commit()

        order_t2 = models.Order(id=3, customer_id=1, amount_total=80, date_shipped=None)
        session2.add(order_t2)
        try:
            session2.commit()
            raise AssertionError(
                'Expected session2.commit() to raise ConstraintException (true combined '
                'balance 1060 > credit_limit 1000) - it succeeded instead, meaning '
                'populate_existing() did NOT refresh the stale identity-map read. If this '
                'assertion now fails, re-verify the root-cause experiment in this test\'s '
                'docstring before assuming Option A regressed.')
        except ConstraintException as e:
            assert 'exceeds credit_limit' in str(e), f'Unexpected constraint message: {e}'
        finally:
            session2.rollback()

        session1.close(); engine1.dispose()
        session2.close(); engine2.dispose()

        print("\n...test_pessimistic_locking_closes_the_race_even_on_sqlite ran to completion\n\n")
