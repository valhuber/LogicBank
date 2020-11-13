from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.allocate import allocate, Allocate
from logic_bank.logic_bank import Rule
from payment_allocation.db.models import Customer, Order, Payment, PaymentAllocation


def allocate_payment(row: Payment, old_row: Payment, logic_row: LogicRow):
    """ get unpaid orders (recipient), invoke allocation """
    customer_of_payment = row.Customer
    unpaid_orders = logic_row.session.query(Order)\
        .filter(Order.AmountOwed > 0, Order.CustomerId == customer_of_payment.Id)\
        .order_by(Order.OrderDate).all()
    Allocate(from_provider_row=logic_row,  # uses default while_calling_allocator
             to_recipients=unpaid_orders,
             creating_allocation=PaymentAllocation).execute()


def declare_logic():

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountOwed)

    Rule.formula(derive=Order.AmountOwed, as_expression=lambda row: row.AmountTotal - row.AmountPaid)

    Rule.sum(derive=Order.AmountPaid, as_sum_of=PaymentAllocation.AmountAllocated)

    Rule.early_row_event(on_class=Payment, calling=allocate_payment)

    """
    failed getting unpaid orders like this
        https://stackoverflow.com/questions/40524749/sqlalchemy-query-filter-on-child-attribute
        q = s.query(Parent).filter(Parent.child.has(Child.value > 20))
    
    sample data:

        (10653 owes nothing)
        orderId OrderDate   AmountTotal AmountPaid  AmountOwed  ==> Allocated
        10692   2013-10-03  878         0           100         100
        10702   2013-10-03  330         0           330         330
        10835   2014-01-15  851         0           851         570
        10952   2014-03-16  491.20      0           491.20      *
        11011   2014-04-09  960         0           960         *
    """
