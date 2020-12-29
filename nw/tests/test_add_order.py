import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="nw.tests.test_add_order")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import nw.tests as tests  # careful - this must follow add_python_path, above

    tests.copy_gold_over_db()

    import nw.db.models as models

    from nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    from logic_bank.exec_row_logic.logic_row import LogicRow  # must follow import of models
    from logic_bank.util import prt, row_prt, ConstraintException

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
        session.expunge(pre_cust)


        """
            Test 1 - should fail due to credit limit exceeded
        """

        bad_order = models.Order(AmountTotal=0, CustomerId="ALFKI", ShipCity="Richmond",
                                 EmployeeId=6, Freight=1)
        session.add(bad_order)

        # OrderDetails - https://docs.sqlalchemy.org/en/13/orm/backref.html
        bad_item1 = models.OrderDetail(ProductId=1, Amount=0,
                                       Quantity=1, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item1)
        bad_item2 = models.OrderDetail(ProductId=2, Amount=0,
                                       Quantity=20000, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item2)
        did_fail_as_expected = False
        try:
            session.commit()
        except ConstraintException as ce:
            print("Expected constraint: " + str(ce))
            session.rollback()
            did_fail_as_expected = True
        except:
            self.fail("Unexpected Exception Type")

        if not did_fail_as_expected:
            self.fail("huge order expected to fail, but succeeded")
        else:
            print("\n" + prt("huge order failed credit check as expected.  Now trying non-commissioned order, should also fail..."))

        """
            Test 2 - should fail due to not-commissioned
        """

        bad_order = models.Order(AmountTotal=0, CustomerId="ALFKI", ShipCity="Richmond",
                                 EmployeeId=2, Freight=1)
        session.add(bad_order)

        # OrderDetails - https://docs.sqlalchemy.org/en/13/orm/backref.html
        bad_item1 = models.OrderDetail(ProductId=1, Amount=0,
                                       Quantity=1, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item1)
        bad_item2 = models.OrderDetail(ProductId=2, Amount=0,
                                       Quantity=2, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item2)
        did_fail_as_expected = False
        try:
            session.commit()
        except ConstraintException:
            session.rollback()
            did_fail_as_expected = True
        except:
            print("Unexpected Exception Type")

        if not did_fail_as_expected:
            self.fail("order for non-commissioned expected to fail, but succeeded")
        else:
            print("\n" + prt("non-commissioned order failed constraint as expected.  Now trying invalid customer, should fail..."))

        """
            Test 3 - should fail due to invalid customer
        """

        bad_order = models.Order(AmountTotal=0, CustomerId="XX INVALID CUSTOMER", ShipCity="Richmond",
                                 EmployeeId=6, Freight=1)
        session.add(bad_order)

        # OrderDetails - https://docs.sqlalchemy.org/en/13/orm/backref.html
        bad_item1 = models.OrderDetail(ProductId=1, Amount=0,
                                       Quantity=1, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item1)
        bad_item2 = models.OrderDetail(ProductId=2, Amount=0,
                                       Quantity=2, UnitPrice=18,
                                       Discount=0)
        bad_order.OrderDetailList.append(bad_item2)
        did_fail_as_expected = False
        try:
            session.commit()
        except ConstraintException as ce:
            session.rollback()
            did_fail_as_expected = True
            print(str(ce))
        except:
            session.rollback()
            did_fail_as_expected = True
            e = sys.exc_info()[0]
            print(e)

        if not did_fail_as_expected:
            self.fail("order for invalid customer expected to fail, but succeeded")
        else:
            print("\n" + prt("invalid customer failed as expected.  Now trying valid order, should succeed..."))

        """
            Test 4 - should succeed
        """

        new_order = models.Order(AmountTotal=0, CustomerId="ALFKI", ShipCity="Richmond",
                                 EmployeeId=6, Freight=1)
        session.add(new_order)

        # OrderDetails - https://docs.sqlalchemy.org/en/13/orm/backref.html
        new_item1 = models.OrderDetail(ProductId=1, Amount=0,
                                       Quantity=1, UnitPrice=18,
                                       Discount=0)
        new_order.OrderDetailList.append(new_item1)
        new_item2 = models.OrderDetail(ProductId=2, Amount=0,
                                       Quantity=2, UnitPrice=18,
                                       Discount=0)
        new_order.OrderDetailList.append(new_item2)
        session.commit()

        post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

        print("\nadd_order, update completed - analyzing results..\n\n")

        row_prt(new_order, session, "\nnew Order Result")  # $18 + $38 = $56
        if new_order.AmountTotal != 56:
            self.fail(row_prt(new_order, "Unexpected AmountTotal: " + str(new_order.AmountTotal) +
                   "... expected 56"))
        row_prt(new_item1, session, "\nnew Order Detail 1 Result")  # 1 Chai  @ $18
        row_prt(new_item2, session, "\nnew Order Detail 2 Result")  # 2 Chang @ $19 = $38

        logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
        if post_cust.Balance == pre_cust.Balance + 56:
            logic_row.log("Correct adjusted Customer Result")
            assert True
        else:
            self.fail(logic_row.log("ERROR - incorrect adjusted Customer Result"))

        if post_cust.OrderCount == pre_cust.OrderCount + 1 and\
            post_cust.UnpaidOrderCount == pre_cust.UnpaidOrderCount + 1:
            pass
        else:
            self.fail(logic_row.log("Error - unexpected OrderCounts - did not increase by 1"))

        from sqlalchemy.sql import func
        qry = session.query(models.Order.CustomerId,
                            func.sum(models.Order.AmountTotal).label('sql_balance'))\
            .filter(models.Order.CustomerId == "ALFKI", models.Order.ShippedDate == None)
        qry = qry.group_by(models.Order.CustomerId).one()
        if qry.sql_balance == post_cust.Balance:
            logic_row.log("Derived balance matches sql `select sum' result: " + str(post_cust.Balance))
        else:
            self.fail(logic_row.log("ERROR - computed balance does not match sql result"))

        print("\nadd_order, ran to completion\n\n")
        self.assertTrue(True)
