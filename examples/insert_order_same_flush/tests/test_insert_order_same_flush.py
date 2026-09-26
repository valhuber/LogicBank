import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.insert_order_same_flush.tests.test_insert_order_same_flush")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from logic_bank.exec_trans_logic.row_sets import RowSets
    from examples.insert_order_same_flush.db.models import Order, OrderDetail, Base

    print("\n" + sys_env_info + "\n\n")


def order_apply_tax(row, old_row=None, logic_row=None):
    """Fixed for this suite - only here to give Order a formula to race against"""
    return 1


def detail_apply_tax(row, old_row=None, logic_row=None):
    """Copy of the parent's computed apply_tax"""
    return row.Order.apply_tax


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #35
    (https://github.com/valhuber/LogicBank/issues/35): before_flush processed
    inserts by iterating `RowSets.client_inserts`, which was a plain `set()` -
    so rows were visited in hash order, not in the order they were added
    (unlike `a_session.new`, which does preserve that order). When a parent and
    its child are inserted in the same flush, the child could be processed
    before the parent, and a child formula reading a derived parent column
    (row.Order.apply_tax) would read it before the parent's own formula had
    run - with nothing to recompute the child afterwards, and no error.

    Fixed by making `client_inserts` a dict (insertion-ordered) instead of a
    set - same membership semantics, deterministic order. See
    system/LogicBank-Internal-Dev/insert-order-same-flush-issue-35.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.formula(derive=Order.apply_tax, calling=order_apply_tax)
            Rule.formula(derive=OrderDetail.apply_tax, calling=detail_apply_tax)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_client_inserts_preserves_insertion_order(self):
        """
        Direct test of the mechanism: RowSets.client_inserts must iterate in
        the order rows were added, not hash order. A plain set() of several
        distinct object instances does not reliably do this; a dict always
        does - this is what the fix relies on, independent of any particular
        flush's hash-order luck.
        """
        row_sets = RowSets()
        added = [object() for _ in range(10)]
        for each_row in added:
            row_sets.add_client_inserts(each_row)

        self.assertEqual(list(row_sets.client_inserts), added,
                         "Expected client_inserts to iterate in insertion order")

        print("\n...test_client_inserts_preserves_insertion_order ran to completion\n\n")

    def test_child_formula_sees_parent_value_in_same_flush(self):
        """
        The functional scenario from the issue: Order and OrderDetail are
        both new and committed together. The detail's formula must observe
        the order's computed apply_tax, not run before it.
        """
        session = self._activate()

        order = Order(id=1)
        detail = OrderDetail(id=1, order_id=1, Order=order)
        session.add(order)
        session.add(detail)
        session.commit()  # previously: detail.apply_tax could stay None

        session.refresh(order)
        session.refresh(detail)
        self.assertEqual(order.apply_tax, 1, "Expected order.apply_tax derived")
        self.assertEqual(detail.apply_tax, 1,
                         "Expected detail.apply_tax copied from the parent computed "
                         "in the same flush")

        print("\n...test_child_formula_sees_parent_value_in_same_flush ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
