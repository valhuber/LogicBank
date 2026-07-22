from logic_bank.logic_bank import Rule
from examples.min_cardinality.db.models import Order, OrderDetail


def declare_logic():
    """
    CommitConstraint regression rules - see logic_bank/rule_type/constraint.py.

    Order must have at least one OrderDetail - a min-cardinality rule that
    Rule.commit_constraint can express but a plain Rule.constraint cannot:
    Order's own insert-time row logic can run before its OrderDetails are
    processed in the same transaction (SQLAlchemy gives no ordering guarantee
    across a flush's dirty/new rows), so a mid-cascade Rule.constraint on
    item_count is not reliable here. Rule.commit_constraint instead checks
    once, after the whole transaction's cascade has settled.
    """
    Rule.count(derive=Order.item_count, as_count_of=OrderDetail)

    Rule.commit_constraint(validate=Order,
                    as_condition=lambda row: row.item_count > 0,
                    error_msg="Order {row.id} must have at least one item")
