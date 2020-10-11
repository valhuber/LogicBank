from sqlalchemy import event
from sqlalchemy.orm import session

from nw.logic.legacy.order_code import order_commit_dirty, order_flush_dirty, order_flush_new, order_flush_delete
from nw.logic.legacy.order_detail_code import order_detail_flush_new, order_detail_flush_delete

from logic_bank.util import prt

'''
These listeners are part of the legacy, hand-coded logic alternative
(Not required in a rules-based approach)
'''


def before_flush(a_session: session, a_flush_context, an_instances):
    print("before_flush   BEGIN")
    for each_instance in a_session.dirty:
        print("nw_before_flush flushing Dirty! --> " + str(each_instance))
        obj_class = each_instance.__tablename__
        if obj_class == "Order":
            order_flush_dirty(each_instance, a_session)
        elif obj_class == "OrderDetail":
            print("Stub")

    for each_instance in a_session.new:
        print("nw_before_flush flushing New! --> " + str(each_instance))
        obj_class = each_instance.__tablename__
        if obj_class == "OrderDetail":
            order_detail_flush_new(each_instance, a_session)
        elif obj_class == "Order":
            order_flush_new(each_instance, a_session)

    for each_instance in a_session.deleted:
        print("nw_before_flush flushing New! --> " + str(each_instance))
        obj_class = each_instance.__tablename__
        if obj_class == "OrderDetail":
            order_detail_flush_delete(each_instance, a_session)
        elif obj_class == "Order":
            order_flush_delete(each_instance, a_session)

    print("before_flush  EXIT")


def setup(session: session):
    """
    setup legacy logic

    only implements 5 basic check-credit rules
    other Use Cases not implemented

    only tested for tests/add_order
    tests will fail that verify counts

    :param session:
    :return:
    """
    # target, modifier, function
    print("\n" + prt("legacy setup - register listeners"))
    event.listen(session, "before_flush", before_flush)
