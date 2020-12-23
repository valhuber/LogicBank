from decimal import Decimal
from typing import Callable

import sqlalchemy
from sqlalchemy.orm import object_mapper
from sqlalchemy_utils import get_mapper

from logic_bank import rule_bank
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.allocate import Allocate
from logic_bank.rule_bank import rule_bank_withdraw
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.row_event import EarlyRowEvent

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
    they are run when you issue `session.commit()'.

    Use code completion to discover rules.
    """

    @staticmethod
    def allocate(provider: object = None,
                 calling: Callable = None,
                 recipients: Callable = None,
                 while_calling_allocator: Callable = None,
                 creating_allocation: object = None):
        """
        Allocates anAmount from a Provider to Recipients, creating Allocation rows

        In your rule_bank:

            RuleExtension.allocate(provider=Payment,
                                   recipients=receiving_orders,
                                   calling=allocate_payment,
                                   creating_allocation=PaymentAllocation)

        @see https://github.com/valhuber/LogicBank/wiki/Sample-Project---Allocation
        """
        return Allocate(provider=provider,
                        calling=calling,
                        recipients=recipients,
                        creating_allocation=creating_allocation,
                        while_calling_allocator=while_calling_allocator)

