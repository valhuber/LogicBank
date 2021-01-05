from logic_bank.logic_bank import Rule
from examples.custom_exceptions.db.models import Customer, Order, Payment, PaymentAllocation


def declare_logic():
    """
    activate, then rules applied on commit

    automatically invoked, ordered and optimized
    """

    Rule.constraint(validate=Customer,
                    error_msg="balance ({row.Balance}) exceeds CreditLimit ({row.CreditLimit})",
                    as_condition=lambda row: row.Balance <= row.CreditLimit,
                    error_attributes=[Customer.CreditLimit, Customer.Balance])
                    # error_attributes="Customer.CreditLimit, Customer.Balance")

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal)