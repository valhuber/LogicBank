from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.logic_bank import Rule
from nw.db.models import Customer, OrderDetail, Product, Order, OrderClass


def declare_logic():
    """
    Issues function calls to activate check credit rules, below.
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

    Activate these rules like this

    LogicBank.activate(session=session, activator=declare_logic)
    """

    def units_in_stock(row: Product, old_row: Product, logic_row: LogicRow):
        result = row.UnitsInStock - (row.UnitsShipped - old_row.UnitsShipped)
        return result

    def congratulate_sales_rep(row: Order, old_row: Order, logic_row: LogicRow):
        if logic_row.ins_upd_dlt == "ins" or True:  # logic engine fills parents for insert
            sales_rep = row.SalesRep  # type : Employee
            if sales_rep is None:
                logic_row.log("no salesrep for this order")
            else:
                logic_row.log(f'Hi, {sales_rep.Manager.FirstName}, congratulate {sales_rep.FirstName} on their new order')

    Rule.constraint(validate=Customer,
                    as_condition=lambda row: row.Balance <= row.CreditLimit,
                    error_msg="balance ({row.Balance}) exceeds credit ({row.CreditLimit})")
    Rule.sum(derive=Customer.Balance, as_sum_of=Order.AmountTotal,
             where=lambda row: row.ShippedDate is None)  # *not* a sql select sum...

    Rule.sum(derive=Order.AmountTotal, as_sum_of=OrderDetail.Amount)

    Rule.formula(derive=OrderDetail.Amount, as_expression=lambda row: row.UnitPrice * row.Quantity)
    Rule.copy(derive=OrderDetail.UnitPrice, from_parent=Product.UnitPrice)

    Rule.commit_row_event(on_class=Order, calling=congratulate_sales_rep)

    Rule.formula(derive=OrderDetail.ShippedDate, as_exp="row.OrderHeader.ShippedDate")

    Rule.sum(derive=Product.UnitsShipped, as_sum_of=OrderDetail.Quantity,
             where="row.ShippedDate is not None")
    Rule.formula(derive=Product.UnitsInStock, calling=units_in_stock)

    Rule.count(derive=Customer.UnpaidOrderCount, as_count_of=Order,
             where=lambda row: row.ShippedDate is None)  # *not* a sql select sum...

    Rule.count(derive=Customer.OrderCount, as_count_of=Order)

    Rule.constraint(validate=OrderClass,
                    as_condition=lambda row: row.Id <= 99999,
                    error_msg="Test constraint for className <> tableName")


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

