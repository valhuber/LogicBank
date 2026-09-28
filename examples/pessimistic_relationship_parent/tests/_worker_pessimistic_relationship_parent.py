"""
Worker process for test_pessimistic_relationship_parent.py - run in its own
process per trans_update_locking mode, since RuleBank is a process-wide
singleton and a second LogicBank.activate() in the same process would reuse
the first activation's state.

Usage: python _worker_pessimistic_relationship_parent.py <ignored|pessimistic>
Prints "ok" and exits 0 on success; prints details and exits 1 on failure.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from decimal import Decimal

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import Rule, LogicBank
from examples.pessimistic_relationship_parent.db.models import Customer, Order, Base


def main():
    mode = sys.argv[1]

    engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def declare_logic():
        Rule.sum(derive=Customer.balance, as_sum_of=Order.amount)

    LogicBank.activate(session=Session, activator=declare_logic, trans_update_locking=mode)

    session = Session()
    session.add(Customer(id=1))
    session.commit()

    # Link through the relationship (not the FK column) to an EXISTING, already
    # persistent Customer - before the flush, SQLAlchemy has not yet copied the
    # parent's key into the child's FK column.
    customer = session.query(Customer).filter(Customer.id == 1).one()
    session.add(Order(id=1, customer=customer, amount=Decimal("3")))
    session.commit()

    order = session.query(Order).filter(Order.id == 1).one()
    customer = session.query(Customer).filter(Customer.id == 1).one()

    failures = []
    if order.customer_id != 1:
        failures.append(f"Order(1).customer_id = {order.customer_id}, expected 1 (FK wiped)")
    if customer.balance != Decimal("3"):
        failures.append(f"Customer(1).balance = {customer.balance}, expected 3 (adjustment skipped)")

    if failures:
        print(f"{mode}: WRONG - " + "; ".join(failures))
        sys.exit(1)
    print(f"{mode}: ok")
    sys.exit(0)


if __name__ == "__main__":
    main()
