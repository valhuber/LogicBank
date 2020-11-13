from decimal import Decimal
from typing import Callable

import sqlalchemy
from sqlalchemy.orm import object_mapper
from sqlalchemy_utils import get_mapper

from logic_bank import rule_bank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_bank import rule_bank_withdraw


class Allocate():
    """
    Allocates anAmount from a Provider to Recipients, creating Allocation rows
    @see https://github.com/valhuber/LogicBank/wiki/Sample-Project---Allocation
    """

    def __init__(self,
                 from_provider_row: LogicRow,  # eg, payment
                 to_recipients: list,          # eg, unpaid orders
                 creating_allocation: object,  # eg, PaymentAllocation (junction)
                 while_calling_allocator: Callable = None):
        self.from_provider_row = from_provider_row
        self.to_recipients = to_recipients
        self.creating_allocation = creating_allocation
        self.while_calling_allocator = while_calling_allocator

    def execute(self):
        """
        Create allocation row for each recipient until while_calling_allocator returns false

        :return:
        """
        for each_recipient in self.to_recipients:
            new_allocation = self.creating_allocation()
            new_allocation_logic_row = LogicRow(row=new_allocation, old_row=new_allocation,
                                                ins_upd_dlt="ins",
                                                nest_level=self.from_provider_row.nest_level + 1,
                                                a_session=self.from_provider_row.session,
                                                row_sets=self.from_provider_row.row_sets)
            new_allocation_logic_row.link(to_parent=self.from_provider_row)
            each_recipient_logic_row = LogicRow(row=each_recipient, old_row=each_recipient,
                                                ins_upd_dlt="*", nest_level=0,
                                                a_session=self.from_provider_row.session,
                                                row_sets=None)
            new_allocation_logic_row.link(to_parent=each_recipient_logic_row)
            if self.while_calling_allocator is not None:
                allocator = self.while_calling_allocator(new_allocation_logic_row, self.from_provider_row)
            else:
                allocator = self.each_allocation(new_allocation_logic_row, self.from_provider_row)
            new_allocation_logic_row.insert(reason="Allocate " + self.from_provider_row.name)
            if not allocator:
                break
        return self

    def each_allocation(self, allocation_logic_row, provider_logic_row) -> bool:
        """
        Called for each created allocation,
        to compute allocation.amount_allocated and reduce provider.AmountUnAllocated

        This uses default names; to use your names, copy this code and alter as as required

        :param allocation_logic_row: allocation row being created
        :param provider_logic_row: provider
        :return: provider has AmountUnAllocated remaining
        """
        if provider_logic_row.row.AmountUnAllocated is None:
            provider_logic_row.row.AmountUnAllocated = provider_logic_row.row.Amount
        amount = min(Decimal(provider_logic_row.row.AmountUnAllocated),
                     Decimal(allocation_logic_row.row.Order.AmountOwed))
        provider_logic_row.row.AmountUnAllocated = \
            provider_logic_row.row.AmountUnAllocated - amount
        allocation_logic_row.row.AmountAllocated = amount
        any_left = provider_logic_row.row.AmountUnAllocated > 0
        return any_left
