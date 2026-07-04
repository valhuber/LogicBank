"""
Regression test for: AfterFlushRowEvent.if_condition / when_condition were never evaluated.

Bug report: logic_bank/rule_type/row_event.py's AfterFlushRowEvent.__init__ did
`self.if_condition = lambda row: eval(if_condition)` (tries to eval() a lambda object -
broken even to construct), and .execute()'s branching
(`if self.if_condition is not None and self.when_condition is not None: pass`)
meant if_condition was never actually called - the handler always fired,
regardless of if_condition's value. Traced from a GenAI-Logic basic_demo project
where a Kafka-publish-on-ship rule fired on every Order insert/update instead of
only when date_shipped was set.

This test declares 3 after_flush_row_event rules on the same class - no condition,
if_condition, and when_condition - and asserts each fires (or doesn't) as documented.
"""
from datetime import datetime
import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from logic_bank.logic_bank import LogicBank
from logic_bank.util import row_prt, prt

import examples.after_flush_row_event.db.models as models


def copy_db_from_gold():
    """ copy db/database-gold.db over db/database.db"""
    print("\n" + prt("restoring database-gold\n"))

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    db_loc = os.path.join(basedir, "db/database.db")
    db_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=db_source, dst=db_loc)


def setup_logging():
    logic_logger = logging.getLogger('logic_logger')
    logic_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    logic_logger.addHandler(handler)


setup_logging()
copy_db_from_gold()

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

db_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + db_loc
engine = sqlalchemy.create_engine(conn_string, echo=False)

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

from examples.after_flush_row_event.logic import rules_bank
from examples.after_flush_row_event.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)

trans_date = datetime(2020, 10, 1)

"""
    ********* Test 1 - Insert Order, not shipped *********
    if_condition (date_shipped is not None) is False -> notify_if_shipped must NOT fire
    when_condition (date_shipped is not None) is False, was False -> notify_when_shipped must NOT fire
    unconditional handler must fire regardless
"""
print("\n\nTest 1 - Insert Order, not shipped")
order = models.Order(id=2, amount_total=50, date_shipped=None, notes="new order")
session.add(order)
session.commit()

assert 2 in rules_bank.no_condition_fired_for, \
    "Unconditional after_flush handler must fire on insert regardless of condition"
assert 2 not in rules_bank.if_condition_fired_for, \
    "if_condition=False must suppress the handler - BUG: if_condition was never evaluated"
assert 2 not in rules_bank.when_condition_fired_for, \
    "when_condition False->False must suppress the handler"
print(prt("Test 1 - Insert Order, not shipped -- passes"))

"""
    ********* Test 2 - Ship the order (date_shipped set) *********
    if_condition becomes True -> notify_if_shipped must fire
    when_condition transitions False->True -> notify_when_shipped must fire
"""
print("\n\nTest 2 - Ship the order (set date_shipped)")
order_to_ship = session.query(models.Order).filter(models.Order.id == 2).one()
order_to_ship.date_shipped = trans_date
session.commit()

assert 2 in rules_bank.if_condition_fired_for, \
    "if_condition=True must fire the handler once date_shipped is set - BUG being tested"
assert rules_bank.if_condition_fired_for.count(2) == 1, "if_condition handler should have fired exactly once so far"
assert 2 in rules_bank.when_condition_fired_for, \
    "when_condition False->True transition must fire the handler"
assert rules_bank.when_condition_fired_for.count(2) == 1, "when_condition handler should have fired exactly once so far"
print(prt("Test 2 - Ship the order -- passes"))

"""
    ********* Test 3 - Update shipped order again (date_shipped stays set) *********
    if_condition remains True -> notify_if_shipped fires again (level-triggered)
    when_condition True->True (no transition) -> notify_when_shipped must NOT fire again (edge-triggered)
"""
print("\n\nTest 3 - Update already-shipped order (notes only)")
order_to_update = session.query(models.Order).filter(models.Order.id == 2).one()
order_to_update.notes = "updated after shipping"
session.commit()

assert rules_bank.if_condition_fired_for.count(2) == 2, \
    "if_condition is level-triggered - must re-fire while condition stays True"
assert rules_bank.when_condition_fired_for.count(2) == 1, \
    "when_condition is edge-triggered - must NOT re-fire when condition stays True (no False->True transition)"
print(prt("Test 3 - Update already-shipped order -- passes"))
