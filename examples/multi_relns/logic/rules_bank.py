from logic_bank.logic_bank import Rule
from examples.multi_relns.db.models import Department, Employee


def declare_logic():
    """
    Multi-relationship regression rules - see
    system/LogicBank-Internal-Dev/multi-relationship-bug.md for full background.

    Department <-> Employee via two distinct relationships (works_for, on_loan).

    Sum/Count, one of each per role - exercises issue #20 (Rule.sum previously
    ignored child_role_name when 2+ relationships target the same parent class;
    Rule.count was unaffected).
    """
    Rule.sum(derive=Department.works_for_salary_total, as_sum_of=Employee.salary,
             child_role_name="EmployeeWorksForList")
    Rule.sum(derive=Department.on_loan_salary_total, as_sum_of=Employee.salary,
             child_role_name="EmployeeOnLoanList")
    Rule.count(derive=Department.works_for_count, as_count_of=Employee,
               child_role_name="EmployeeWorksForList")
    Rule.count(derive=Department.on_loan_count, as_count_of=Employee,
               child_role_name="EmployeeOnLoanList")

    """
    Live reference (Rule.formula) on the on_loan role - parent changes cascade.
    Exercises get_referring_children() multi-relationship disambiguation.
    """
    Rule.formula(derive=Employee.on_loan_dept_name_live,
                 as_expression=lambda row: row.on_loan_dept.name if row.on_loan_dept else None)

    """
    NOTE: Rule.copy(derive=Employee.works_for_dept_name_copy, from_parent=Department.name)
    is deliberately NOT declared here.

    Rule.copy has no child_role_name / role disambiguation parameter at all (unlike
    Rule.sum/Rule.count) - declaring it against this schema raises:
        LBActivateException: [Exception('TODO / copy - disambiguate relationship')]
    See test_copy_ambiguous.py, which asserts this exception is raised (documenting
    the current, honestly-unfinished state) rather than silently working around it.
    """
