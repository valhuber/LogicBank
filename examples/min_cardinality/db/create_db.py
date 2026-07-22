"""
Builds examples/min_cardinality/db/database-gold.db from scratch, WITH
LogicBank rules active during seeding - so item_count is correctly derived
and baked into the gold copy, rather than left at column defaults.

Run from repo root:
    venv/bin/python examples/min_cardinality/db/create_db.py
"""
import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import LogicBank

import logic_bank_utils.util as logic_bank_utils
(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from examples.min_cardinality.db.models import Order, OrderDetail, Base
from examples.min_cardinality.logic.rules_bank import declare_logic

basedir = os.path.abspath(os.path.dirname(__file__))
db_loc = os.path.join(basedir, "database-gold.db")
if os.path.exists(db_loc):
    os.remove(db_loc)

engine = sqlalchemy.create_engine("sqlite:///" + db_loc)
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

LogicBank.activate(session=session, activator=declare_logic, aggregate_defaults=True, all_defaults=False)

# every seeded Order has >=1 OrderDetail in the SAME commit, proving
# CommitConstraint accepts the case a plain Constraint would reject
order1 = Order(id=1, notes='Order 1')
order1.OrderDetailList.append(OrderDetail(id=1, product_name='Widget'))
order1.OrderDetailList.append(OrderDetail(id=2, product_name='Gadget'))

order2 = Order(id=2, notes='Order 2')
order2.OrderDetailList.append(OrderDetail(id=3, product_name='Gizmo'))

session.add_all([order1, order2])
session.commit()

print("\ngold db created with seed data, rules active during seeding\n")

order1 = session.get(Order, 1)
order2 = session.get(Order, 2)
print(f"Order 1: item_count={order1.item_count}")
print(f"Order 2: item_count={order2.item_count}")

session.close()
engine.dispose()
