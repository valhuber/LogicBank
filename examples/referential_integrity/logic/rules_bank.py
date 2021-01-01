from logic_bank.logic_bank import Rule
from examples.referential_integrity.db.models import Parent, Child


def declare_logic():

    Rule.parent_check(validate=Child, error_msg="no parent", enable=True)

    Rule.constraint(validate=Parent,
                    as_condition=lambda row: row.parent_attr_1 != "hello",
                    error_msg="Ensure other tables ok")
