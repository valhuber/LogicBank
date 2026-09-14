import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.insert_parent_partial_null_fk.tests.test_insert_parent_partial_null_fk")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy import func, select
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.insert_parent_partial_null_fk.db.models import Stock, SaleLine, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #29
    (https://github.com/valhuber/LogicBank/issues/29): 1.34.0 regression -
    insert_parent with a partially null composite FK.

    The fix for #26 made Aggregate.adjust_from_inserted_child call
    _is_inserted_parent when no parent is found, on the premise that by then
    the child's FK is complete (set at construction, or by an early_row_event).
    That holds for a LATE-set key (see examples/insert_parent_late_key, #26), but
    not for a key that legitimately stays PARTIALLY NULL forever - e.g. a
    free-text sales line with product_id null and store_id set. Without a guard,
    the parent gets inserted with a null key column and the flush fails:
    "NOT NULL constraint failed: stock.product_id".

    The intended behavior was already documented for this case:
    LogicRow._is_foreign_key_null() treats ANY null column in a composite FK as
    "no parent to load" - insert_parent must never be attempted. The #26 call
    site didn't check it.

    Two fixes were needed together (one alone is insufficient - see the issue):
    1. Aggregate.adjust_from_inserted_child (rule_type/aggregate.py) now also
       checks `not child_logic_row._is_foreign_key_null(relationship)` before
       calling _is_inserted_parent - so a partially-null FK never attempts
       insert_parent.
    2. LogicRow._get_parent_logic_row (exec_row_logic/logic_row.py) now
       short-circuits to a null parent when a composite FK is partially null,
       instead of querying with a None key component (which, before 1.34.0,
       silently returned None then wiped the child's own non-null FK columns
       via the relationship setter's side effect - a separate, older bug).

    See system/LogicBank-Internal-Dev/insert-parent-partial-null-fk.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.sum(derive=Stock.sold, as_sum_of=SaleLine.qty, insert_parent=True)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_full_key_still_inserts_parent(self):
        """ Baseline: a fully-set composite FK still creates the Stock row via insert_parent. """
        session = self._activate()

        session.add(SaleLine(id_sale_line=1, product_id=10, store_id=2, qty=3))
        session.commit()

        stock = session.get(Stock, (10, 2))
        self.assertIsNotNone(stock, "Expected Stock(10, 2) to be inserted via insert_parent")
        self.assertEqual(stock.sold, 3, "Expected Stock(10, 2).sold = 3")

        print("\n...test_full_key_still_inserts_parent ran to completion\n\n")

    def test_partially_null_key_saves_line_without_inserting_parent(self):
        """
        The actual regression: product_id is None (free-text line, no product),
        store_id is set. Must NOT attempt to insert a Stock parent with a null
        product_id (previously: NOT NULL constraint failure), and must NOT wipe
        store_id off the saved line (the pre-1.34.0 shape of this bug).
        """
        session = self._activate()

        session.add(SaleLine(id_sale_line=2, product_id=None, store_id=2, qty=2))
        session.commit()  # previously: IntegrityError (1.34.0) or wiped store_id (1.33.0)

        line = session.get(SaleLine, 2)
        self.assertEqual(line.store_id, 2, "Expected store_id preserved on the saved line")
        self.assertIsNone(line.product_id, "Expected product_id to remain None")

        stock_rows = session.scalar(select(func.count()).select_from(Stock))
        self.assertEqual(stock_rows, 0, "Expected no Stock parent inserted for a partially null FK")

        print("\n...test_partially_null_key_saves_line_without_inserting_parent ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
