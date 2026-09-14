"""
Reparenting (changing a child's FK to point at a different parent) is a
corner case that hand-written logic routinely misses: it's easy to write
code that recomputes a sum/count when a row is inserted, updated or
deleted, and forget the fourth case - the row moves to a *different*
parent, so *both* the old and new parent must be adjusted in the same
transaction. LogicBank derives this automatically from the same Rule.sum
declaration; these tests exist to pin that guarantee down, including the
case where the reparent is rejected (both parents must then be left
untouched - see test_reparent_rejected).
"""
import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_upd_order_customer")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt, ConstraintException

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        """
        The FK-only reparent case: Order.CustomerId changes, nothing else.
        Manual/procedural logic for "update order" or "update customer
        balance" would not naturally run here at all, since neither Order
        nor OrderDetail amounts changed - the FK move itself is the only
        trigger. Both old and new parent must adjust by the order amount.
        """

        pre_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        pre_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
        session.expunge(pre_alfki)
        session.expunge(pre_anatr)

        if pre_alfki.Balance != 1016:
            self.fail("pre_alfki balance not 1016 (database-gold not copied?), value: " + str(pre_alfki.Balance))

        print("")
        test_order = session.query(models.Order).filter(models.Order.Id == 11011).one()  # type : Order
        amount_total = test_order.AmountTotal
        if test_order.CustomerId  == "ALFKI":
            test_order.CustomerId = "ANATR"
        else:
            test_order.CustomerId = "ALFKI"
        print(prt("Reparenting order - new CustomerId: " + test_order.CustomerId))
        session.commit()

        print("")
        post_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        logic_row = LogicRow(row=post_alfki, old_row=pre_alfki, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

        if abs(post_alfki.Balance - pre_alfki.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            pass
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))

        post_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
        logic_row = LogicRow(row=post_anatr, old_row=pre_anatr, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

        if abs(post_anatr.Balance - pre_anatr.Balance) == 960:
            logic_row.log("Correct adjusted Customer Result")
            pass
        else:
            self.fail(logic_row.log("Incorrect adjusted Customer Result - expected 960 difference"))

        print("\nupd_order_customer, ran to completion")
        self.assertTrue(True)

    def test_reparent_rejected(self):
        """
        The other half of the corner case above: a *rejected* reparent.
        Manual logic that does remember to handle FK changes often still
        gets this half wrong - e.g. adjusting the old parent down before
        checking the new parent's constraint, leaving a stale/partial
        update if the constraint then fails. Here the reparent (ALFKI ->
        ANTON) should be rejected outright by the credit-limit constraint,
        and *both* customers' balances must be left untouched - old parent
        not adjusted away, new parent not adjusted to receive it.
        """

        pre_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        pre_anton = session.query(models.Customer).filter(models.Customer.Id == "ANTON").one()
        pre_alfki_balance = pre_alfki.Balance
        pre_anton_balance = pre_anton.Balance
        session.expunge(pre_alfki)
        session.expunge(pre_anton)

        print("")
        test_order = session.query(models.Order).filter(models.Order.Id == 11011).one()
        self.assertEqual(test_order.CustomerId, "ALFKI", "gold data assumption changed")
        test_order.CustomerId = "ANTON"
        print(prt("Reparenting order to over-limit Customer - new CustomerId: " + test_order.CustomerId))

        did_fail_as_expected = False
        try:
            session.commit()
        except ConstraintException as ce:
            print("Expected constraint: " + str(ce))
            session.rollback()
            did_fail_as_expected = True
        except:
            self.fail("Unexpected Exception Type")

        if not did_fail_as_expected:
            self.fail("reparent to over-limit Customer expected to fail, but succeeded")

        print("")
        post_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        post_anton = session.query(models.Customer).filter(models.Customer.Id == "ANTON").one()

        if post_alfki.Balance != pre_alfki_balance:
            self.fail("Old parent (ALFKI) balance changed despite rejected reparent: " +
                      str(pre_alfki_balance) + " -> " + str(post_alfki.Balance))
        if post_anton.Balance != pre_anton_balance:
            self.fail("New parent (ANTON) balance changed despite rejected reparent: " +
                      str(pre_anton_balance) + " -> " + str(post_anton.Balance))

        post_order = session.query(models.Order).filter(models.Order.Id == 11011).one()
        if post_order.CustomerId != "ALFKI":
            self.fail("Order CustomerId not rolled back - expected ALFKI, got " + post_order.CustomerId)

        print("\nupd_order_customer (rejected reparent), ran to completion")
        self.assertTrue(True)


