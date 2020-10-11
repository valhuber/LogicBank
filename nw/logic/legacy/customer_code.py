from sqlalchemy.orm import session

from logic_bank.util import get_old_row, row_prt


def customer_update(a_row, an_old_row, a_session):
    """Customer update logic
    e.g., balance adjusted in in Order before_flush, check credit here
    """
    if a_row.Balance > a_row.CreditLimit:  # TODO proper Exception type
        raise Exception("\ncustomer_flush credit limit exceeded")


def customer_flush_dirty(a_row, a_session: session):
    """
    Called from listeners.py on before_flush
    """
    old_row = get_old_row(a_row)
    row_prt(a_row, "\ncustomer_flush_dirty")

    customer_update(a_row, old_row, a_session)


# happens before flush
def customer_commit_dirty(a_row, a_session: session):
    old_row = get_old_row(a_row)
    row_prt(a_row, "order_commit_dirty")

