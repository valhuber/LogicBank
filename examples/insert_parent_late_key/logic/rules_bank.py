from logic_bank.logic_bank import Rule
from logic_bank.exec_row_logic.logic_row import LogicRow
from examples.insert_parent_late_key.db.models import Parent, Child


def declare_logic():

    def set_period(row: Child, old_row, logic_row: LogicRow):
        """Child event: sets period (part of the composite FK to Parent) before Row Logic
        runs - like a real order's year_month bucket key, computed from order_date. This
        is what makes period unavailable at Child() construction time, unlike
        examples/insert_parent's Child.parent_2 (set directly in the constructor)."""
        if row.period is None:
            row.period = "2026-09"

    Rule.early_row_event(on_class=Child, calling=set_period)

    Rule.sum(derive=Parent.child_sum, as_sum_of=Child.summed, insert_parent=True)
    Rule.count(derive=Parent.child_count, as_count_of=Child, insert_parent=True)
