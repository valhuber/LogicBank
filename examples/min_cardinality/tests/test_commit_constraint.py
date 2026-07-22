import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.min_cardinality.tests.test_commit_constraint")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.min_cardinality import tests
    import examples.min_cardinality.db.models as models
    from logic_bank.util import ConstraintException

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression tests for Rule.commit_constraint (logic_bank/rule_type/constraint.py),
    the min-cardinality case a plain Rule.constraint cannot reliably express: "Order
    must have at least one OrderDetail".

    A plain Rule.constraint on Order checking row.item_count > 0 is checked inline,
    mid-cascade, on every touch of Order during before_flush - including Order's own
    insert, which can be processed before its OrderDetails in the same transaction
    (SQLAlchemy gives no ordering guarantee across a flush's dirty/new rows).
    Rule.commit_constraint instead checks once per touched row, in after_flush,
    once the whole transaction's cascade has settled - so it always sees the final
    item_count, not a mid-cascade one.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_gold_seed_data_is_correct(self):
        """ Baseline: gold seed data's item_count is correctly derived for both orders. """
        session = self.session
        order1 = session.query(models.Order).filter(models.Order.id == 1).one()
        order2 = session.query(models.Order).filter(models.Order.id == 2).one()

        assert order1.item_count == 2, f'Expected Order 1 item_count=2, got {order1.item_count}'
        assert order2.item_count == 1, f'Expected Order 2 item_count=1, got {order2.item_count}'

        print("\n...test_gold_seed_data_is_correct ran to completion\n\n")

    def test_insert_order_with_items_same_transaction(self):
        """ Case 1: insert a new Order AND its OrderDetails in the SAME transaction/commit.
        CommitConstraint must NOT raise - by the time after_flush runs, both OrderDetails
        have chained their count adjustment into Order, regardless of mid-cascade ordering.
        """
        session = self.session
        new_order = models.Order(id=3, notes='Order 3')
        new_order.OrderDetailList.append(models.OrderDetail(id=4, product_name='Widget'))
        new_order.OrderDetailList.append(models.OrderDetail(id=5, product_name='Gadget'))
        session.add(new_order)
        session.commit()  # must NOT raise

        order3 = session.query(models.Order).filter(models.Order.id == 3).one()
        assert order3.item_count == 2, f'Expected Order 3 item_count=2, got {order3.item_count}'

        print("\n...test_insert_order_with_items_same_transaction ran to completion\n\n")

    def test_insert_order_without_items_raises(self):
        """ Case 2: insert an Order with NO OrderDetails, commit alone.
        CommitConstraint must raise - item_count is 0 after the (only) flush settles.
        """
        session = self.session
        new_order = models.Order(id=3, notes='Order 3 - no items')
        session.add(new_order)

        with self.assertRaises(ConstraintException) as context:
            session.commit()
        assert 'must have at least one item' in str(context.exception), \
            f'Expected min-cardinality error, got: {context.exception}'

        print("\n...test_insert_order_without_items_raises ran to completion\n\n")

    def test_delete_last_item_raises(self):
        """ Case 3: Order 2 (gold seed data) has exactly 1 OrderDetail. Delete it ->
        item_count drops to 0 -> CommitConstraint must raise on commit.
        """
        session = self.session
        last_detail = session.query(models.OrderDetail).filter(models.OrderDetail.id == 3).one()
        session.delete(last_detail)

        with self.assertRaises(ConstraintException) as context:
            session.commit()
        assert 'must have at least one item' in str(context.exception), \
            f'Expected min-cardinality error, got: {context.exception}'

        print("\n...test_delete_last_item_raises ran to completion\n\n")

    def test_delete_one_of_two_items_does_not_raise(self):
        """ Case 3 variant: Order 1 has 2 OrderDetails. Deleting ONE leaves item_count=1 -
        CommitConstraint must NOT raise (still satisfies >0).
        """
        session = self.session
        one_detail = session.query(models.OrderDetail).filter(models.OrderDetail.id == 1).one()
        session.delete(one_detail)
        session.commit()  # must NOT raise

        order1 = session.query(models.Order).filter(models.Order.id == 1).one()
        assert order1.item_count == 1, f'Expected Order 1 item_count=1, got {order1.item_count}'

        print("\n...test_delete_one_of_two_items_does_not_raise ran to completion\n\n")

    def test_delete_order_does_not_raise(self):
        """ Deleting an Order (cascade-deletes its OrderDetails) must NOT trigger
        CommitConstraint on the now-gone Order - listeners.py's after_flush loop skips
        rows whose ins_upd_dlt is "dlt".
        """
        session = self.session
        order2 = session.query(models.Order).filter(models.Order.id == 2).one()
        session.delete(order2)
        session.commit()  # must NOT raise

        remaining = session.query(models.Order).filter(models.Order.id == 2).all()
        assert remaining == [], f'Expected Order 2 to be deleted, got {remaining}'

        print("\n...test_delete_order_does_not_raise ran to completion\n\n")
