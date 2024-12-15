from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.attributes import InstrumentedAttribute

import logic_bank.exec_row_logic.logic_row as LogicRow
from logic_bank.rule_bank.rule_bank import RuleBank
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.rule_type.derivation import Derivation
from typing import Callable


class Copy(Derivation):

    def __init__(self, derive: InstrumentedAttribute, from_parent: any):
        super(Copy, self).__init__(derive)
        if isinstance(from_parent, str):
            names = from_parent.split('.')
            self._from_parent_role = names[0]
            self._from_column = names[1]
            self._parent_class_name = names[2]  # TODO if role?
        elif isinstance(from_parent, InstrumentedAttribute):
            self._from_column = from_parent.key
            table_class = from_parent.class_
            self._parent_class_name = self.get_class_name(table_class)  # aka parent_class_name
            pass
            attrs = self._derive.parent.attrs
            found_attr = None
            for each_attr in attrs:
                if isinstance(each_attr, RelationshipProperty):
                    each_parent_class_nodal_name = each_attr.entity.class_
                    each_parent_class_name = self.get_class_name(each_parent_class_nodal_name)
                    if each_parent_class_name == self._parent_class_name:
                        if found_attr is not None:
                            raise Exception("TODO / copy - disambiguate relationship")
                        found_attr = each_attr
            if found_attr is None:
                raise Exception("Invalid 'as_sum_of' - not a reference to: " + self.table +
                                " in " + self.__str__())
            else:
                self._from_parent_role = found_attr.key

        else:
            pass
        rb = RuleBank()
        rb.deposit_rule(self)

    def get_referenced_attributes(self) -> list[str]:
        referenced_attributes = []
        self.get_derived_attribute_name()
        referenced_attributes.append(f'{self.get_derived_attribute_name()}: parent copy derivation')
        referenced_attributes.append(f'{self._parent_class_name}.{self._from_column}: parent copy from')
        return referenced_attributes

    def execute(self, child_logic_row: LogicRow, parent_logic_row: LogicRow):
        AbstractRule.execute(self, child_logic_row)
        each_column_value = getattr(parent_logic_row.row, self._from_column)
        setattr(child_logic_row.row, self._column, each_column_value)

    def __str__(self):
        return super().__str__() + \
               f'Copy({self._from_parent_role}.{self._from_column})'
