from logic_bank.logic_bank import Rule
from examples.passive_delete_cascade.db.models import Order, OrderDetail


def declare_logic():
    """
    passive_deletes cascade-delete regression rules - see
    system/LogicBank-Internal-Dev/passive-delete-cascade-typo.md.

    Order.amount_total = Sum(OrderDetail.amount) - exercises the sum-adjustment
    path inside LogicRow._cascade_delete_children(), which only runs when a
    relationship declares BOTH cascade="all, delete" AND passive_deletes=True
    (the DBMS enforces the cascade, not SQLAlchemy).
    """
    Rule.sum(derive=Order.amount_total, as_sum_of=OrderDetail.amount)
