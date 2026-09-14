import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime
from decimal import Decimal

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.spurious_parent_dependency.tests.test_spurious_parent_dependency")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import func
    from logic_bank.logic_bank import Rule, LogicBank
    from logic_bank.rule_bank.rule_bank import RuleBank
    from logic_bank.exec_row_logic.logic_row import LogicRow
    from logic_bank.exceptions import LBActivateException
    from examples.spurious_parent_dependency.db.models import Customer, Item, Label, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression tests for GitHub issue #21
    (https://github.com/valhuber/LogicBank/issues/21): parse_dependencies
    (abstractrule.py) used to register any 3+-node `row.X.Y` token as a parent
    dependency, whether or not X was an actual relationship. A chained method
    call on a plain column (row.code.zfill(8)) or a sub-query fragment left over
    from paren-stripping (row.id_customer).scalar()) would be misparsed the same
    way a real parent reference (row.customer.name) is.

    Fixed via AbstractRule._is_relationship_node(): a 3+-node token is only kept
    as a dependency if the middle node is a real SQLAlchemy relationship on the
    mapped class. See system/LogicBank-Internal-Dev/spurious-parent-dependency.md.

    Each test builds its own fresh in-memory engine/session, since the thing
    under test is dependency parsing / LogicBank.activate() itself.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self, declare_logic):
        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic,
                           aggregate_defaults=True, all_defaults=False)
        return session

    def test_case_2a_str_method_on_column_not_registered_as_dependency(self):
        """ row.code.zfill(8): 'code' is a plain column, not a relationship - must
        NOT be registered as a parent-role dependency, and must NOT crash on UPDATE
        (previously: _get_parent_role_def raised "FIXME invalid role name code").

        GitHub issue #31 (follow-up to #21): the #21 fix over-corrected by dropping
        the 'code' token entirely instead of registering it as an own-column
        dependency. That silently broke pruning - updating 'code' left padded_code
        stale, with no error - and, when 'code' was itself a formula, execution
        ordering, since the engine didn't know padded_code depended on it. Fixed via
        AbstractRule._is_column_node(): 'code' IS now registered (as a plain
        dependency, not a parent-role dependency), so the formula is correctly
        recomputed when 'code' changes and correctly ordered after it.
        """
        def declare_logic():
            Rule.formula(derive=Item.padded_code, as_exp="row.code.zfill(8)")

        session = self._activate(declare_logic)  # must NOT raise

        formula = RuleBank().orm_objects["Item"].rules[0]
        assert formula._dependencies == ["code"], \
            f"Expected the chain on a plain column to register that column, got {formula._dependencies}"

        item = Item(id_item=1, code="42", price=Decimal("1.00"))
        session.add(item)
        session.commit()  # insert - formulas aren't pruned, must not raise

        item.price = Decimal("2.00")
        session.commit()  # update - THIS previously raised "FIXME invalid role name code"
        assert item.padded_code == "00000042", f"Expected zero-padded code, got {item.padded_code}"

        item.code = "7"
        session.commit()  # update of the column the method is called on - must recompute, not be pruned
        assert item.padded_code == "00000007", f"Expected recomputed padded code, got {item.padded_code}"

        print("\n...test_case_2a_str_method_on_column_not_registered_as_dependency ran to completion\n\n")

    def test_case_2c_method_on_column_that_is_itself_a_formula_orders_correctly(self):
        """ GitHub issue #31: Label.padded_code (row.code.zfill(8)) is declared
        BEFORE Label.code (row.raw + ''), and code is itself a formula. Without
        registering 'code' as a dependency, compute_formula_execution_order has
        no way to know padded_code must run after code - on insert, the method
        would be called against code's un-derived (None) value and crash with
        AttributeError: 'NoneType' object has no attribute 'zfill'. Registering
        'code' as an own-column dependency (test_case_2a) also fixes this: the
        engine now knows padded_code depends on code, regardless of declaration
        order.
        """
        def declare_logic():
            Rule.formula(derive=Label.padded_code, as_exp="row.code.zfill(8)")  # declared before code
            Rule.formula(derive=Label.code, as_exp="row.raw + ''")

        session = self._activate(declare_logic)  # must NOT raise

        label = Label(id_label=1, raw="42")
        session.add(label)
        session.commit()  # insert - previously crashed: code not yet derived when padded_code ran
        assert label.code == "42", f"Expected code derived from raw, got {label.code}"
        assert label.padded_code == "00000042", f"Expected zero-padded code, got {label.padded_code}"

        print("\n...test_case_2c_method_on_column_that_is_itself_a_formula_orders_correctly ran to completion\n\n")

    def test_case_2b_subquery_fragment_does_not_kill_activation(self):
        """ A sub-query inside a Constraint's calling= function - the trailing
        `... != row.id_customer).scalar()` used to parse to the dependency
        'id_customer).scalar', which isn't a real attribute, so activation of
        the WHOLE rule set died with LBActivateException. Must now activate
        cleanly.
        """
        def only_one_unknown_customer(row: Customer, old_row: Customer, logic_row: LogicRow):
            count = logic_row.session.query(func.count()).select_from(Customer).filter(
                Customer.unknown_customer == 1,
                Customer.id_customer != row.id_customer).scalar()
            return count == 0

        def declare_logic():
            Rule.constraint(validate=Customer, calling=only_one_unknown_customer,
                            error_msg="only one unknown customer allowed")

        self._activate(declare_logic)  # must NOT raise LBActivateException

        print("\n...test_case_2b_subquery_fragment_does_not_kill_activation ran to completion\n\n")

    def test_genuine_parent_reference_still_registered(self):
        """ Non-regression: a REAL parent reference (row.customer.name, where
        'customer' IS an actual relationship) must still be registered as a
        dependency (_is_relationship_node() must not drop legitimate references,
        only spurious ones) and the formula must still compute correctly on
        insert - the fix must not make _is_relationship_node() over-eager and
        reject real relationships.

        Note: parent-attribute-change cascading to a `calling=`/`as_expression=`
        lambda formula's dependents is a separate, pre-existing behavior
        (unaffected either way by this fix - reproduced identically on
        unmodified main) and is out of scope here; see
        system/LogicBank-Internal-Dev/spurious-parent-dependency.md.
        """
        def declare_logic():
            Rule.formula(derive=Item.padded_code,
                        as_expression=lambda row: (row.customer.name or "") + row.code)

        session = self._activate(declare_logic)  # must NOT raise

        formula = RuleBank().orm_objects["Item"].rules[0]
        assert "customer.name" in formula._dependencies, \
            f"Expected genuine parent reference 'customer.name' to be tracked, got {formula._dependencies}"

        customer = Customer(id_customer=1, name="Acme")
        item = Item(id_item=1, id_customer=1, code="42", price=Decimal("1.00"), customer=customer)
        session.add_all([customer, item])
        session.commit()
        assert item.padded_code == "Acme42", f"Expected initial cascade, got {item.padded_code}"

        print("\n...test_genuine_parent_reference_still_registered ran to completion\n\n")
