from enum import Enum

import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule


class ParentCascade(AbstractRule):

    def __init__(self, validate: object,
                 error_msg: str = "Unable to delete - existing Child rows",
                 relationship: str = "*",
                 action: str = 'nullify'):
        super(ParentCascade, self).__init__(validate)
        self._error_msg = error_msg
        if not isinstance(action, ParentCascadeAction):
            raise Exception("Invalid Action: " + str(action))
        self._action = action
        self._relationship = relationship
        ll = RuleBank()
        ll.deposit_rule(self)

    def __str__(self):
        return f'ParentCheck: {self._error_msg} '

    def get_rule_text(self):
        text = "Parent Check: " + str(self._decl_meta)
        return text


class ParentCascadeAction(Enum):
    DELETE = 'delete'
    NULLIFY = 'nullify'
    PREVENT = 'prevent'
