from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.hybrid import hybrid_property
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.rule_bank.rule_bank import RuleBank


class Derivation(AbstractRule):

    def __init__(self, derive: InstrumentedAttribute):
        # names = derive.split('.')
        if not isinstance(derive, InstrumentedAttribute) and \
                not isinstance(derive.descriptor, hybrid_property):
            raise Exception("'derive' attribute not a class.attribute: " + str(derive))
        super(Derivation, self).__init__(derive.class_)
        self._column = derive.key
        self._derive = derive

        rb = RuleBank()  # issue[16]: check for duplicate derivation rules
        if self.table in rb.orm_objects:
            rules_for_this_class = rb.orm_objects[self.table].rules
            if rules_for_this_class is not None:
                if len(rules_for_this_class) > 0:
                    for each_rule in rules_for_this_class:
                        if isinstance(each_rule, Derivation) and each_rule._column == self._column:
                            raise Exception(f"Duplicate Derivation rule for {self.table}.{self._column}")

    def get_derived_attribute_name(self):
        return self.table + "." + self._column


    def __str__(self):
        return f'Derive {self.table}.{self._column} as '
