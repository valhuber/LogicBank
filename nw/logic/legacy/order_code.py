import nw.db.models as models
from sqlalchemy.orm import session

from logic_bank.util import get_old_row, row_prt, row2dict, ObjectView

# https://docs.sqlalchemy.org/en/13/_modules/examples/versioned_history/history_meta.html
from nw.logic.legacy.customer_code import customer_update

"""            NO LONGER REQUIRED WITH A RULES-BASED APPROACH

This is part of the hand-coded alternative to declarative logic.
Such code is NO LONGER REQUIRED - rules express the same logic order of magnitude more concisely.
"""

def order_flush_dirty(a_row, a_session: session):
    """
    Called from module init on before_flush
    E.g., altering an Order ShippedDate (we must adjust Customer balance)
    """
    old_row = get_old_row(a_row)
    order_update(a_row, old_row, a_session)


def order_update(a_row, an_old_row, a_session):
    """
    called either by order_flush_dirty, *or* by order_detail_code. to adjust order
    see order_detail_code.order_detail_flush_new
    """
    row_prt(a_row, "\norder_flush_dirty")

    if a_row.ShippedDate != an_old_row.ShippedDate:
        is_unshipped = (a_row.ShippedDate is None) or (a_row.ShippedDate == "")
        delta = - a_row.AmountTotal  # assume not changed!!
        if is_unshipped:
            delta = a_row.AmountTotal
        customer = a_row.Customer
        customer.Balance += delta  # attach, update not req'd
        row_prt(customer, "order_upd adjusted per shipped change")

    if a_row.CustomerId != an_old_row.CustomerId:
        is_unshipped = (a_row.ShippedDate is None) or (a_row.ShippedDate == "")
        if is_unshipped:
            delta = a_row.AmountTotal
            customer = a_row.Customer
            customer.Balance += delta  # attach, update not req'd
            row_prt(customer, "order_upd adjusted Customer per re-assignment")
            old_customer = a_session.query(models.Customer). \
                filter(models.Customer.Id == an_old_row.CustomerId).one()
            # old_customer = ObjectView(row2dict(customer))
            old_customer.Balance -= delta
            a_session.add(old_customer)
            customer_update(old_customer, old_customer, a_session)
            row_prt(customer, "order_upd adjusted Customer, per AmountTotal change")

    if a_row.AmountTotal != an_old_row.AmountTotal:
        # nice try: customer = a_row.Customer  -- fails, since this is *adding* order
        customer = a_session.query(models.Customer). \
            filter(models.Customer.Id == a_row.CustomerId).one()
        old_customer = ObjectView(row2dict(customer))
        delta = a_row.AmountTotal - an_old_row.AmountTotal
        customer.Balance += delta
        #  a_session.add(customer)
        customer_update(customer, old_customer, a_session)
        row_prt(customer, "order_upd adjusted Customer, per AmountTotal change")


def order_flush_new(a_row, a_session: session):
    """
    Called from module init on before_flush
    """
    a_row.ShippedDate = ""  # default value
    row_prt(a_row, "order_flush_new - default values supplied")


def order_flush_delete(a_row, a_session: session):  # FIXME
    """
    Called from module init on before_flush
    """
    is_unshipped = (a_row.ShippedDate is None) or (a_row.ShippedDate == "")
    if is_unshipped:
        delta = a_row.AmountTotal
        customer = a_row.Customer
        customer.Balance -= delta  # attach, update not req'd
        row_prt(customer, "order_upd adjusted Customer per delete")
    row_prt(a_row, "order_flush_delete - default values supplied")


# happens before flush
def order_commit_dirty(a_row, a_session: session):
    old_row = get_old_row(a_row)
    row_prt(a_row, "order_commit_dirty")
