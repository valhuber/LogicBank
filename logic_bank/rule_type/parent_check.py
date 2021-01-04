import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule


class ParentCheck(AbstractRule):

    def __init__(self, validate: object,
                 error_msg: str = "Missing Parent",
                 enable: bool = True):
        super(ParentCheck, self).__init__(validate)
        self._error_msg = error_msg
        self._enable = enable
        ll = RuleBank()
        ll.deposit_rule(self)

    def __str__(self):
        return f'ParentCheck: {self._error_msg} '

    def get_rule_text(self):
        text = "Parent Check: " + str(self._decl_meta)
        return text
