import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.cascade_delete_multi_parent.tests.test_cascade_delete_multi_parent")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from decimal import Decimal
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.cascade_delete_multi_parent.db.models import Product, Order, OrderLine, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #38
    (https://github.com/valhuber/LogicBank/issues/38): deleting a child can
    skip its parent's sum adjustment, or raise AttributeError.

    LogicRow._is_in_list compared the primary key columns of a row with those
    of every row in a do_not_adjust_list, without checking that they belong to
    the same table:

        for each_column in meta.primary_key.columns:
            col_name = each_column.name
            if getattr(self.row, col_name) != getattr(each_logic_row.row, col_name):

    adjust_from_deleted_child calls this on the parent to adjust, passing the
    delete's do_not_adjust_list. Two paths put rows of OTHER tables in that
    list: before_flush appends every client-deleted row of the flush, and
    _cascade_delete_children passes [self] to a child that may sum into a
    parent of another table. Here, deleting an Order cascades to OrderLine,
    which also sums into Product - a different table, with a different
    primary-key column name (id_product vs id_order). getattr(<Order
    instance>, "id_product") then raises AttributeError. With MATCHING column
    names (both "id", as in the issue's own repro and the original #8 `nw`
    dataset) nothing is raised, but the parent is silently treated as "in the
    list" whenever the ids happen to be equal, and its adjustment is skipped.

    Fixed: _is_in_list now skips any row whose table_meta is not the same
    table before comparing primary-key columns.

    See system/LogicBank-Internal-Dev/cascade-delete-is-in-list-issue-38.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.sum(derive=Order.qty_total, as_sum_of=OrderLine.qty)
            Rule.sum(derive=Product.qty_sold, as_sum_of=OrderLine.qty)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_cascade_delete_adjusts_unrelated_parent_table(self):
        """
        Deleting an Order cascades to OrderLine (cascade="all, delete",
        passive_deletes=True). The line also sums into Product - a table
        unrelated to the cascade. Product.qty_sold must be decremented, and
        no AttributeError should be raised even though Order and Product have
        different primary-key column names.
        """
        session = self._activate()

        session.add_all([Product(id_product=1), Order(id_order=1)])
        session.commit()
        session.add(OrderLine(id_line=1, id_order=1, id_product=1, qty=Decimal("3")))
        session.commit()

        product = session.query(Product).filter(Product.id_product == 1).one()
        self.assertEqual(product.qty_sold, Decimal("3"), "Expected qty_sold set from insert")

        session.delete(session.query(Order).filter(Order.id_order == 1).one())
        session.commit()  # previously: AttributeError: 'Order' object has no attribute 'id_product'

        product = session.query(Product).filter(Product.id_product == 1).one()
        self.assertEqual(product.qty_sold, Decimal("0"),
                         "Expected qty_sold decremented by the cascade-deleted line")
        self.assertEqual(session.query(OrderLine).count(), 0, "Expected line cascade-deleted")

        print("\n...test_cascade_delete_adjusts_unrelated_parent_table ran to completion\n\n")

    def test_non_cascade_delete_of_another_row_does_not_block_adjustment(self):
        """
        Same failure shape without the cascade: before_flush's do_not_adjust
        list is built from every client-deleted row in the flush. Deleting
        another Order in the same commit as deleting an OrderLine must not
        prevent the line's own parents from being adjusted.
        """
        session = self._activate()

        session.add_all([Product(id_product=1), Order(id_order=1), Order(id_order=2)])
        session.commit()
        session.add(OrderLine(id_line=1, id_order=1, id_product=1, qty=Decimal("3")))
        session.commit()

        session.delete(session.query(Order).filter(Order.id_order == 2).one())  # unrelated
        session.delete(session.query(OrderLine).filter(OrderLine.id_line == 1).one())
        session.commit()

        product = session.query(Product).filter(Product.id_product == 1).one()
        order = session.query(Order).filter(Order.id_order == 1).one()
        self.assertEqual(product.qty_sold, Decimal("0"), "Expected qty_sold decremented")
        self.assertEqual(order.qty_total, Decimal("0"), "Expected qty_total decremented")

        print("\n...test_non_cascade_delete_of_another_row_does_not_block_adjustment ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
