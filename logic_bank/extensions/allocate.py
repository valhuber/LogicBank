from typing import Callable

import sqlalchemy
from sqlalchemy.orm import object_mapper
from sqlalchemy_utils import get_mapper

from logic_bank import rule_bank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_bank import rule_bank_withdraw


def allocate(from_provider_row: LogicRow,   # eg, payment
             to_recipients: list,           # eg, unpaid orders
             creating_allocation: object,   # PaymentAllocation (intersection)
             while_calling_allocator: Callable):
    for each_recipient in to_recipients:
        new_allocation = creating_allocation()
        new_allocation_logic_row = LogicRow(row=new_allocation, old_row=new_allocation,
                                            ins_upd_dlt="ins",
                                            nest_level=from_provider_row.nest_level+1,
                                            a_session=from_provider_row.session,
                                            row_sets=None)
        link(from_child=new_allocation_logic_row, to_parent=from_provider_row)
        recipient_mapper = get_mapper(each_recipient)
        each_recipient_logic_row = LogicRow(row=each_recipient, old_row=each_recipient,
                                            ins_upd_dlt="*", nest_level=0,
                                            a_session=from_provider_row.session,
                                            row_sets=None)
        link(from_child=new_allocation_logic_row, to_parent=each_recipient_logic_row)
        allocator = while_calling_allocator(new_allocation_logic_row, from_provider_row)
        # TODO - session.add(new_allocation)
        if not allocator:
            break
    print("Done")


def link(from_child: LogicRow, to_parent: LogicRow):
    parent_mapper = object_mapper(to_parent.row)
    parents_relationships = parent_mapper.relationships
    parent_role_name = None
    child = from_child.row
    for each_relationship in parents_relationships:  # eg, Payment has child PaymentAllocation
        if each_relationship.direction == sqlalchemy.orm.interfaces.ONETOMANY:  # PA
            each_parent_role_name = each_relationship.back_populates  # eg, AllocationList
            if isinstance(child, each_relationship.entity.class_):
                if parent_role_name is not None:
                    raise Exception("TODO - disambiguate relationship from Provider: <" +
                                    to_parent.name +
                                    "> to Allocation: " + str(type(child)))
                parent_role_name = parent_mapper.class_.__name__  # default TODO design review
    if parent_role_name is None:
        raise Exception("Missing relationship from Provider: <" +
                        to_parent.name +
                        "> to Allocation: " + str(type(child)))
    setattr(child, parent_role_name, to_parent.row)
    return True