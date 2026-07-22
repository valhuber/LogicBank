"""
Builds examples/passive_delete_cascade/db/database-gold.db from scratch, WITH
LogicBank rules active during seeding - so amount_total is correctly derived
and baked into the gold copy, rather than left at column defaults.

Run from repo root:
    venv/bin/python examples/passive_delete_cascade/db/create_db.py
"""
import os
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import LogicBank

import logic_bank_utils.util as logic_bank_utils
(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from examples.passive_delete_cascade.db.models import Order, OrderDetail, Base
from examples.passive_delete_cascade.logic.rules_bank import declare_logic

basedir = os.path.abspath(os.path.dirname(__file__))
db_loc = os.path.join(basedir, "database-gold.db")
if os.path.exists(db_loc):
    os.remove(db_loc)

engine = sqlalchemy.create_engine("sqlite:///" + db_loc)

@event.listens_for(engine, "connect")
def _enable_sqlite_fk_cascade(dbapi_connection, connection_record):
    """ SQLite ignores FK constraints (incl. ON DELETE CASCADE) unless enabled
    per-connection - required for passive_deletes=True to actually work. """
    dbapi_connection.execute("PRAGMA foreign_keys=ON")

Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

LogicBank.activate(session=session, activator=declare_logic, aggregate_defaults=True, all_defaults=False)

order1 = Order(id=1)
order1.OrderDetailList.append(OrderDetail(id=1, amount=10))
order1.OrderDetailList.append(OrderDetail(id=2, amount=5))

order2 = Order(id=2)
order2.OrderDetailList.append(OrderDetail(id=3, amount=7))

session.add_all([order1, order2])
session.commit()

print("\ngold db created with seed data, rules active during seeding\n")

order1 = session.get(Order, 1)
order2 = session.get(Order, 2)
print(f"Order 1: amount_total={order1.amount_total}")
print(f"Order 2: amount_total={order2.amount_total}")

session.close()
engine.dispose()
