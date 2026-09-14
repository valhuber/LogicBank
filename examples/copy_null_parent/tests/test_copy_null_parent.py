import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.copy_null_parent.tests.test_copy_null_parent")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from examples.copy_null_parent.db.models import Product, OrderLine, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #28
    (https://github.com/valhuber/LogicBank/issues/28): Copy.execute
    (rule_type/copy.py) did `getattr(parent_logic_row.row, self._from_column)`
    unconditionally. When the child's foreign key is null (a legitimately-absent
    optional parent - e.g. a free-text order line with no product), there is no
    parent, parent_logic_row.row is None, and the insert crashed with
    AttributeError instead of just leaving the copied column None.

    A null optional parent is already a supported case elsewhere (aggregate
    adjustments check `parent_logic_row.row is None` and skip) - Rule.copy was
    the one rule that broke the transaction instead of following that pattern.

    Fixed by guarding the getattr/setattr with a None check. See
    system/LogicBank-Internal-Dev/copy-null-parent.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.copy(derive=OrderLine.tax_rate, from_parent=Product.tax_rate)

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_copy_with_product_still_works(self):
        session = self._activate()

        session.add(Product(id_product=1, tax_rate=21))
        session.commit()

        session.add(OrderLine(id_order_line=1, id_product=1))
        session.commit()
        self.assertEqual(session.get(OrderLine, 1).tax_rate, 21,
                         "Expected tax_rate copied from product")

        print("\n...test_copy_with_product_still_works ran to completion\n\n")

    def test_copy_with_null_parent_does_not_raise(self):
        """
        The actual regression: id_product is None (free-text line, no product).
        Rule.copy must leave tax_rate as None instead of crashing the commit
        with AttributeError: 'NoneType' object has no attribute 'tax_rate'.
        """
        session = self._activate()

        session.add(OrderLine(id_order_line=2, id_product=None))
        session.commit()  # previously: AttributeError

        self.assertIsNone(session.get(OrderLine, 2).tax_rate,
                          "Expected tax_rate to stay None when there is no parent")

        print("\n...test_copy_with_null_parent_does_not_raise ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
