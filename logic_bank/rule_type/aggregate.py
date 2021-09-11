from typing import Callable

from sqlalchemy.orm import object_mapper, RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.exec_row_logic.logic_row import ParentRoleAdjuster
from logic_bank.rule_type.derivation import Derivation
from logic_bank.util import ConstraintException


class Aggregate(Derivation):

    def __init__(self, derive: InstrumentedAttribute, where: any):
        super(Aggregate, self).__init__(derive)
        self._child_role_name = "FIXME"
        self._where = where
        if where is None:
            self._where_cond = lambda row: True
        elif isinstance(where, str):
            self._where_cond = lambda row: eval(where)
        elif isinstance(where, Callable):
            self._where_cond = where
        else:
            raise Exception("'where' must be string, or lambda: " + self.__str__())
        self._parent_role_name = "set in rule_blank_withdraw"

    def get_parent_role_from_child_role_name(self,
                                             child_logic_row: LogicRow,
                                             child_role_name: str) -> str:
        return self._parent_role_name

    def adjust_parent_aggregate(self,
                                parent_adjustor: ParentRoleAdjuster,
                                get_summed_field: Callable,
                                get_old_summed_field: Callable):
        """
        @see LogicRow.adjust_parent_aggregates
        Set parent_adjustor iff adjustment update is required for this aggregate
            * Insert & Delete - value non-zero
            * Update - summed field, where or pk changes
        if set, the parent will be updated (for possibly multiple adjusts for this role)
        """
        # parent_adjustor.child_logic_row.log(str(self))  # this is where the work is
        if parent_adjustor.child_logic_row.ins_upd_dlt == "ins":
            self.adjust_from_inserted_child(parent_adjustor,
                                            get_summed_field = get_summed_field,
                                            get_old_summed_field = get_old_summed_field)
        elif parent_adjustor.child_logic_row.ins_upd_dlt == "dlt":
            self.adjust_from_deleted_child(parent_adjustor,
                                           get_summed_field = get_summed_field,
                                           get_old_summed_field = get_old_summed_field)
        elif parent_adjustor.child_logic_row.ins_upd_dlt == "upd":
            self.adjust_from_updated_child(parent_adjustor,
                                           get_summed_field = get_summed_field,
                                           get_old_summed_field = get_old_summed_field)
        else:
            raise Exception("Internal error - unexpected ins_upd_dlt value")

    def adjust_from_inserted_child(self,
                                   parent_adjustor: ParentRoleAdjuster,
                                   get_summed_field: Callable,
                                   get_old_summed_field: Callable):
        where = self._where_cond(parent_adjustor.child_logic_row.row)
        delta = get_summed_field()
        if delta is None:
            delta = 0
        if where and delta != 0.0:  # trigger update by setting parent_adjustor.parent_logic_row
            if parent_adjustor.parent_logic_row is None:
                parent_adjustor.parent_logic_row = \
                    parent_adjustor.child_logic_row.get_parent_logic_row(role_name=self._parent_role_name)
            curr_value = getattr(parent_adjustor.parent_logic_row.row, self._column)
            if curr_value is None:
                curr_value = 0
            setattr(parent_adjustor.parent_logic_row.row, self._column, curr_value + delta)
            parent_adjustor.append_adjusting_attributes(self._column)
            # parent_adjustor.child_logic_row.log(f'adjust_from_inserted/adopted_child adjusts {str(self)}')

    def adjust_from_deleted_child(self,
                                  parent_adjustor: ParentRoleAdjuster,
                                  get_summed_field: Callable,
                                  get_old_summed_field: Callable):
        where = self._where_cond(parent_adjustor.child_logic_row.row)
        delta = get_summed_field()
        if where and delta != 0.0:  # trigger update by setting parent_adjustor.parent_logic_row
            parent_role_name = self.get_parent_role_from_child_role_name(
                child_logic_row=parent_adjustor.child_logic_row,
                child_role_name=self._child_role_name
            )
            if parent_adjustor.parent_logic_row is None:
                parent_adjustor.parent_logic_row = \
                    parent_adjustor.child_logic_row.get_parent_logic_row(role_name=self._parent_role_name)
            curr_value = get_summed_field()
            setattr(parent_adjustor.parent_logic_row.row, self._column, curr_value - delta)
            parent_adjustor.append_adjusting_attributes(self._column)
            # print(f'adjust_from_deleted/abandoned_child adjusts {str(self)}')

    def adjust_from_updated_child(self,
                                  parent_adjustor: ParentRoleAdjuster,
                                  get_summed_field: Callable,
                                  get_old_summed_field: Callable):
        parent_role_name = parent_adjustor.parent_role_name
        is_different_parent = parent_adjustor.child_logic_row.is_different_parent(parent_role_name)
        summed_field = get_summed_field()
        old_summed_field = get_old_summed_field()
        if old_summed_field is None:
            old_summed_field = 0
        if is_different_parent:
            self.adjust_from_updated_reparented_child(parent_adjustor=parent_adjustor,
                                                      get_summed_field=get_summed_field,
                                                      get_old_summed_field=get_old_summed_field
                                                      )
        else:
            where = self._where_cond(parent_adjustor.child_logic_row.row)
            old_where = self._where_cond(parent_adjustor.child_logic_row.old_row)
            if where != False and where != True:
                raise Exception("where clause must return boolean: " +
                                str(where) + ", from " + self.__str__())
            if where and old_where:
                delta = summed_field - old_summed_field
            elif not where and not old_where:
                delta = 0.0
            elif where:
                delta = summed_field
            else:  # no longer meets where - decrement
                delta = - summed_field

            if delta != 0.0:  # trigger update by setting parent_adjustor.parent_logic_row
                if delta is not None and delta != 0.0:  # FIXME
                    if parent_adjustor.parent_logic_row is None:
                        parent_adjustor.parent_logic_row = \
                            parent_adjustor.child_logic_row.get_parent_logic_row(role_name=self._parent_role_name)
                curr_value = getattr(parent_adjustor.parent_logic_row.row, self._column)
                setattr(parent_adjustor.parent_logic_row.row, self._column, curr_value + delta)
                parent_adjustor.append_adjusting_attributes(self._column)
                # parent_adjustor.child_logic_row.log(f'adjust_from_updated_child adjusts {str(self)}')

    def adjust_from_updated_reparented_child(self,
                                             parent_adjustor: ParentRoleAdjuster,
                                             get_summed_field: Callable,
                                             get_old_summed_field: Callable):
        """
        Foreign key changed, may require adjust old and new parent
        """
        where = self._where_cond(parent_adjustor.child_logic_row.row)
        delta = get_summed_field()
        if where and delta != 0:  # trigger update by setting parent_adjustor.parent_logic_row
            if parent_adjustor.parent_logic_row is None:
                parent_adjustor.parent_logic_row = \
                    parent_adjustor.child_logic_row.get_parent_logic_row(
                        role_name=self._parent_role_name)
                if parent_adjustor.parent_logic_row.row is None:
                    msg = "Unable to Adjust Missing Parent: " + self._parent_role_name
                    raise ConstraintException(msg)
                curr_value = getattr(parent_adjustor.parent_logic_row.row, self._column)
                setattr(parent_adjustor.parent_logic_row.row, self._column, curr_value + delta)
                parent_adjustor.append_adjusting_attributes(self._column)

        where = self._where_cond(parent_adjustor.child_logic_row.old_row)
        delta = get_old_summed_field()
        if where and delta != 0:
            if parent_adjustor.previous_parent_logic_row is None:
                parent_adjustor.previous_parent_logic_row = \
                    parent_adjustor.child_logic_row.get_parent_logic_row(
                        role_name=self._parent_role_name,
                        from_row=parent_adjustor.child_logic_row.old_row)
            curr_value = getattr(parent_adjustor.previous_parent_logic_row.row, self._column)
            setattr(parent_adjustor.previous_parent_logic_row.row, self._column, curr_value - delta)
            parent_adjustor.append_adjusting_attributes(self._column)

    def get_child_role_name(self, child_attrs):
        found_attr = None
        for each_attr in child_attrs:
            if isinstance(each_attr, RelationshipProperty):
                pass
                parent_class_nodal_name = each_attr.entity.class_
                parent_class_name = self.get_class_name(parent_class_nodal_name)
                if parent_class_name == self.table:
                    if found_attr is not None:
                        raise Exception("TODO - disambiguate relationship")
                    found_attr = each_attr
        if found_attr is None:
            raise Exception("Invalid 'as_sum_of' - not a reference to: " + self.table +
                            " in " + self.__str__())
        child_role_name = found_attr.back_populates
        if child_role_name is None:
            msg = "Invalid 'as_sum_of' - missing back_populates: " + self.table + " in " + self.__str__()
            raise Exception("Invalid 'as_sum_of' - missing back_populates: " + self.table +
                            " in " + self.__str__())
        return child_role_name
