import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.passive_delete_cascade.tests.test_passive_delete_cascade")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    from examples.passive_delete_cascade import tests
    import examples.passive_delete_cascade.db.models as models

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #22
    (https://github.com/valhuber/LogicBank/issues/22): LogicRow._cascade_delete_children()
    called LogicRow.delete() with a keyword argument (do_not_adjust=self) that the
    method's signature doesn't accept (do_not_adjust_list=...) - a TypeError on
    every delete of a parent whose child relationship declares BOTH
    cascade="all, delete" AND passive_deletes=True (the DBMS enforces the cascade,
    not SQLAlchemy - this is the only combination that routes through
    _cascade_delete_children() rather than the normal client-delete path).

    Fixed: do_not_adjust=self -> do_not_adjust_list=[self], matching the sibling
    client-delete call site (listeners.py) and _is_in_list()'s List[LogicRow]
    contract. See system/LogicBank-Internal-Dev/passive-delete-cascade-typo.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)
        self.session, self.engine = tests.new_session_from_gold()

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=self.engine, session=self.session)

    def test_gold_seed_data_is_correct(self):
        """ Baseline: gold seed data's amount_total is correctly derived for both orders. """
        session = self.session
        order1 = session.query(models.Order).filter(models.Order.id == 1).one()
        order2 = session.query(models.Order).filter(models.Order.id == 2).one()

        assert order1.amount_total == 15, f'Expected Order 1 amount_total=15, got {order1.amount_total}'
        assert order2.amount_total == 7, f'Expected Order 2 amount_total=7, got {order2.amount_total}'

        print("\n...test_gold_seed_data_is_correct ran to completion\n\n")

    def test_delete_parent_cascades_via_passive_deletes(self):
        """ The exact repro from the issue: delete an Order whose OrderDetailList
        relationship declares cascade="all, delete" + passive_deletes=True.
        Must NOT raise TypeError, and both Order and its OrderDetails must be gone.
        """
        session = self.session
        order1 = session.query(models.Order).filter(models.Order.id == 1).one()
        session.delete(order1)
        session.commit()  # previously: TypeError - unexpected keyword argument 'do_not_adjust'

        remaining_order = session.query(models.Order).filter(models.Order.id == 1).all()
        remaining_details = session.query(models.OrderDetail).filter(models.OrderDetail.order_id == 1).all()
        assert remaining_order == [], f'Expected Order 1 to be deleted, got {remaining_order}'
        assert remaining_details == [], f'Expected Order 1\'s OrderDetails to be cascade-deleted, got {remaining_details}'

        print("\n...test_delete_parent_cascades_via_passive_deletes ran to completion\n\n")

    def test_delete_one_parent_leaves_sibling_order_untouched(self):
        """ Deleting Order 1 must not affect Order 2 (a different parent, own
        OrderDetails, own amount_total) - confirms the cascade delete is scoped
        correctly and the do_not_adjust_list fix doesn't suppress unrelated
        adjustments.
        """
        session = self.session
        order1 = session.query(models.Order).filter(models.Order.id == 1).one()
        session.delete(order1)
        session.commit()

        order2 = session.query(models.Order).filter(models.Order.id == 2).one()
        assert order2.amount_total == 7, f'Expected Order 2 amount_total unchanged at 7, got {order2.amount_total}'
        details2 = session.query(models.OrderDetail).filter(models.OrderDetail.order_id == 2).all()
        assert len(details2) == 1, f'Expected Order 2 to still have 1 OrderDetail, got {len(details2)}'

        print("\n...test_delete_one_parent_leaves_sibling_order_untouched ran to completion\n\n")
