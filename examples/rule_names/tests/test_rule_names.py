"""
Rule names (LogicBank 1.34.06): constraints and events take an optional name=, derivations are named by their column.

Uses the insert_parent models, with its own copy of the database (rule_names/db/).
    Test 1 - every rule type that takes name= (constraint, commit_constraint, the 4 row events), with and without a name;
             defaulted from the function, none for a lambda, <Table>.<column> for derivations; the log text for each
    Test 2 - a duplicate declared name on one table fails activation (LBActivateException)
    Test 3 - default names may repeat (one handler used by two events), and the same declared name on two tables is fine
    Test 4 - behavior unchanged: named and unnamed events all fire; named and unnamed constraints all reject, and the
             failure line names the rule when it has a name
"""
import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils
(did_fix_path, sys_env_info) = logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

from logic_bank.logic_bank import LogicBank, Rule
from logic_bank.exceptions import LBActivateException
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.util import ConstraintException
from logic_bank.rule_type.constraint import AbstractConstraint
from logic_bank.rule_type.row_event import AbstractRowEvent
from logic_bank.rule_type.derivation import Derivation

import examples.insert_parent.db.models as models

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_loc = os.path.join(basedir, "db/database.db")
copyfile(src=os.path.join(basedir, "db/database-gold.db"), dst=db_loc)


def new_session():
    engine = sqlalchemy.create_engine("sqlite:///" + db_loc, echo=False)
    session_maker = sqlalchemy.orm.sessionmaker()
    session_maker.configure(bind=engine)
    return session_maker()


fired = []

def child_early(row, old_row, logic_row):
    """ Child early event: records that it fired """
    fired.append(("child_early", row.child_key))

def child_row(row, old_row, logic_row):
    """ Child row event: records that it fired """
    fired.append(("child_row", row.child_key))

def child_audit(row, old_row, logic_row):
    """ Child commit event: records that it fired """
    fired.append(("child_audit", row.child_key))

def child_after_flush(row, old_row, logic_row):
    """ Child after-flush event: records that it fired """
    fired.append(("child_after_flush", row.child_key))

def child_key_ok(row, old_row, logic_row):
    """ Child constraint: the key is not 'bad' """
    return row.child_key != "bad"


class LogCapture(logging.Handler):
    """ collects the logic log, to check what it says about named and unnamed rules """
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []
    def emit(self, record):
        self.lines.append(record.getMessage())

log_capture = LogCapture()
logic_logger = logging.getLogger('logic_logger')
logic_logger.setLevel(logging.DEBUG)
logic_logger.addHandler(log_capture)


def names_by_type():
    rules = RuleBank().get_all_rules()
    return {"constraints": sorted(str(r.get_name()) for r in rules if isinstance(r, AbstractConstraint)),
            "events": sorted(str(r.get_name()) for r in rules if isinstance(r, AbstractRowEvent)),
            "derivations": sorted(str(r.get_name()) for r in rules if isinstance(r, Derivation))}


"""
    Test 1 - names: every rule type that takes name=, with and without it
"""
def declare_logic():
    # constraints: declared / lambda without a name / function without a name (defaults to the function name)
    Rule.constraint(validate=models.Parent, as_condition=lambda row: row.parent_attr_1 != "hello",
                    error_msg="no hello", name="no_hello")
    Rule.constraint(validate=models.Child, as_condition=lambda row: (row.summed or 0) >= 0,
                    error_msg="negative")
    Rule.constraint(validate=models.Child, calling=child_key_ok, error_msg="bad key")
    # commit constraints: declared / lambda without a name
    Rule.commit_constraint(validate=models.Child, as_condition=lambda row: (row.summed or 0) <= 1000,
                           error_msg="too big", name="max_summed")
    Rule.commit_constraint(validate=models.Parent, as_condition=lambda row: (row.child_count or 0) >= 0,
                           error_msg="count below zero")
    # events, all four types: declared / defaulted
    Rule.early_row_event(on_class=models.Child, calling=child_early, name="stamp_child")
    Rule.row_event(on_class=models.Child, calling=child_row)
    Rule.commit_row_event(on_class=models.Child, calling=child_audit)
    Rule.after_flush_row_event(on_class=models.Child, calling=child_after_flush, name="child_flushed")
    # derivations: named by their column
    Rule.sum(derive=models.Parent.child_sum, as_sum_of=models.Child.summed, insert_parent=True)
    Rule.count(derive=models.Parent.child_count, as_count_of=models.Child, insert_parent=True)

