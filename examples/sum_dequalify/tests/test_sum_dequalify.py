import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.sum_dequalify.tests.test_sum_dequalify")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.sum_dequalify.db.models import Order, OrderLine, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #27
    (https://github.com/valhuber/LogicBank/issues/27): Aggregate.adjust_from_updated_child
    (rule_type/aggregate.py), the "no longer meets where - decrement" branch, used
    to decrement the parent by the CHILD'S NEW value (`delta = - summed_field`)
    instead of the value the parent still holds (the OLD one). Whenever the same
    update both dequalifies a child from the `where` clause AND changes the summed
    attribute in the same statement - e.g. a discount column that also feeds the
    summed amount via a formula - the parent total silently drifts, with no error.

    Fixed by decrementing by old_summed_field instead of summed_field. See
    system/LogicBank-Internal-Dev/sum-dequalify-decrement.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.formula(derive=OrderLine.amount,
                        as_expression=lambda row: row.qty * row.price * (100 - row.discount) // 100)
            Rule.sum(derive=Order.undiscounted_total, as_sum_of=OrderLine.amount,
                    where=lambda row: row.discount == 0)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_dequalify_decrements_by_old_value(self):
        """
        insert qty=2 price=100 discount=0  (amount 200)  -> undiscounted_total = 200
        update discount=10                 (amount 180, dequalifies)
            -> must decrement by the OLD amount (200), landing at 0 - not by the
               NEW amount (180), which would wrongly leave 20
        update discount=0                  (amount 200, requalifies)
            -> must increment by the NEW amount (200), landing back at 200
        """
        session = self._activate()

        order = Order(id_order=1)
        session.add(order)
        session.commit()

        line = OrderLine(id_order_line=1, id_order=1, qty=2, price=100, discount=0)
        session.add(line)
        session.commit()
        self.assertEqual(session.get(Order, 1).undiscounted_total, 200,
                         "Insert: expected undiscounted_total = 200")

        session.refresh(line)  # load the row before changing it, as an API update does
        line.discount = 10  # amount becomes 180, line no longer qualifies for the sum
        session.commit()
        self.assertEqual(session.get(Order, 1).undiscounted_total, 0,
                         "Dequalify: expected decrement by OLD amount (200), landing at 0")

        session.refresh(line)
        line.discount = 0  # amount becomes 200 again, line re-qualifies
        session.commit()
        self.assertEqual(session.get(Order, 1).undiscounted_total, 200,
                         "Requalify: expected increment by NEW amount (200), landing at 200")

        print("\n...test_dequalify_decrements_by_old_value ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
