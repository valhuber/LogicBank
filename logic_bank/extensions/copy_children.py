from decimal import Decimal
from typing import Callable
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_type.row_event import RowEvent

# not used (LogicBank 1.0.5)

class CopyChildren(RowEvent):
    """
        Called by logic engine, overriding generic EarlyEvent rule.
        Tested in ApiLogicServer: place_order.py, scenario_name = "Clone Existing Order"
    """
    def __init__(self,
                 copy_from: object,
                 copy_to: object,  # eg, PaymentAllocation (junction)
                 which_children: dict,
                 copy_when: Callable = None):
        self.copy_to = copy_to
        self.copy_from = copy_from
        self.copy_when = copy_when
        self.which_children = which_children
        if copy_to is None:
            raise Exception("copy_to object is required")
        super(CopyChildren, self).__init__(copy_from, None)

    def __str__(self):
        copy_to = str(self.copy_to)
        nodes = copy_to.split('.')
        last_node = nodes[len(nodes)-1]
        last_node = last_node[0: len(last_node)-2]
        return f'Copy children: {last_node}'

    def execute(self, logic_row: LogicRow):
        """
        Delegates to LogicRow.copy_children

        :return:
        """
        do_copy = self.copy_when(logic_row)
        if not do_copy:
            nothing_changed = True  # debug stop
        else:
            copy_to = logic_row
            copy_to.copy_children(copy_from=self.copy_from, which_children=self.which_children)
            return self
