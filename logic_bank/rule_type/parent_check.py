import logic_bank.exec_row_logic.logic_row as LogicRow

from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.util import ConstraintException


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

    def execute(self, logic_row: LogicRow):
        # logic_row.log(f'Constraint BEGIN {str(self)} on {str(logic_row)}')
        if self._function is not None:
            value = self._function(row=logic_row.row, old_row=logic_row.old_row, logic_row=logic_row)
        else:
            value = self._as_condition(row=logic_row.row)

        if value:
            pass
        elif not value:
            row = logic_row.row
            msg = eval(f'f"""{self._error_msg}"""')
            from sqlalchemy import exc
            # exception = exc.DBAPIError(msg, None, None)  # 'statement', 'params', and 'orig'
            raise ConstraintException(msg)
        else:
            raise RuntimeError(f'Constraint did not return boolean: {str(self)}')
        logic_row.log_engine(f'Constraint END {str(self)} on {str(logic_row)}')
