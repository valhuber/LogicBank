from logic_bank.logic_bank import Rule
from examples.insert_parent.db.models import Parent, Child


def declare_logic():

    Rule.parent_check(validate=Child, error_msg="no parent", enable=True)

    Rule.constraint(validate=Parent,
                    as_condition=lambda row: row.parent_attr_1 != "hello",
                    error_msg="Ensure other tables ok")

    do_sum = True
    if do_sum:
        Rule.sum(derive=Parent.child_sum, as_sum_of=Child.summed, insert_parent=True)

    do_count = True # FIXME raises logic_bank.util.ConstraintException: Unable to Adjust Missing Parent: Parent
    if do_count:
        Rule.count(derive=Parent.child_count, as_count_of=Child, insert_parent=True)