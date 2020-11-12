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
                                            row_sets=from_provider_row.row_sets)
        new_allocation_logic_row.link(to_parent=from_provider_row)
        recipient_mapper = get_mapper(each_recipient)
        each_recipient_logic_row = LogicRow(row=each_recipient, old_row=each_recipient,
                                            ins_upd_dlt="*", nest_level=0,
                                            a_session=from_provider_row.session,
                                            row_sets=None)
        new_allocation_logic_row.link(to_parent=each_recipient_logic_row)
        allocator = while_calling_allocator(new_allocation_logic_row, from_provider_row)
        new_allocation_logic_row.update(reason="Allocate " + from_provider_row.name)
        if not allocator:
            break
    print("Done")