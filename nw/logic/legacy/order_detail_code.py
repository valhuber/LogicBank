import nw.db.models as models
from sqlalchemy.orm import session
from logic_bank.util import get_old_row, row_prt, row2dict, ObjectView
from nw.logic.legacy.order_code import order_update


"""            NO LONGER REQUIRED WITH A RULES-BASED APPROACH

This is part of the hand-coded alternative to declarative logic.
Such code is NO LONGER REQUIRED - rules express the same logic order of magnitude more concisely.
"""

def order_detail_flush_new(a_row: models.OrderDetail, a_session: session):
    """
    OrderDetail before_flush, new rows
    compute amount, adjust Order.AmountTotal
    .. which adjusts Customer.balance)
    """
    # no "old" in inserts...  old_row = get_old_row(a_row)
    row_prt(a_row, "\norder_detail_flush_new")  # readable log: curr/old values
    # nice try.. product = row.Product
    product = a_session.query(models.Product).\
        filter(models.Product.Id == a_row.ProductId).one()
    a_row.UnitPrice = product.UnitPrice
    a_row.Amount = a_row.Quantity * a_row.UnitPrice
    order = a_row.OrderHeader
    """
        2 issues make this a little more complicated than expected:
            1. can't just alter AmountTotal - does not trigger Order's before_flush
            2. can't just call Order's before_flush - old values not available
    """
    old_order = ObjectView(row2dict(order))
    order.AmountTotal += a_row.Amount
    order_update(order, old_order, a_session)
    row_prt(order, "order_detail_flush_new adjusted to: " +
            str(order.AmountTotal))


def order_detail_flush_dirty(a_row: models.OrderDetail, a_session: session):
    old_row = get_old_row(a_row)  # type: models.OrderDetail
    if a_row.OrderId == old_row.OrderId:
        if a_row.ProductId != old_row.ProductId:
            product = a_session.query(models.Product). \
                filter(models.Product.Id == a_row.ProductId).one()
            a_row.UnitPrice = product.UnitPrice
        a_row.Amount = a_row.UnitPrice * a_row.Quantity
        if a_row.Amount != old_row.Amount:
            order = a_row.OrderHeader
            order.AmountTotal += a_row.Amount - old_row.Amount
            old_order = ObjectView(row2dict(order))
            order_update(order, old_order, a_session)
            row_prt(order, "order_detail_flush_dirty adjusted to: " +
                    str(order.AmountTotal))
    else:  # moved item to different order
        order = a_row.OrderHeader  # reduce the old one
        order.AmountTotal -= old_row.Amount
        old_order = ObjectView(row2dict(order))
        order_update(order, old_order, a_session)
        row_prt(order, "order_detail_flush_dirty adjusted to: " +
                str(order.AmountTotal))

        if a_row.ProductId != old_row.ProductId:
            product = a_session.query(models.Product). \
                filter(models.Product.Id == old_row.ProductId).one()
            a_row.UnitPrice = product.UnitPrice
        a_row.Amount = a_row.UnitPrice * a_row.Quantity
        order = a_session.query(models.Order). \
            filter(models.Order.Id == a_row.OrderId).one()
        old_order = ObjectView(row2dict(order))
        order.AmountTotal += a_row.Amount
        order_update(order, old_order, a_session)
        row_prt(order, "order_detail_flush_dirty adjusted to: " +
                str(order.AmountTotal))


def order_detail_flush_delete(a_row, a_session: session):
    order = a_row.OrderHeader
    old_order = ObjectView(row2dict(order))  # hmm... key ShippedDate vs. "ShippedDate"
    order.AmountTotal -= a_row.Amount
    order_update(order, old_order, a_session)
    row_prt(order, "order_detail_flush_delete adjusted to: " +
            str(order.AmountTotal))


# happens before flush
def order_detail_commit_dirty(a_row, a_session: session):
    old_row = get_old_row(a_row)

    row_prt(a_row, "\norder_detail_commit_dirty")


def order_detail_modified(object):
    print("order_detail_modified")
