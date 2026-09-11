"""
Regression test for a bug found building a real-world sales-rep monthly-rollup sample
(see internal_dev/composite_key_issue/composite_key_issue.md, ApiLogicServer-src): when
a composite-key column is set LATE - by an early_row_event, not at construction time -
Rule.sum/Rule.count's insert_parent=True silently failed to create the parent AND
silently nulled the child's own FK columns, with no error.

Why examples/insert_parent's existing test did not catch this: that test's
Child(parent_1="...", parent_2="...", ...) sets BOTH composite-key columns directly in
the constructor, so the FK is already fully non-null the first time
LogicRow._load_parents_on_insert() runs (before any early_row_events fire) -
insert_parent is handled there, in a single pass, and the bug's code path
(Aggregate.adjust_from_inserted_child, in rule_type/aggregate.py) is never reached
because the parent already exists (or was already created) by the time it runs.

Here, Child.period (part of the composite FK to Parent) is set by an early_row_event -
like a real Order's year_month bucket key, computed from order_date - so it is still
None the first time _load_parents_on_insert() runs. _is_foreign_key_null() correctly
defers insert_parent at that point (nothing to load - the FK is incomplete). The ONLY
code path left to trigger insert_parent is the aggregate adjustment in aggregate.py,
which - before the fix - never called _is_inserted_parent() at all, and separately,
_get_parent_logic_row()/_is_inserted_parent() were nulling the child's real FK values
as a side effect of linking the (not-yet-keyed) new parent object. Both are fixed in
logic_bank/exec_row_logic/logic_row.py and logic_bank/rule_type/aggregate.py.
"""

import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from logic_bank.logic_bank import LogicBank
from logic_bank.util import prt
from logic_bank.exec_row_logic.logic_row import LogicRow

import examples.insert_parent_late_key.db.models as models


def copy_db_from_gold():
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

from examples.insert_parent_late_key.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)


"""
    Test 1 - insert_parent creates the parent AND the child's own FK columns survive,
    even though the composite key's `period` column is set by an early_row_event
    (not known at Child() construction time).
"""
print("\nTest 1 - Insert Parent, late-set composite-key column")

new_child = models.Child(parent_1="rep_1", summed=2, child_key="late_key_child_1")
# note: period is NOT set here - set_period() (early_row_event) sets it before Row Logic runs

session.add(new_child)
session.commit()

assert new_child.parent_1 == "rep_1", \
    "BUG: Child.parent_1 was nulled by insert_parent's parent-linking side effect"
assert new_child.period == "2026-09", \
    "BUG: Child.period was nulled by insert_parent's parent-linking side effect"

new_parent_check = session.query(models.Parent).filter(
    models.Parent.parent_attr_1 == "rep_1", models.Parent.period == "2026-09").one()
assert new_parent_check.child_sum == 2, "Unexpected child_sum - parent not created/adjusted correctly"
assert new_parent_check.child_count == 1, "Unexpected child_count - parent not created/adjusted correctly"

print("\n" + prt("Test 1 - Insert Parent, late-set composite-key column -- passes"))


"""
    Test 2 - a second child for the same (late-set) composite key ADJUSTS the existing
    parent bucket, rather than re-creating it or losing the FK a second time.
"""
print("\nTest 2 - second child, same composite key - adjusts existing parent")

second_child = models.Child(parent_1="rep_1", summed=3, child_key="late_key_child_2")
session.add(second_child)
session.commit()

assert second_child.parent_1 == "rep_1", "BUG: second child's parent_1 was nulled"
assert second_child.period == "2026-09", "BUG: second child's period was nulled"

parent_check_2 = session.query(models.Parent).filter(
    models.Parent.parent_attr_1 == "rep_1", models.Parent.period == "2026-09").one()
assert parent_check_2.child_sum == 5, "Unexpected child_sum after second child - insert_parent re-created instead of adjusting"
assert parent_check_2.child_count == 2, "Unexpected child_count after second child - insert_parent re-created instead of adjusting"

print("\n" + prt("Test 2 - second child, same composite key - adjusts existing parent -- passes"))


"""
    Test 3 - a child under a DIFFERENT late-set key creates a SEPARATE parent bucket.
"""
print("\nTest 3 - different composite key - creates a separate parent bucket")

third_child = models.Child(parent_1="rep_2", summed=7, child_key="late_key_child_3")
session.add(third_child)
session.commit()

assert third_child.parent_1 == "rep_2", "BUG: third child's parent_1 was nulled"
assert third_child.period == "2026-09", "BUG: third child's period was nulled"

parent_check_3 = session.query(models.Parent).filter(
    models.Parent.parent_attr_1 == "rep_2", models.Parent.period == "2026-09").one()
assert parent_check_3.child_sum == 7, "Unexpected child_sum for new rep bucket"
assert parent_check_3.child_count == 1, "Unexpected child_count for new rep bucket"

# rep_1's bucket must be untouched by rep_2's insert
parent_check_1_again = session.query(models.Parent).filter(
    models.Parent.parent_attr_1 == "rep_1", models.Parent.period == "2026-09").one()
assert parent_check_1_again.child_sum == 5, "rep_1 bucket was disturbed by rep_2's insert"
assert parent_check_1_again.child_count == 2, "rep_1 bucket was disturbed by rep_2's insert"

print("\n" + prt("Test 3 - different composite key - creates a separate parent bucket -- passes"))

print("\n" + prt("ALL insert_parent_late_key TESTS PASS"))
