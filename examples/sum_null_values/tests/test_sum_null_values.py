import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.sum_null_values.tests.test_sum_null_values")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from decimal import Decimal
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.sum_null_values.db.models import Customer, Order, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #39
    (https://github.com/valhuber/LogicBank/issues/39): Rule.sum raises
    TypeError on NULL summed-column values, except on insert.

    Aggregate.adjust_from_inserted_child already normalized a NULL summed
    child value, and a NULL parent sum, to 0. The other paths did this only in
    part, and subtracted/added None where they didn't:
      - adjust_from_deleted_child: neither the child's value nor the parent's
        sum - `curr_value - delta` raised when delta (the child's NULL amount)
        was None.
      - adjust_from_updated_child: normalized the OLD value but not the new
        one - setting a non-NULL amount to NULL raised (delta = new - old,
        new was None).
      - adjust_from_updated_reparented_child: normalized on the new parent
        side, not on the previous-parent side - reparenting a child with a
        NULL amount raised on the `curr_value - delta` decrement of the old
        parent.
    So a row accepted on insert (NULL amount) could not be deleted, cleared,
    or moved to another parent, without a TypeError. This is the same
    normalization gap class as #27/#31/#34: an aggregate path assumed a value
    that a sibling path already knew could be missing.

    Fixed: the same `if x is None: x = 0` normalization insert already applied
    is now applied consistently across delete, update and reparent, for both
    the child's summed value and the parent's current sum.

    See system/LogicBank-Internal-Dev/sum-null-values-issue-39.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.sum(derive=Customer.balance, as_sum_of=Order.amount)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_insert_null_amount_baseline(self):
        """ Baseline (already worked pre-fix): insert with a NULL summed value. """
        session = self._activate()
        session.add(Customer(id=1))
        session.commit()
        session.add(Order(id=1, customer_id=1, amount=None))
        session.commit()

        customer = session.query(Customer).filter(Customer.id == 1).one()
        self.assertEqual(customer.balance, Decimal("0"), "Expected NULL amount summed as 0")

        print("\n...test_insert_null_amount_baseline ran to completion\n\n")

    def test_delete_child_with_null_amount(self):
        """ Deleting a child whose summed value is NULL must not raise. """
        session = self._activate()
        session.add(Customer(id=1))
        session.commit()
        session.add(Order(id=1, customer_id=1, amount=None))
        session.commit()

        session.delete(session.query(Order).filter(Order.id == 1).one())
        session.commit()  # previously: TypeError: unsupported operand type(s) for -: 'Decimal' and 'NoneType'

        customer = session.query(Customer).filter(Customer.id == 1).one()
        self.assertEqual(customer.balance, Decimal("0"))

        print("\n...test_delete_child_with_null_amount ran to completion\n\n")

    def test_update_amount_to_null(self):
        """ Updating a non-NULL summed value to NULL must not raise. """
        session = self._activate()
        session.add(Customer(id=1))
        session.commit()
        session.add(Order(id=1, customer_id=1, amount=Decimal("5")))
        session.commit()

        order = session.query(Order).filter(Order.id == 1).one()
        order.amount = None
        session.commit()  # previously: TypeError: unsupported operand type(s) for -: 'NoneType' and 'Decimal'

        customer = session.query(Customer).filter(Customer.id == 1).one()
        self.assertEqual(customer.balance, Decimal("0"))

        print("\n...test_update_amount_to_null ran to completion\n\n")

    def test_reparent_child_with_null_amount(self):
        """ Reparenting a child whose summed value is NULL must not raise. """
        session = self._activate()
        session.add_all([Customer(id=1), Customer(id=2)])
        session.commit()
        session.add(Order(id=1, customer_id=1, amount=None))
        session.commit()

        order = session.query(Order).filter(Order.id == 1).one()
        order.customer_id = 2
        session.commit()  # previously: TypeError: unsupported operand type(s) for -: 'Decimal' and 'NoneType'

        cust1 = session.query(Customer).filter(Customer.id == 1).one()
        cust2 = session.query(Customer).filter(Customer.id == 2).one()
        self.assertEqual(cust1.balance, Decimal("0"))
        self.assertEqual(cust2.balance, Decimal("0"))

        print("\n...test_reparent_child_with_null_amount ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
