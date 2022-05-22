from datetime import datetime

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from examples.custom_exceptions.db.models import Customer, Order, Payment, PaymentAllocation
from logic_bank.util import ConstraintException


def declare_logic():
    """
    activate, then rules applied on commit

    automatically invoked, ordered and optimized
    """

    Rule.constraint(validate=Customer,
                    error_msg="balance ({row.Balance}) exceeds CreditLimit ({row.CreditLimit})",
                    as_condition=lambda row: row.Balance <= row.CreditLimit,
                    error_attributes=[Customer.CreditLimit, Customer.Balance])

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal)

    def handle_all(logic_row: LogicRow):
        row = logic_row.row
        if logic_row.ins_upd_dlt == "ins" and hasattr(row, "CreatedOn"):
            row.CreatedOn = datetime.datetime.now()
            logic_row.log("early_row_event_all_classes - handle_all sets 'Created_on"'')

        if logic_row.nest_level == 0:  # client updates should not alter derivations
            derived_attributes = logic_row._get_derived_attributes()
            if logic_row.are_attributes_changed(derived_attributes):
                # NOTE: this does not trigger constraint_event registered in activate
                raise ConstraintException("One or more derived attributes are changed")

    Rule.early_row_event_all_classes(early_row_event_all_classes=handle_all)
