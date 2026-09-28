"""
Worker process for test_pessimistic_multi_child_adjust.py - run in its own
process per trans_update_locking mode, since RuleBank is a process-wide
singleton and a second LogicBank.activate() in the same process would reuse
the first activation's state.

Usage: python _worker_pessimistic_multi_child_adjust.py <ignored|pessimistic>
Prints "ok" and exits 0 on success; prints details and exits 1 on failure.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from decimal import Decimal

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import Rule, LogicBank
from examples.pessimistic_multi_child_adjust.db.models import Customer, Order, Base


def main():
    mode = sys.argv[1]

    engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def declare_logic():
        Rule.sum(derive=Customer.balance, as_sum_of=Order.amount)

    LogicBank.activate(session=Session, activator=declare_logic, trans_update_locking=mode)

    session = Session()
    session.add(Customer(id=1, name=1))
    session.commit()

    # Two orders for the same customer, in the SAME flush - the second child's
    # locking read on Customer must not discard the first child's adjustment.
    session.add(Order(id=1, customer_id=1, amount=Decimal("3")))
    session.add(Order(id=2, customer_id=1, amount=Decimal("5")))
    session.commit()

    customer = session.query(Customer).filter(Customer.id == 1).one()

    failures = []
    if customer.balance != Decimal("8"):
        failures.append(f"Customer(1).balance = {customer.balance}, expected 8 (adjustment lost)")

    # A client-side edit to the parent, made in the SAME transaction as a new
    # child - the locking read must not discard it either.
    customer.name = 99
    session.add(Order(id=3, customer_id=1, amount=Decimal("2")))
    session.commit()
    customer = session.query(Customer).filter(Customer.id == 1).one()
    if customer.balance != Decimal("10"):
        failures.append(f"Customer(1).balance after 3rd order = {customer.balance}, expected 10")
    if customer.name != 99:
        failures.append(f"Customer(1).name = {customer.name}, expected 99 (client edit lost)")

    if failures:
        print(f"{mode}: WRONG - " + "; ".join(failures))
        sys.exit(1)
    print(f"{mode}: ok")
    sys.exit(0)


if __name__ == "__main__":
    main()
