import datetime
import os
from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule

from examples.nw.db.models import Customer, OrderDetail, Product, Order, OrderClass, Employee, EmployeeAudit, Department

from examples.nw.logic.extensibility.nw_rule_extensions import NWRuleExtension


def declare_logic():
    """
    Issues function calls to activate rules for check credit (etc), below.
        These rules are executed not now, but on commits
        Order is irrelevant - determined by system based on dependency analysis
        Their inclusion in classes is for doc / convenience, no semantics

    These rules apply to all transactions (automatic re-use), eg.
    * place order
    * change Order Detail product, quantity
    * add/delete Order Detail
    * ship / unship order
    * delete order
    * move order to new customer, etc

    Activate rules like this

        LogicBank.activate(session=session, activator=declare_logic)
    """
    test_bad_rules = os.getenv('LOAD_BAD_RULES')
    if test_bad_rules:
        print('loading bad rules')
        if use_strings := True:
            '''
            Rule.constraint(validate='CustomerBadConstraint',
                            as_condition=lambda row: row.Balance <= row.CreditLimitConstraintBadAttr,
                            error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
            '''
            # Rule.sum(derive='Customer.CreditLimitYY', as_sum_of='Order.AmountTotalTT', where=lambda row: row.BalWhereWorseAttr is None)
            # Rule.count(derive='Customer.IdNoCount', as_count_of='OrderNoCount', where=lambda row: row.WorstAttr is None)

            # missing attr tests
            Rule.sum(derive='Customer.CreditLimit', as_sum_of='Order.AmountTotal', where=lambda row: row.BalWhereWorseAttr is None)
            Rule.count(derive='Customer.Count', as_count_of='Order', where=lambda row: row.WorstAttr is None)
            Rule.constraint(validate='Customer',
                            as_condition=lambda row: row.Balance <= row.CreditLimitConstraintBadAttr,
                            error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
        else:
            Rule.constraint(validate=CustomerYY,
                            as_condition=lambda row: row.Balance <= row.CreditLimitConstraintBadAttr,
                            error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
            Rule.sum(derive=Customer.CreditLimitYY, as_sum_of=Order.AmountTotal, where=lambda row: row.WorseAttr is None)
            Rule.count(derive=Customer.IdX, as_count_of=Order, where=lambda row: row.WorstAttr is None)


    def congratulate_sales_rep(row: Order, old_row: Order, logic_row: LogicRow):
        if logic_row.ins_upd_dlt == "ins":  # logic engine fills parents for insert
            sales_rep = row.SalesRep  # type : Employee
            if sales_rep is None:
                logic_row.log("no salesrep for this order")
            else:
                logic_row.log(f'Hi, {sales_rep.Manager.FirstName}, congratulate {sales_rep.FirstName} on their new order')

    Rule.constraint(validate=Customer,
                    as_condition=lambda row: (row.Balance <= row.CreditLimit),
                    error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
             where=lambda row: row.ShippedDate is None or row.ShippedDate == '')  # *not* a sql select sum...
#    Rule.sum(derive=Customer.Balance, as_sum_of=OrderDetail.Amount,
#             where=lambda row: row.ShippedDate is None)  # test bad rule definition

    Rule.sum(derive=Order.AmountTotal, as_sum_of=OrderDetail.Amount)

    Rule.formula(derive=OrderDetail.Amount, as_expression=lambda row: row.UnitPrice * row.Quantity)
    Rule.copy(derive=OrderDetail.UnitPrice, from_parent=Product.UnitPrice)

    Rule.commit_row_event(on_class=Order, calling=congratulate_sales_rep)

    Rule.formula(derive=OrderDetail.ShippedDate, as_exp="row.OrderHeader.ShippedDate")

    Rule.sum(derive=Department.SalaryTotal, as_sum_of=Employee.Salary, child_role_name="EmployeeWorksForList")
    Rule.count(derive=Department.OnLoanCount, as_count_of=Employee, child_role_name="EmployeeOnLoanList")
    Rule.count(derive=Department.WorksForCount, as_count_of=Employee, child_role_name="EmployeeWorksForList")

    def units_in_stock(row: Product, old_row: Product, logic_row: LogicRow):
        result = row.UnitsInStock - (row.UnitsShipped - old_row.UnitsShipped)
        return result
    Rule.sum(derive=Product.UnitsShipped, as_sum_of=OrderDetail.Quantity,
             where= lambda row: row.ShippedDate is not None and row.ShippedDate  != '')
            #"row.ShippedDate is not None or row.ShippedDate != ''")

    Rule.formula(derive=Product.UnitsInStock, calling=units_in_stock)

    Rule.count(derive=Customer.UnpaidOrderCount, as_count_of=Order,
             where=lambda row: row.ShippedDate is None or row.ShippedDate == '')  # *not* a sql select sum...

    Rule.count(derive=Customer.OrderCount, as_count_of=Order)

    Rule.constraint(validate=OrderClass,
                    as_condition=lambda row: row.Id <= 99999,
                    error_msg="Test constraint for className <> tableName")

    Rule.constraint(validate=Employee,
                    as_condition=lambda row: row.IsCommissioned == 1 or row.order_count == 0,
                    error_msg="{row.LastName} is not commissioned ({row.IsCommissioned}) - cannot have orders ({row.order_count})")

    Rule.count(derive=Employee.order_count, as_count_of=Order)

    def raise_over_20_percent(row: Employee, old_row: Employee, logic_row: LogicRow):
        if logic_row.ins_upd_dlt == "upd" and row.Salary != old_row.Salary:
            return row.Salary >= Decimal('1.20') * old_row.Salary
        else:
            return True

    Rule.constraint(validate=Employee,
                    calling=raise_over_20_percent,
                    error_msg="{row.LastName} needs a more meaningful raise")

    def audit_by_event(row: Employee, old_row: Employee, logic_row: LogicRow):
        tedious = False  # tedious code to repeat for every audited class
        if tedious:      # see instead the following rule extension - nw_copy_row
            if logic_row.are_attributes_changed([Employee.Salary, Employee.Title]):
                copy_to_logic_row = logic_row.new_logic_row(EmployeeAudit)
                copy_to_logic_row.link(to_parent=logic_row)
                copy_to_logic_row.set_same_named_attributes(logic_row)
                copy_to_logic_row.insert(reason="Manual Copy " + copy_to_logic_row.name)  # triggers rules...
                # logic_row.log("audit_by_event (Manual Copy) complete")

    Rule.commit_row_event(on_class=Employee, calling=audit_by_event)

    """ also provided in system version
    RuleExtension.copy(copy_from=Employee,
                       copy_to=EmployeeAudit,
                       copy_when=lambda logic_row: logic_row.are_attributes_changed([Employee.Salary, Employee.Title]))
    """

    NWRuleExtension.nw_copy_row(copy_from=Employee,
                                copy_to=EmployeeAudit,
                                copy_when=lambda logic_row:
                                    logic_row.are_attributes_changed([Employee.Salary, Employee.Title]))

    def handle_all(logic_row: LogicRow):
        row = logic_row.row
        if logic_row.ins_upd_dlt == "ins" and hasattr(row, "CreatedOn"):
            row.CreatedOn = datetime.datetime.now()
            logic_row.log("early_row_event_all_classes - handle_all sets 'Created_on"'')

    Rule.early_row_event_all_classes(early_row_event_all_classes=handle_all)


class InvokePythonFunctions:  # use functions for more complex rules, type checking, etc (not used)

    @staticmethod
    def load_rules(self):

        def my_early_event(row, old_row, logic_row):
            logic_row.log("early event for *all* tables - good breakpoint, time/date stamping, etc")

        def check_balance(row: Customer, old_row, logic_row) -> bool:
            """
            Not used... illustrate function alternative (e.g., more complex if/else logic)
            specify rule with `calling=check_balance` (instead of as_condition)
            """
            return row.Balance <= row.CreditLimit

        def compute_amount(row: OrderDetail, old_row, logic_row):
            return row.UnitPrice * row.Quantity

        Rule.formula(derive="OrderDetail.Amount", calling=compute_amount)

        Rule.formula(derive="OrderDetail.Amount", calling=lambda Customer: Customer.Quantity * Customer.UnitPrice)

        Rule.early_row_event(on_class="*", calling=my_early_event)  # just for debug

        Rule.constraint(validate="Customer", calling=check_balance,
                        error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")


class DependencyGraphTests:
    """Not loaded"""

    def not_loaded(self):
        Rule.formula(derive="Tbl.ColA",  # or, calling=compute_amount)
                     as_exp="row.ColB + row.ColC")

        Rule.formula(derive="Tbl.ColB",  # or, calling=compute_amount)
                     as_exp="row.ColC")

        Rule.formula(derive="Tbl.ColC",  # or, calling=compute_amount)
                     as_exp="row.ColD")

        Rule.formula(derive="Tbl.ColD",  # or, calling=compute_amount)
                     as_exp="row.ColE")

        Rule.formula(derive="Tbl.ColE",  # or, calling=compute_amount)
                     as_exp="xxx")

