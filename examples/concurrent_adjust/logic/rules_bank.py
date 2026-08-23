from logic_bank.logic_bank import Rule
from examples.concurrent_adjust.db.models import Customer, Order


def declare_logic():
    """
    TRANS_UPDATE_LOCKING regression rules - see internal_dev/locking_strategy.md
    (ApiLogicServer-src) for full background.

    The framework's own flagship example, unchanged - this is deliberate, so the
    scenario maps 1:1 onto the design doc's Section 3 walkthrough.
    """
    Rule.sum(derive=Customer.balance, as_sum_of=Order.amount_total,
             where=lambda row: row.date_shipped is None)
    Rule.constraint(validate=Customer,
                     as_condition=lambda row: row.balance <= row.credit_limit,
                     error_msg="balance ({row.balance}) exceeds credit_limit ({row.credit_limit})")
