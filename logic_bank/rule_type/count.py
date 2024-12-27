import sqlalchemy
from sqlalchemy.orm.attributes import InstrumentedAttribute

from logic_bank.exec_row_logic.logic_row import ParentRoleAdjuster
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.aggregate import Aggregate


class Count(Aggregate):
    """
    Create rule instance and save in RuleBank, eg

        Rule.count(derive=Customer.UnpaidOrderCount, as_count_of=Order,
                 where=lambda row: row.ShippedDate is None)  # *not* a sql select sum...

    Execute adjust_parent
    """

    def __init__(self, derive: InstrumentedAttribute, as_count_of: object, where: any, child_role_name: str = "", insert_parent: bool=False):
        super(Count, self).__init__(derive=derive, where=where, child_role_name=child_role_name, insert_parent=insert_parent)

        if not isinstance(as_count_of, sqlalchemy.orm.DeclarativeMeta):
            self._load_error = "rule definition error, not mapped class: " + str(as_count_of)
            # raise Exception("rule definition error, not mapped class: " + str(as_count_of))
        self._as_count_of = as_count_of
        self._child_class = self.get_class_name(as_count_of)

        if self._load_error:
            pass  # FIXME log
        else:
            local_attrs = as_count_of._sa_class_manager.local_attrs  # FIXME design
            for each_local_attr in local_attrs:
                random_attr = local_attrs[each_local_attr]
                child_attrs = random_attr.parent.attrs
                break
            self._child_role_name = self.get_child_role_name(child_attrs=child_attrs)

        rb = RuleBank()
        rb.deposit_rule(self)

    def __str__(self):
        if self._where != "":
            result = super().__str__() + f'Count({self._as_count_of} Where {self.get_where_text(self._where)} - {self._where})'
        else:
            result = super().__str__() + f'Count({self._as_count_of})'
        if self.insert_parent:
            result = result[0: len(result)-1] + ", insert_parent)"
        return result

    def get_referenced_attributes(self) -> list[str]:
        referenced_attributes = self.get_aggregate_dependencies()
        return referenced_attributes

    def adjust_parent(self, parent_adjustor: ParentRoleAdjuster, do_not_adjust_list = None):
        """
        @see LogicRow.adjust_parent_aggregates
        Set parent_adjustor iff adjustment update is required for this aggregate
            * Insert & Delete - value non-zero
            * Update - summed field, where or pk changes
        if set, the parent will be updated (for possibly multiple adjusts for this role)
        """
        self.adjust_parent_aggregate(parent_adjustor=parent_adjustor,
                                     get_summed_field=lambda: 1,
                                     get_old_summed_field=lambda: 1,
                                     do_not_adjust_list=do_not_adjust_list
                                     )

