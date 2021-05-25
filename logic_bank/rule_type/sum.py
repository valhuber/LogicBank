from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from typing import Callable

from logic_bank.exec_row_logic.logic_row import ParentRoleAdjuster
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.aggregate import Aggregate


class Sum(Aggregate):
    """
    Create rule instance and save in RuleBank, eg

        Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
             where=lambda row: row.ShippedDate is None)  # *not* a sql select sum...

    Execute adjust_parent
    """

    def __init__(self, derive: InstrumentedAttribute, as_sum_of: any, where: any):
        super(Sum, self).__init__(derive=derive, where=where)
        self._as_sum_of = as_sum_of  # could probably super-ize parent accessor
        if isinstance(as_sum_of, str):
            self._child_role_name = self._as_sum_of.split(".")[0]  # child role retrieves children
            self._child_summed_field = self._as_sum_of.split(".")[1]
        elif isinstance(as_sum_of, InstrumentedAttribute):
            self._child_summed_field = as_sum_of.key
            child_attrs = as_sum_of.parent.attrs
            self._child_role_name = self.get_child_role_name(child_attrs=child_attrs)
        else:
            raise Exception("as_sum_of must be either string, or <mapped-class.column>: " +
                            str(as_sum_of))
        rb = RuleBank()
        rb.deposit_rule(self)

    def __str__(self):
        if self._where != "":
            result = super().__str__() + f'Sum({self._as_sum_of} Where {self._where})'
        else:
            result = super().__str__() + f'Sum({self._as_sum_of})'
        # result += "  (adjust using parent_role_name: " + self._parent_role_name + ")"
        return result

    def adjust_parent(self, parent_adjustor: ParentRoleAdjuster):
        """
        @see LogicRow.adjust_parent_aggregates - drives adjustments by calling this for each aggregate
        Set parent_adjustor iff adjustment update is required for this aggregate
            * Insert & Delete - value non-zero
            * Update - summed field, where or pk changes
        if set, the parent will be updated (for possibly multiple adjusts for this role)
        """
        self.adjust_parent_aggregate(parent_adjustor=parent_adjustor,
                                     get_summed_field=lambda: getattr(parent_adjustor.child_logic_row.row, self._child_summed_field),
                                     get_old_summed_field=lambda: getattr(parent_adjustor.child_logic_row.old_row, self._child_summed_field)
                                     )

