from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.hybrid import hybrid_property

from logic_bank import engine_logger, logic_logger
from logic_bank.rule_type.abstractrule import AbstractRule
from logic_bank.rule_bank.rule_bank import RuleBank


class Derivation(AbstractRule):

    def __init__(self, derive: InstrumentedAttribute):
        # names = derive.split('.')
        self._derive = derive
        self._column = ''
        if isinstance(derive, str):
            self._load_error = "'derive' attribute not a class.attribute: " + str(derive)
        else:
            if not isinstance(derive, InstrumentedAttribute) and not isinstance(derive.descriptor, hybrid_property):
                self._load_error = "'derive' attribute not a class.attribute: " + str(derive)
            # raise Exception("'derive' attribute not a class.attribute: " + str(derive))
        wants_to_be_class = "Not a class"
        if hasattr(derive, "class_") == True:
            wants_to_be_class = derive.class_
        else:
            wants_to_be_class = derive
            pass # not a class, try to proceed to return all errors; AbsractRule logs self._load_error
        super(Derivation, self).__init__(wants_to_be_class)  # got here for sum

        if self._load_error:
            pass # FIXME logic_logger.log("Derivation fails to load", self._load_error)
        else:
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
        invalid = ""
        if self._load_error is not None:
            invalid =  self._load_error + " "
        wants_to_be_class = "Not a class"
        if hasattr(self._derive, "class_") == True:
            wants_to_be_class = self._derive.class_
        else:
            wants_to_be_class = self._derive
            pass # not a class, try to proceed to return all errors; AbsractRule logs self._load_error
        return f'{invalid}Derive {wants_to_be_class}.{self._column} as '
