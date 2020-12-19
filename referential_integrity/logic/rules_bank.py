from logic_bank.logic_bank import Rule
from logic_bank.rule_type.parent_cascade import ParentCascadeAction
from referential_integrity.db.models import Parent, Child, ChildOrphan


def declare_logic():

    Rule.parent_check(validate=Child, error_msg="no parent", enable=True)

    Rule.constraint(validate=Parent,
                    as_condition=lambda row: row.parent_attr_1 != "hello",
                    error_msg="Ensure other tables ok")

    Rule.parent_cascade(validate=Parent, relationship="ChildList", action=ParentCascadeAction.DELETE)

    Rule.parent_cascade(validate=Parent, relationship="ChildOrphanList", action=ParentCascadeAction.NULLIFY)
