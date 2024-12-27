from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute
from typing import Callable

from logic_bank.exec_row_logic.logic_row import ParentRoleAdjuster
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.rule_type.aggregate import Aggregate


class Sum(Aggregate):
    """
    Create rule instance and save in RuleBank, eg

        Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
             where=lambda row: row.ShippedDate is None)  # *not* a sql select sum...

    Execute adjust_parent
    """

    def __init__(self, derive: InstrumentedAttribute, as_sum_of: any, where: any, child_role_name: str = "", insert_parent: bool=False):
        import sqlalchemy.orm.attributes as attrs
        # from sqlalchemy.orm.attributes import Mapped TODO - see why Pylance complains about rule defs
        # what_is = attrs.Mapped -- this is a super of InstrumentedAttribute, but does not satisfy Pylance
        super(Sum, self).__init__(derive=derive, where=where, child_role_name=child_role_name, insert_parent=insert_parent)  # got here for sum
        self._as_sum_of = as_sum_of  # could probably super-ize parent accessor
        if isinstance(as_sum_of, str):
            self._child_role_name = self._as_sum_of.split(".")[0]  # child role retrieves children
            self._child_summed_field = self._as_sum_of.split(".")[1]
        elif isinstance(as_sum_of, InstrumentedAttribute):
            class_attr = str(self._as_sum_of).split(".")
            self._child_summed_field = as_sum_of.key
            self._child_class = class_attr[0]
            child_attrs = as_sum_of.parent.attrs
            self._child_role_name = self.get_child_role_name(child_attrs=child_attrs)
        else:
            self._load_error = "'derive' attribute not a class.attribute: " + str(derive)
            # raise Exception("as_sum_of must be either string, or <mapped-class.column>: " + str(as_sum_of))
        if 'Customer.CreditLimitYY disabled' in self.get_where_text(self._where) or 'row.BalWhereWorseAttr' in self.get_where_text(self._where):
            debug_stop = 'good breakpoint'
        rb = RuleBank()
        rb.deposit_rule(self)

    def __str__(self):
        if self._where != "":
            result = super().__str__() + f'Sum({self._as_sum_of} Where {self.get_where_text(self._where)} - {self._where})'
        else:
            result = super().__str__() + f'Sum({self._as_sum_of})'
        # result += "  (adjust using parent_role_name: " + self._parent_role_name + ")"
        if self.insert_parent:
            result = result[0: len(result)-1] + ", insert_parent)"
        return result

    def get_referenced_attributes(self) -> list[str]:
        referenced_attributes = self.get_aggregate_dependencies()
        referenced_attributes.append(self._child_class  + '.' + self._child_summed_field + ": sum derived from")
        return referenced_attributes


    def adjust_parent(self, parent_adjustor: ParentRoleAdjuster, do_not_adjust_list = None):
        """
        @see LogicRow.adjust_parent_aggregates - drives adjustments by calling this for each aggregate
        Set parent_adjustor iff adjustment update is required for this aggregate
            * Insert & Delete - value non-zero
            * Update - summed field, where or pk changes
        if set, the parent will be updated (for possibly multiple adjusts for this role)
        """
        self.adjust_parent_aggregate(parent_adjustor=parent_adjustor,
                                     get_summed_field=lambda: getattr(parent_adjustor.child_logic_row.row, self._child_summed_field),
                                     get_old_summed_field=lambda: getattr(parent_adjustor.child_logic_row.old_row, self._child_summed_field),
                                     do_not_adjust_list=do_not_adjust_list
                                     )