session = new_session()
LogicBank.activate(session=session, activator=declare_logic)
names = names_by_type()
print("Test 1 names:", names)
assert names["constraints"] == ["Child.child_key_ok", "Child.max_summed", "None", "None", "Parent.no_hello"], names
assert names["events"] == ["Child.child_audit", "Child.child_flushed", "Child.child_row", "Child.stamp_child"], names
assert names["derivations"] == ["Parent.child_count", "Parent.child_sum"], names
texts = {str(r).strip() for r in RuleBank().get_all_rules()}
for expected in ["Constraint Parent.no_hello",                                  # declared: the name
                 "Constraint Child.child_key_ok Function: child_key_ok",       # defaulted from the function
                 "Constraint Function: None",                                  # lambda, no name: as before
                 "CommitConstraint Child.max_summed",
                 "RowEvent Child.child_early() name: stamp_child",            # declared name differs: shown
                 "RowEvent Child.child_row()",                                 # defaulted name: nothing added
                 "RowEvent Child.child_audit()",
                 "RowEvent Child.child_after_flush() name: child_flushed"]:
    assert expected in texts, (expected, texts)
print("Test 1 passed - every rule type with and without a name, and the log text for each")

"""
    Test 4 - behavior unchanged, named and unnamed rules both run; failures name the rule when it has a name
"""
session.add(models.Child(parent_1="named", parent_2="rules", summed=3, child_key="rn1"))
session.commit()
for event in ["child_early", "child_row", "child_audit", "child_after_flush"]:
    assert (event, "rn1") in fired, (event, fired)
parent = session.query(models.Parent).filter(models.Parent.parent_attr_1 == "named").one()
assert parent.child_sum == 3 and parent.child_count == 1, (parent.child_sum, parent.child_count)

def expect_rejection(row, message: str, log_text: str):
    """ commit row, expect a ConstraintException with message, and log_text in the logic log """
    log_capture.lines.clear()
    try:
        session.add(row)
        session.commit()
        assert False, f"Test 4 failed: expected rejection '{message}'"
    except ConstraintException as ce:
        session.rollback()
        assert message in str(ce), str(ce)
    assert any(log_text in line for line in log_capture.lines), (log_text, log_capture.lines[-5:])

expect_rejection(models.Parent(parent_attr_1="hello", parent_attr_2="x"),
                 "no hello", "Constraint Failure (Parent.no_hello): no hello")             # declared name
expect_rejection(models.Child(parent_1="named", parent_2="rules", summed=-1, child_key="rn2"),
                 "negative", "Constraint Failure: negative")                               # lambda, no name
expect_rejection(models.Child(parent_1="named", parent_2="rules", summed=1, child_key="bad"),
                 "bad key", "Constraint Failure (Child.child_key_ok): bad key")           # defaulted name
expect_rejection(models.Child(parent_1="named", parent_2="rules", summed=5000, child_key="rn3"),
                 "too big", "CommitConstraint Failure (Child.max_summed): too big")       # commit constraint
print("Test 4 passed - named and unnamed rules behave as before; failures name the rule when it has one")
session.close()

"""
    Test 2 - duplicate declared name on one table
"""
def declare_duplicate():
    Rule.constraint(validate=models.Parent, as_condition=lambda row: True, error_msg="a", name="same")
    Rule.commit_row_event(on_class=models.Parent, calling=child_audit, name="same")

try:
    LogicBank.activate(session=new_session(), activator=declare_duplicate)
    assert False, "Test 2 failed: duplicate name was accepted"
except LBActivateException as e:
    assert "Duplicate rule name: Parent.same" in str(e.invalid_rules), e.invalid_rules
print("Test 2 passed - duplicate declared name fails activation")

"""
    Test 3 - repeated default names, and one declared name on two tables
"""
def declare_repeats():
    Rule.after_flush_row_event(on_class=models.Child, calling=child_after_flush, with_args={"topic": "a"})
    Rule.after_flush_row_event(on_class=models.Child, calling=child_after_flush, with_args={"topic": "b"})
    Rule.constraint(validate=models.Parent, as_condition=lambda row: True, error_msg="p", name="always")
    Rule.constraint(validate=models.Child, as_condition=lambda row: True, error_msg="c", name="always")

LogicBank.activate(session=new_session(), activator=declare_repeats)
names = names_by_type()
assert names["events"] == ["Child.child_after_flush", "Child.child_after_flush"], names
assert names["constraints"] == ["Child.always", "Parent.always"], names
print("Test 3 passed - default names may repeat; declared names are per table")

print("\nrule_names: all tests passed\n")
