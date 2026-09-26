import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.formula_no_python_type.tests.test_formula_no_python_type")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.formula_no_python_type.db.models import Item

    print("\n" + sys_env_info + "\n\n")


def is_active(row, old_row=None, logic_row=None):
    """Active while the code starts with A"""
    code = row.code
    return bool(code) and code.startswith('A')


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #32
    (https://github.com/valhuber/LogicBank/issues/32): Formula.execute
    (rule_type/formula.py) read `mapper.columns[self._column].type.python_type`
    unconditionally whenever the derived value did not change, to detect a
    stray float that should be reset to the column's real type. `python_type`
    raises NotImplementedError for column types that don't implement it (e.g.
    MySQL BIT) - so recomputing such a column to the value it already had
    crashed the flush instead of being a no-op.

    Fixed by moving the type inspection inside the 'is the old value a float'
    guard, so it only runs when it's actually needed. See
    system/LogicBank-Internal-Dev/formula-no-python-type-issue-32.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        self.engine.dialect.supports_native_bit = True  # mysql.BIT's result_processor checks this
        # BIT has no sqlite compiler (visit_BIT) - create the table with raw DDL,
        # storing the bit as an INTEGER, rather than Base.metadata.create_all().
        # Only the mapped column's Python type (BIT, no python_type) matters here.
        with self.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                'CREATE TABLE item ("id" INTEGER PRIMARY KEY, "code" TEXT, "is_active" INTEGER)'))

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.formula(derive=Item.is_active, calling=is_active)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_insert_sets_derived_value(self):
        session = self._activate()

        item = Item(code='A1')
        session.add(item)
        session.commit()
        session.refresh(item)
        self.assertEqual(item.is_active, 1, "Expected is_active derived True on insert")

        print("\n...test_insert_sets_derived_value ran to completion\n\n")

    def test_update_with_unchanged_derived_value_does_not_raise(self):
        """
        The actual regression: code changes from A1 to A2, a dependency of the
        formula, but the derived value stays True. Previously this crashed
        commit() with NotImplementedError instead of being a silent no-op.
        """
        session = self._activate()

        item = Item(code='A1')
        session.add(item)
        session.commit()
        session.refresh(item)  # otherwise 'code' is expired and its old value is lost,
                                # which is a different reason the formula would not see it change

        item.code = 'A2'
        session.commit()  # previously: NotImplementedError
        session.refresh(item)
        self.assertEqual(item.is_active, 1,
                         "Expected is_active to stay derived True after update")

        print("\n...test_update_with_unchanged_derived_value_does_not_raise ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
