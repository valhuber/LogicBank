from decimal import Decimal
from typing import Callable
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_type.row_event import EarlyRowEvent


class Allocate(EarlyRowEvent):
    """
    Allocates anAmount from a Provider to Recipients, creating Allocation rows.

    @see https://github.com/valhuber/LogicBank/wiki/Sample-Project---Allocation
    """
    def __init__(self, provider: object,
                 creating_allocation: object,  # eg, PaymentAllocation (junction)
                 while_calling_allocator: callable = None,
                 calling: Callable = None):
        self.creating_allocation = creating_allocation  # Custom Rule Arguments
        self.while_calling_allocator = while_calling_allocator
        super(Allocate, self).__init__(provider, calling)

    def __str__(self):
        return f'Allocate Rule, for function: {str(self._function)}, creating {str(self.creating_allocation)} '

    def execute(self, logic_row: LogicRow):
        """
        called by logic engine, overriding generic earlyEvent rule.
        Note it passes the rule instance to the handler,
        so that Custom Rule Arguments are passed only to allocation(), below.
        """
        logic_row.log(f'BEGIN {str(self)} on {str(logic_row)}')
        value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row, do=self)
        print(f'END {str(self)} on {str(logic_row)}')

    def allocation(self, provider: LogicRow,  # eg, payment
                   to_recipients: list):
        """
        Create allocation row for each recipient until while_calling_allocator returns false

        :return:
        """
        provider.log("Allocate " + provider.name)
        for each_recipient in to_recipients:
            new_allocation = self.creating_allocation()
            new_allocation_logic_row = LogicRow(row=new_allocation, old_row=new_allocation,
                                                ins_upd_dlt="ins",
                                                nest_level=provider.nest_level + 1,
                                                a_session=provider.session,
                                                row_sets=provider.row_sets)
            new_allocation_logic_row.link(to_parent=provider)
            each_recipient_logic_row = LogicRow(row=each_recipient, old_row=each_recipient,
                                                ins_upd_dlt="*", nest_level=0,
                                                a_session=provider.session,
                                                row_sets=None)
            new_allocation_logic_row.link(to_parent=each_recipient_logic_row)
            if self.while_calling_allocator is not None:
                allocator = self.while_calling_allocator(new_allocation_logic_row,
                                                    provider)
            else:
                allocator = self.while_calling_allocator_default(new_allocation_logic_row,
                                                                 provider)
            if not allocator:
                break
        return self

    def while_calling_allocator_default(self, allocation_logic_row, provider_logic_row) -> bool:
        """
        Called for each created allocation, to
        compute Allocation.AmountAllocated (by running rules), and
        reduce Provider.AmountUnAllocated

        This uses default names:
        provider.Amount
        provider.AmountUnallocated
        allocation.AmountAllocated

        To use your names, copy this code and alter as as required

        :param allocation_logic_row: allocation row being created
        :param provider_logic_row: provider
        :return: provider has AmountUnAllocated remaining
        """
        allocation_logic_row.insert(reason="Allocate " + provider_logic_row.name)

        provider_logic_row.row.AmountUnAllocated = \
            provider_logic_row.row.AmountUnAllocated - allocation_logic_row.row.AmountAllocated

        return provider_logic_row.row.AmountUnAllocated > 0  #  terminate allocation loop if none left
