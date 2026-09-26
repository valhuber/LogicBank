import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.cascade_parent_without_rules.tests.test_cascade_parent_without_rules")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.cascade_parent_without_rules.db.models import Order, OrderDetail, Base

    print("\n" + sys_env_info + "\n\n")


def detail_shipped_date(row, old_row=None, logic_row=None):
    """Copy of the parent's shipped date"""
    return row.Order.shipped_date


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #33
    (https://github.com/valhuber/LogicBank/issues/33): get_referring_children
    (rule_bank/rule_bank_withdraw.py) returned {} whenever the PARENT class had
    no rules of its own - even though the dependency it needed to find lives on
    the CHILD's rules. So a child formula referencing a parent attribute
    (row.Order.shipped_date) silently stopped being recomputed when that
    attribute changed on the parent, as long as the parent itself had no rules.
    Adding any unrelated rule to the parent masked the bug.

    Fixed by registering an empty TableRules for the parent instead of
    returning early, so the loop that inspects the child's rules still runs.
    See system/LogicBank-Internal-Dev/cascade-parent-without-rules-issue-33.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.formula(derive=OrderDetail.shipped_date, calling=detail_shipped_date)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_insert_copies_parent_shipped_date(self):
        session = self._activate()

        order = Order(shipped_date='2026-01-01')
        session.add(order)
        session.commit()

        detail = OrderDetail(order_id=order.id)
        session.add(detail)
        session.commit()
        session.refresh(detail)
        self.assertEqual(detail.shipped_date, '2026-01-01',
                         "Expected shipped_date copied from parent on insert")

        print("\n...test_insert_copies_parent_shipped_date ran to completion\n\n")

    def test_update_on_parent_without_rules_still_cascades(self):
        """
        The actual regression: Order has no rules of its own. Changing
        Order.shipped_date must still recompute OrderDetail.shipped_date via
        the cascade - previously it stayed stale with no error.
        """
        session = self._activate()

        order = Order(shipped_date='2026-01-01')
        session.add(order)
        session.commit()
        detail = OrderDetail(order_id=order.id)
        session.add(detail)
        session.commit()

        # Reload the parent before updating it, as any request does: otherwise
        # the attribute is still expired from the prior commit when assigned,
        # and old_row would already hold the new value - a different reason
        # for the cascade not to happen, and not what this test is about.
        session.refresh(order)
        order.shipped_date = '2026-02-02'
        session.commit()  # previously: cascade skipped, detail stayed stale

        session.refresh(detail)
        self.assertEqual(detail.shipped_date, '2026-02-02',
                         "Expected shipped_date cascaded from parent despite "
                         "parent having no rules of its own")

        print("\n...test_update_on_parent_without_rules_still_cascades ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
