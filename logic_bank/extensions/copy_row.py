from decimal import Decimal
from typing import Callable
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.rule_type.row_event import RowEvent


class CopyRow(RowEvent):
    """
    Copy copy_from -> copy_to (e.g., auditing).
    """
    def __init__(self, copy_from: object,
                 copy_to: object,  # eg, PaymentAllocation (junction)
                 copy_when: Callable = None,
                 initialize_target: Callable = None):
        self.copy_to = copy_to
        if copy_to is None:
            raise Exception("copy_to object is required")
        self.copy_when = copy_when  # Custom Rule Arguments
        self.initialize_target = initialize_target
        super(CopyRow, self).__init__(copy_from, None)

    def __str__(self):
        copy_to = str(self.copy_to)
        nodes = copy_to.split('.')
        last_node = nodes[len(nodes)-1]
        last_node = last_node[0: len(last_node)-2]
        return f'Copy to: {last_node}'

    def execute(self, logic_row: LogicRow):
        """
        Called by logic engine, overriding generic EarlyEvent rule.

        Creates allocation row for each recipient until while_calling_allocator returns false

        :return:
        """
        copy_from = logic_row
        do_copy = self.copy_when(copy_from)
        if not do_copy:
            nothing_changed = True  # debug stop
        else:
            copy_from.log(f'BEGIN {str(self)}')
            copy_to_logic_row = copy_from.new_logic_row(new_row_class=self.copy_to)
            copy_to_logic_row.link(to_parent=copy_from)
            copy_to_logic_row.set_same_named_attributes(copy_from)
            do_session_add = False
            if do_session_add:  # does not appear to matter...
                copy_to_logic_row.session.add(copy_to_logic_row.row)
            copy_to_logic_row.insert(reason="Copy " + copy_to_logic_row.name)  # triggers rules...
            # copy_from.log(f'END {str(self)}')
        return self
