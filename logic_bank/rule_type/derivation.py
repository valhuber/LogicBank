from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.hybrid import hybrid_property
from logic_bank.rule_type.abstractrule import AbstractRule


class Derivation(AbstractRule):

    def __init__(self, derive: InstrumentedAttribute):
        # names = derive.split('.')
        if not isinstance(derive, InstrumentedAttribute) and \
            not isinstance(derive.descriptor, hybrid_property):
            raise Exception("'derive' attribute not a class.attribute: " + str(derive))
        super(Derivation, self).__init__(derive.class_)
        self._column = derive.key
        self._derive = derive

    def __str__(self):
        return f'Derive {self.table}.{self._column} as '
