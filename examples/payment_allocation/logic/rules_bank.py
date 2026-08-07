from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.rule_extensions import RuleExtension
from logic_bank.logic_bank import Rule
from examples.payment_allocation.db.models import Customer, Order, Payment, PaymentAllocation


def unpaid_orders(provider: LogicRow):
    """ returns Payments' Customers' Orders, where AmountOwed > 0, by OrderDate """
    customer_of_payment = provider.row.Customer
    unpaid_orders_result = provider.session.query(Order)\
        .filter(Order.AmountOwed > 0, Order.CustomerId == customer_of_payment.Id)\
        .order_by(Order.OrderDate).all()
    return unpaid_orders_result


def declare_logic():

    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountOwed)

    Rule.formula(derive=Order.AmountOwed, as_expression=lambda row: row.AmountTotal - row.AmountPaid)
    Rule.sum(derive=Order.AmountPaid, as_sum_of=PaymentAllocation.AmountAllocated)

    Rule.formula(derive=PaymentAllocation.AmountAllocated, as_expression=lambda row:
        min(Decimal(row.Payment.AmountUnAllocated), Decimal(row.Order.AmountOwed)))

    RuleExtension.allocate(provider=Payment,
                           recipients=unpaid_orders,
                           creating_allocation=PaymentAllocation)

    """
    minor issue to research - failed getting unpaid orders like this
        https://stackoverflow.com/questions/40524749/sqlalchemy-query-filter-on-child-attribute
        q = s.query(Parent).filter(Parent.child.has(Child.value > 20))
    """

    """
    another allocation test is in genai-logic: ~/dev/ApiLogicServer/ApiLogicServer-dev/build_and_test/genai-logic/samples/allocate_dept_account_demo
    see logic/logic_discovery/charge_distribution.py - it uses an explicit session
    query (not the relationship proxy) to get from a ChargeDeptAllocation to its
    Project, because project_id there is set as a raw scalar FK by an
    early_row_event (AI handler) rather than via relationship assignment - the
    relationship proxy isn't guaranteed to reflect that FK within the same flush.

    NOT applicable here: unpaid_orders() above uses provider.row.Customer directly
    (a relationship proxy), which is safe because Payment.Customer is always set via
    relationship assignment/append (see tests/test_payment_allocation.py -
    cust_alfki.PaymentList.append(new_payment)), never as a bare CustomerId scalar.
    The explicit-query workaround is only needed when the FK was just set
    programmatically as a scalar column, not as the general/safer pattern.
    """