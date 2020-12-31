from typing import Callable
from logic_bank.extensions.allocate import Allocate
from logic_bank.extensions.copy_row import CopyRow

"""
Logic Bank supports Rule Extensions, of Event Rules.
Rule Extensions are called when event rules are called,
and support Custom Rule Arguments (@see allocate).

Extend this class with your own Rule Extensions.

This class 'publishes' rules built by providers, for consumers.

It enables
    1. Discovery of rules
    2. Code completion for Custom Rule Arguments
"""


class RuleExtension:
    """Invoke these functions to *define* rules.

    Rules are *not* run as they are defined,
    they are run when you issue session.commit()

    Use code completion to discover rules

    .. _Rule Extensibility:
   https://github.com/valhuber/LogicBank/wiki/Rule-Extensibility

    """

    @staticmethod
    def allocate(provider: object = None,
                 recipients: Callable = None,
                 while_calling_allocator: Callable = None,
                 creating_allocation: object = None):
        """
        Allocates anAmount from a Provider to Recipients, creating Allocation rows

        In your rule_bank:

            RuleExtension.allocate(provider=Payment,
                                   recipients=unpaid_orders,
                                   creating_allocation=PaymentAllocation,
                                   while_calling_allocator: my_allocator)

        @see https://github.com/valhuber/LogicBank/wiki/Sample-Project---Allocation
        """
        return Allocate(provider=provider,
                        recipients=recipients,
                        creating_allocation=creating_allocation,
                        while_calling_allocator=while_calling_allocator)

    @staticmethod
    def copy_row(copy_from: object = None,
             copy_to: object = None,
             copy_when: Callable = None,
             initialize_target: Callable = None):
        """
        Copies like-named attrs from copy_from (current row) to copy_to, e.g.,

            RuleExtension.copy(copy_from=Employee,
                copy_to=EmployeeAudit,
                copy_when=lambda logic_row: logic_row.are_attributes_changed([Employee.Salary, Employee.Title]))

        """
        return CopyRow(copy_from = copy_from,
                    copy_to = copy_to,
                    copy_when = copy_when,
                    initialize_target = initialize_target)
