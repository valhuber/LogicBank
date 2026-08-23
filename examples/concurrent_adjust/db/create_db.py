"""
Builds examples/concurrent_adjust/db/database-gold.db from scratch, WITH LogicBank
rules active during seeding - so derived columns (Sum) are correctly computed and
baked into the gold copy, rather than left at column defaults.

Run from repo root:
    venv/bin/python examples/concurrent_adjust/db/create_db.py
"""
import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import LogicBank

import logic_bank_utils.util as logic_bank_utils
(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from examples.concurrent_adjust.db.models import Customer, Order, Base
from examples.concurrent_adjust.logic.rules_bank import declare_logic

basedir = os.path.abspath(os.path.dirname(__file__))
db_loc = os.path.join(basedir, "database-gold.db")
if os.path.exists(db_loc):
    os.remove(db_loc)

engine = sqlalchemy.create_engine("sqlite:///" + db_loc)
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

LogicBank.activate(session=session, activator=declare_logic)

# ALFKI-style seed: balance=900, credit_limit=1000, matching locking_strategy.md Section 3
session.add_all([
    Customer(id=1, name='ALFKI', credit_limit=1000),
])
session.commit()

session.add_all([
    Order(id=1, customer_id=1, amount_total=900, date_shipped=None),
])
session.commit()

print("\ngold db created with seed data, rules active during seeding\n")

cust = session.get(Customer, 1)
print(f"ALFKI: balance={cust.balance} credit_limit={cust.credit_limit}")

session.close()
engine.dispose()
