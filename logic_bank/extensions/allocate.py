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
                 recipients: Callable = None,
                 while_calling_allocator: Callable = None):
        self.recipients = recipients
        if recipients is None:
            raise Exception("Recipients lambda is required")
        self.creating_allocation = creating_allocation  # Custom Rule Arguments
        self.while_calling_allocator = while_calling_allocator
        super(Allocate, self).__init__(provider, None)

    def __str__(self):
        creating = str(self.creating_allocation)
        nodes = creating.split('.')
        last_node = nodes[len(nodes)-1]
        last_node = last_node[0: len(last_node)-2]
        return f'Allocate Rule, creating: {last_node}'

    def execute(self, logic_row: LogicRow):
        """
        Called by logic engine, overriding generic EarlyEvent rule.

        Creates allocation row for each recipient until while_calling_allocator returns false

        :return:
        """
        logic_row.log(f'BEGIN {str(self)}')
        provider = logic_row
        to_recipients = self.recipients(provider)
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
        provider.log(f'END {str(self)}')
        return self

    def while_calling_allocator_default(self, allocation_logic_row, provider_logic_row) -> bool:
        """
        Called for each created allocation, to
            * insert the created allocation (triggering rules that compute `Allocation.AmountAllocated`)
            * reduce Provider.AmountUnAllocated
            * return boolean indicating whether Provider.AmountUnAllocated > 0 (remains)

        This uses default names:
            * provider.Amount
            * provider.AmountUnallocated
            * allocation.AmountAllocated

        To use your names, copy this code and alter as as required

        :param allocation_logic_row: allocation row being created
        :param provider_logic_row: provider
        :return: provider has AmountUnAllocated remaining
        """

        if provider_logic_row.row.AmountUnAllocated is None:
            provider_logic_row.row.AmountUnAllocated = provider_logic_row.row.Amount  # initialization

        allocation_logic_row.insert(reason="Allocate " + provider_logic_row.name)  # triggers rules, eg AmountAllocated

        provider_logic_row.row.AmountUnAllocated = \
            provider_logic_row.row.AmountUnAllocated - allocation_logic_row.row.AmountAllocated

        return provider_logic_row.row.AmountUnAllocated > 0  # terminate allocation loop if none left
