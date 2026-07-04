from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from examples.after_flush_row_event.db.models import Order

no_condition_fired_for = []
""" regression test hook: Order.id values for which the unconditional after_flush handler fired """

if_condition_fired_for = []
""" regression test hook: Order.id values for which the if_condition handler fired (should be gated on date_shipped) """

when_condition_fired_for = []
""" regression test hook: Order.id values for which the when_condition handler fired (should fire only on False->True transition) """


def declare_logic():

    def notify_no_condition(row: Order, old_row: Order, logic_row: LogicRow):
        no_condition_fired_for.append(row.id)
    Rule.after_flush_row_event(on_class=Order, calling=notify_no_condition)

    def notify_if_shipped(row: Order, old_row: Order, logic_row: LogicRow):
        if_condition_fired_for.append(row.id)
    Rule.after_flush_row_event(on_class=Order, calling=notify_if_shipped,
                                if_condition=lambda row: row.date_shipped is not None)

    def notify_when_shipped(row: Order, old_row: Order, logic_row: LogicRow):
        when_condition_fired_for.append(row.id)
    Rule.after_flush_row_event(on_class=Order, calling=notify_when_shipped,
                                when_condition=lambda row: row.date_shipped is not None)
