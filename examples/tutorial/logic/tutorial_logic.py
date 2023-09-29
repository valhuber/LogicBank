from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from examples.tutorial.db.models import Customer, Order, Payment, PaymentAllocation


def declare_logic():
    """
    activate, then rules applied on commit

    automatically invoked, ordered and optimized
    """

    explore_rules = True   # set True to explore rules
    if explore_rules:
        Rule.constraint(validate=Customer,
                        error_msg="balance ({row.Balance}) exceeds 2000)",
                        as_condition=lambda row: row.Balance <= 2000)

        Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal)

    explore_extensibility = False  # set True to explore extensibility
    if explore_extensibility:

        def follow_up(row: Order, old_row: Order, logic_row: LogicRow):
            if logic_row.ins_upd_dlt == "upd":
                if logic_row.row.AmountTotal < logic_row.old_row.AmountTotal:
                    print("\nStub: send email to sales manager to follow up\n")

        Rule.commit_row_event(on_class=Order, calling=follow_up)
