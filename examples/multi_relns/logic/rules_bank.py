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
    Live reference (Rule.formula) on BOTH roles - parent changes cascade independently.
    Exercises get_referring_children() multi-relationship disambiguation (rule_bank_withdraw.py)
    - previously, only the LAST-declared relationship's referring children survived, so only one
    of these two formulas would ever cascade correctly. See multi-relationship-bug.md "A third
    direction" / Status section.
    """
    Rule.formula(derive=Employee.on_loan_dept_name_live,
                 as_expression=lambda row: row.on_loan_dept.name if row.on_loan_dept else None)
    Rule.formula(derive=Employee.works_for_dept_name_live,
                 as_expression=lambda row: row.works_for_dept.name if row.works_for_dept else None)

    """
    Rule.copy snapshot, disambiguated via child_role_name (now supported - see test_copy_ambiguous.py
    for the pre-fix ambiguity-detection behavior, still verified for the no-child_role_name case).
    """
    Rule.copy(derive=Employee.works_for_dept_name_copy, from_parent=Department.name,
              child_role_name="works_for_dept")
