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
    recipients functions: relationship proxy (provider.row.Customer, as used in
    unpaid_orders() above) vs. explicit session.query() - when to use which:

    - relationship proxy: safe once the FK was set via relationship assignment/append
      (e.g. cust_alfki.PaymentList.append(new_payment), see
      tests/test_payment_allocation.py) and only one hop is needed.
    - explicit query: needed when the FK is a raw scalar column (row.x_id = ...)
      rather than a relationship assignment, or when more than one hop is needed.

    Counter-example: genai-logic's charge_distribution.py
    (~/dev/ApiLogicServer/ApiLogicServer-dev/build_and_test/genai-logic/samples/allocate_dept_account_demo)
    sets Charge.project_id as a scalar FK and needs a second hop
    (project.project_funding_definition_id), so it uses an explicit query.
    """