"""
Builds examples/multi_relns/db/database-gold.db from scratch, WITH LogicBank rules
active during seeding - so derived columns (Sum/Count/Formula) are correctly computed
and baked into the gold copy, rather than left at column defaults.

Run from repo root:
    venv/bin/python examples/multi_relns/db/create_db.py
"""
import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from logic_bank.logic_bank import LogicBank

import logic_bank_utils.util as logic_bank_utils
(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from examples.multi_relns.db.models import Department, Employee, Base
from examples.multi_relns.logic.rules_bank import declare_logic

basedir = os.path.abspath(os.path.dirname(__file__))
db_loc = os.path.join(basedir, "database-gold.db")
if os.path.exists(db_loc):
    os.remove(db_loc)

engine = sqlalchemy.create_engine("sqlite:///" + db_loc)
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

LogicBank.activate(session=session, activator=declare_logic, aggregate_defaults=True, all_defaults=False)

session.add_all([
    Department(id=1, name='Sales'),
    Department(id=2, name='Engineering'),
    Department(id=3, name='Marketing'),
])
session.commit()

session.add_all([
    Employee(id=1, name='Alice', salary=1000, works_for_id=1, on_loan_id=2),    # works Sales, on loan to Engineering
    Employee(id=2, name='Bob',   salary=2000, works_for_id=2, on_loan_id=2),    # works AND on loan to Engineering (same dept, both roles)
    Employee(id=3, name='Carol', salary=1500, works_for_id=1, on_loan_id=1),    # works AND on loan to Sales (same dept, both roles)
])
session.commit()

# NOTE: on_loan_id is nullable=True in the model (an employee may have no on-loan assignment),
# but a null parent FK currently crashes the aggregate adjustor outright:
#   AttributeError: 'NoneType' object has no attribute '<column>'
# (logic_bank/rule_type/aggregate.py:100, adjust_from_inserted_child - parent_logic_row.row is None
# when the FK is null, and the adjustor doesn't guard for that). This is a separate, real bug from
# the multi-relationship issue this suite targets - deliberately not exercised here so it doesn't
# mask the issue-#20 symptoms under test. Tracked as a follow-up, not yet filed.

print("\ngold db created with seed data, rules active during seeding\n")

dept1 = session.get(Department, 1)
dept2 = session.get(Department, 2)
dept3 = session.get(Department, 3)
print(f"Sales:       works_for_count={dept1.works_for_count} works_for_salary_total={dept1.works_for_salary_total} "
      f"on_loan_count={dept1.on_loan_count} on_loan_salary_total={dept1.on_loan_salary_total}")
print(f"Engineering: works_for_count={dept2.works_for_count} works_for_salary_total={dept2.works_for_salary_total} "
      f"on_loan_count={dept2.on_loan_count} on_loan_salary_total={dept2.on_loan_salary_total}")
print(f"Marketing:   works_for_count={dept3.works_for_count} works_for_salary_total={dept3.works_for_salary_total} "
      f"on_loan_count={dept3.on_loan_count} on_loan_salary_total={dept3.on_loan_salary_total}")

session.close()
engine.dispose()
