from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.rule_extensions import RuleExtension
from logic_bank.logic_bank import Rule
from payment_allocation.db.models import Customer, Order, Payment, PaymentAllocation


def allocate_payment(row: Payment, old_row: Payment, logic_row: LogicRow, do: object):
    """ event handler: get unpaid orders (recipient), invoke allocation """
    customer_of_payment = row.Customer
    unpaid_orders = logic_row.session.query(Order)\
        .filter(Order.AmountOwed > 0, Order.CustomerId == customer_of_payment.Id)\
        .order_by(Order.OrderDate).all()
    row.AmountUnAllocated = row.Amount
    do.allocation(provider=logic_row,  # uses default while_calling_allocator
                  to_recipients=unpaid_orders)
    # print("rules_bank#allocate_payment complete")


def declare_logic():

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountOwed)

    Rule.formula(derive=Order.AmountOwed, as_expression=lambda row: row.AmountTotal - row.AmountPaid)
    Rule.sum(derive=Order.AmountPaid, as_sum_of=PaymentAllocation.AmountAllocated)

    Rule.formula(derive=PaymentAllocation.AmountAllocated, as_expression=lambda row:
        min(Decimal(row.Payment.AmountUnAllocated), Decimal(row.Order.AmountOwed)))

    # Rule.early_row_event(on_class=Payment, calling=allocate_payment)
    RuleExtension.allocate(provider=Payment, calling=allocate_payment, creating_allocation=PaymentAllocation)

    """
    minor issue to research - failed getting unpaid orders like this
        https://stackoverflow.com/questions/40524749/sqlalchemy-query-filter-on-child-attribute
        q = s.query(Parent).filter(Parent.child.has(Child.value > 20))    
    """
