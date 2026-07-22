import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.commit_event_mutation_scan.tests.test_row_event_mutation_scan")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from logic_bank.exceptions import LBActivateException
    from examples.commit_event_mutation_scan.db.models import Order, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression tests for AbstractRowEvent._check_row_mutation() (row_event.py) -
    RowEvent and CommitRowEvent both fire AFTER the row's own Formula/Sum/Count/
    Constraint/CommitConstraint cascade has already run for this flush, with no
    second pass. A `row.<attr> = value` there is silently persisted without being
    re-derived-from or re-validated - see
    system/LogicBank-Internal-Dev/commit-event-mutation-gap.md.

    Activation now fails fast (LBActivateException) for RowEvent/CommitRowEvent
    handlers whose source appears to write `row.<attr> =`, unless
    allow_row_mutation=True is passed. EarlyRowEvent is exempt (mutation there is
    safe and is its documented purpose - it fires BEFORE the row's own cascade).

    Each test builds its own fresh in-memory engine/session, since the thing under
    test is LogicBank.activate() itself (which either raises or doesn't) - no
    commit/gold-DB machinery needed.
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

    def test_commit_row_event_mutation_raises(self):
        """ CommitRowEvent handler that writes row.<attr> = ... must fail activation. """
        def declare_logic():
            def bad_handler(row, old_row, logic_row):
                row.notes = "mutated"
            Rule.commit_row_event(on_class=Order, calling=bad_handler)

        with self.assertRaises(LBActivateException) as context:
            self._activate(declare_logic)
        assert "appears to mutate row" in str(context.exception), \
            f"Expected mutation-scan error, got: {context.exception}"
        assert "bad_handler" in str(context.exception)

        print("\n...test_commit_row_event_mutation_raises ran to completion\n\n")

    def test_row_event_mutation_raises(self):
        """ RowEvent handler that writes row.<attr> = ... must fail activation -
        same timing risk as CommitRowEvent (fires after the row's own cascade,
        at _row_events(), not before it).
        """
        def declare_logic():
            def bad_handler(row, old_row, logic_row):
                row.item_count = 999
            Rule.row_event(on_class=Order, calling=bad_handler)

        with self.assertRaises(LBActivateException) as context:
            self._activate(declare_logic)
        assert "appears to mutate row" in str(context.exception), \
            f"Expected mutation-scan error, got: {context.exception}"

        print("\n...test_row_event_mutation_raises ran to completion\n\n")

    def test_early_row_event_mutation_allowed(self):
        """ EarlyRowEvent fires BEFORE the row's own cascade - mutation there is
        safe and is its documented purpose (eg, defaulting). Must NOT be scanned.
        """
        def declare_logic():
            def default_notes(row, old_row, logic_row):
                if row.notes is None:
                    row.notes = "defaulted"
            Rule.early_row_event(on_class=Order, calling=default_notes)

        session = self._activate(declare_logic)  # must NOT raise

        order = Order(id=1)
        session.add(order)
        session.commit()
        assert order.notes == "defaulted", f"Expected early_row_event default to apply, got {order.notes}"

        print("\n...test_early_row_event_mutation_allowed ran to completion\n\n")

    def test_read_only_commit_row_event_allowed(self):
        """ A CommitRowEvent that only READS row attributes (no assignment) must
        activate cleanly - this is the common, documented usage (logging, sending
        webhooks/Kafka messages, congratulate_sales_rep-style patterns).
        """
        seen = []

        def declare_logic():
            def read_only_handler(row, old_row, logic_row):
                seen.append(row.notes)  # read, not write
            Rule.commit_row_event(on_class=Order, calling=read_only_handler)

        session = self._activate(declare_logic)  # must NOT raise

        order = Order(id=1, notes="hello")
        session.add(order)
        session.commit()
        assert seen == ["hello"], f"Expected read-only handler to fire and read notes, got {seen}"

        print("\n...test_read_only_commit_row_event_allowed ran to completion\n\n")

    def test_new_row_insert_pattern_allowed(self):
        """ The safe "insert a NEW row" pattern (transfer_funds / add_employee_via_link
        style: logic_row.insert(reason=..., row=new_row) or
        new_logic_row().row.attr = ...) must NOT be flagged - it mutates a
        freshly-constructed row via a DIFFERENT variable's .row, not the event's
        own `row` parameter, and gets the full cascade via .insert().
        """
        def declare_logic():
            def handler(row, old_row, logic_row):
                new_logic_row = logic_row.new_logic_row(Order)
                new_logic_row.row.id = 2
                new_logic_row.row.notes = "created via event"
                new_logic_row.insert(reason="test new-row pattern")
            Rule.commit_row_event(on_class=Order, calling=handler)

        session = self._activate(declare_logic)  # must NOT raise

        order = Order(id=1, notes="original")
        session.add(order)
        session.commit()

        created = session.query(Order).filter(Order.id == 2).one()
        assert created.notes == "created via event", \
            f"Expected the new-row pattern to insert Order 2, got {created.notes}"

        print("\n...test_new_row_insert_pattern_allowed ran to completion\n\n")

    def test_allow_row_mutation_opt_out(self):
        """ allow_row_mutation=True bypasses the scan entirely - the escape hatch
        for a deliberate, understood mutation (e.g., a plain non-derived column).
        """
        def declare_logic():
            def handler(row, old_row, logic_row):
                row.notes = "mutated with opt-out"
            Rule.commit_row_event(on_class=Order, calling=handler, allow_row_mutation=True)

        session = self._activate(declare_logic)  # must NOT raise

        order = Order(id=1, notes="original")
        session.add(order)
        session.commit()
        assert order.notes == "mutated with opt-out", \
            f"Expected the opted-out mutation to be persisted, got {order.notes}"

        print("\n...test_allow_row_mutation_opt_out ran to completion\n\n")

    def test_old_row_reference_not_flagged(self):
        """ Reading/comparing old_row (a normal, safe pattern) must not be
        mistaken for a `row.<attr> =` write.
        """
        def declare_logic():
            def handler(row, old_row, logic_row):
                if logic_row.is_updated() and old_row.notes != row.notes:
                    pass  # just a comparison, no mutation
            Rule.commit_row_event(on_class=Order, calling=handler)

        self._activate(declare_logic)  # must NOT raise

        print("\n...test_old_row_reference_not_flagged ran to completion\n\n")
