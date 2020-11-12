from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.allocate import allocate
from logic_bank.logic_bank import Rule
from payment_allocation.db.models import Customer, Order, Payment, PaymentAllocation


def declare_logic():

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountOwed)

    Rule.formula(derive=Order.AmountOwed, as_expression=lambda row: row.AmountTotal - row.AmountPaid)

    Rule.sum(derive=Order.AmountPaid, as_sum_of=PaymentAllocation.AmountAllocated)

    def allocate_payment(row: Payment, old_row: Payment, logic_row: LogicRow):
        def each_payment_allocation(allocation_logic_row, provider_logic_row):
            if provider_logic_row.row.AmountUnAllocated is None:
                provider_logic_row.row.AmountUnAllocated = provider_logic_row.row.Amount
            amount = min(Decimal(provider_logic_row.row.AmountUnAllocated),
                         Decimal(allocation_logic_row.row.Order.AmountOwed))
            provider_logic_row.row.AmountUnAllocated = \
                provider_logic_row.row.AmountUnAllocated - amount
            allocation_logic_row.row.AmountAllocated = amount
            any_left = provider_logic_row.row.AmountUnAllocated > 0
            return any_left

        # unpaid_orders = row.Customer.OrderList
        # https://stackoverflow.com/questions/40524749/sqlalchemy-query-filter-on-child-attribute
        # q = s.query(Parent).filter(Parent.child.has(Child.value > 20))
        test_cust = row.Customer
        unpaid_orders = logic_row.session.query(Order)\
            .filter(Order.AmountOwed > 0, Order.CustomerId == test_cust.Id)\
            .order_by(Order.OrderDate).all()
        """
            (10653 owes nothing)
            orderId OrderDate   AmountTotal AmountPaid  AmountOwed  ==> Allocated
            10692   2013-10-03  878         0           100         100
            10702   2013-10-03  330         0           330         330
            10835   2014-01-15  851         0           851         570
            10952   2014-03-16  491.20      0           491.20      *
            11011   2014-04-09  960         0           960         *
        """
        allocate(from_provider_row=logic_row,
                 to_recipients=unpaid_orders,
                 creating_allocation=PaymentAllocation,
                 while_calling_allocator=each_payment_allocation)

    Rule.early_row_event(on_class=Payment, calling=allocate_payment)
