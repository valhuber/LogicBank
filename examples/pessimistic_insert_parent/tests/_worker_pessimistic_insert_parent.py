"""
Worker process for test_pessimistic_insert_parent.py - run in its own process
per trans_update_locking mode, since RuleBank is a process-wide singleton and
a second LogicBank.activate() in the same process would reuse the first
activation's state.

Usage: python _worker_pessimistic_insert_parent.py <ignored|pessimistic>
Prints "ok" and exits 0 on success; prints details and exits 1 on failure.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import Rule, LogicBank
from examples.pessimistic_insert_parent.db.models import Stock, SaleLine, Base


def main():
    mode = sys.argv[1]

    engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def declare_logic():
        Rule.sum(derive=Stock.sold, as_sum_of=SaleLine.qty, insert_parent=True)

    LogicBank.activate(session=Session, activator=declare_logic, trans_update_locking=mode)

    session = Session()
    # No Stock(10) yet - insert_parent must create it, in the SAME transaction
    session.add(SaleLine(id_sale_line=1, product_id=10, qty=3))
    session.commit()

    stock = session.query(Stock).filter(Stock.product_id == 10).one()
    line = session.query(SaleLine).filter(SaleLine.id_sale_line == 1).one()

    failures = []
    if stock.sold != 3:
        failures.append(f"Stock(10).sold = {stock.sold}, expected 3 (insert_parent adjustment lost)")
    if line.product_id != 10:
        failures.append(f"SaleLine.product_id = {line.product_id}, expected 10 (FK wiped)")

    # A second line, now that Stock(10) exists (persistent) - the locking read
    # must still correctly re-fetch and adjust it.
    session.add(SaleLine(id_sale_line=2, product_id=10, qty=2))
    session.commit()
    stock = session.query(Stock).filter(Stock.product_id == 10).one()
    if stock.sold != 5:
        failures.append(f"Stock(10).sold after second line = {stock.sold}, expected 5")

    if failures:
        print(f"{mode}: WRONG - " + "; ".join(failures))
        sys.exit(1)
    print(f"{mode}: ok")
    sys.exit(0)


if __name__ == "__main__":
    main()
