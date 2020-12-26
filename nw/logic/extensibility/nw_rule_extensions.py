from typing import Callable
from nw.logic.extensibility.nw_copy import NWCopy

"""
Logic Bank supports Rule Extensions, of Event Rules.
Rule Extensions are called when event rules are called,
and support Custom Rule Arguments (@see allocate).

@see https://github.com/valhuber/LogicBank/wiki/Rule-Extensibility

Extend this class with your own Rule Extensions.

This class 'publishes' rules built by providers, for consumers.  It enables:
    1. Discovery of rules
    2. Code completion for Custom Rule Arguments
"""


class NWRuleExtension:
    """Invoke these functions to *define* rules.

    Rules are *not* run as they are defined,
    they are run when you issue `session.commit()'.

    Use code completion to discover rules.
    """

    @staticmethod
    def nw_copy(copy_from: object = None,
             copy_to: object = None,
             copy_when: Callable = None,
             initialize_target: Callable = None):
        """
        Copies like-named attrs from copy_from (current row) to copy_to, e.g.,

            RuleExtension.copy_row(copy_from=Employee,
                copy_to=EmployeeAudit,
                copy_when=lambda logic_row: logic_row.are_attributes_changed([Employee.Salary, Employee.Title]))

        """
        return NWCopy(copy_from = copy_from,
                    copy_to = copy_to,
                    copy_when = copy_when,
                    initialize_target = initialize_target)
