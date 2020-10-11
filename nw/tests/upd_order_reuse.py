"""
PyCharm sets PythonPath to the root folder, VSC does not by default - imports fail
Hence, add this to the launch config:
"env": {"PYTHONPATH": "${workspaceFolder}:${env:PYTHONPATH}"}

ref: https://stackoverflow.com/questions/53653083/how-to-correctly-set-pythonpath-for-visual-studio-code
"""

import os
import sys
from datetime import datetime
from decimal import Decimal

from sqlalchemy import inspect

cwd = os.getcwd()   # eg, /Users/val/python/pycharm/logic-bank/nw/tests
required_path_python_rules = cwd  # seeking /Users/val/python/pycharm/logic-bank
required_path_python_rules = required_path_python_rules.replace("/nw/tests", "")
required_path_python_rules = required_path_python_rules.replace("\\nw\\tests", "")
required_path_python_rules = required_path_python_rules.replace("\\\\", "\\")  # you cannot be serious

sys_path = ""
required_path_present = False
for each_node in sys.path:
    sys_path += each_node + "\n"
    if each_node == required_path_python_rules:
        required_path_present = True

if not required_path_present:
    print("Fixing path (so can run from terminal)")
    sys.path.append(required_path_python_rules)
else:
    pass
    print("NOT Fixing path (default PyCharm, set in VSC Launch Config)")

run_environment_info = "Run Environment info...\n\n"
run_environment_info += " Current Working Directory: " + cwd + "\n\n"
run_environment_info += "sys.path: (Python imports)\n" + sys_path + "\n"
run_environment_info += "From: " + sys.argv[0] + "\n\n"
run_environment_info += "Using Python: " + sys.version + "\n\n"
run_environment_info += "At: " + str(datetime.now()) + "\n\n"

print("\n" + run_environment_info + "\n\n")
from nw.tests import setup_db  # careful - this must follow fix-path, above
setup_db()

import nw.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.util import prt
from nw.logic import session  # opens db, activates logic listener <--


""" 
Illustrate re-use with a number of changes:
    1 - reassign the order to a different customer
    2 - change an OrderDetail (eg, "I'll buy 1 WidgetSet, not 5 Widgets")
        a. A different Product
        b. A different Quantity
"""

pre_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
pre_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()

logic_row = LogicRow(row=pre_alfki, old_row=pre_alfki,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
logic_row.log("starting")

logic_row = LogicRow(row=pre_anatr, old_row=pre_anatr,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
logic_row.log("starting")

pre_order = session.query(models.Order).filter(models.Order.Id == 11011).one()  # type : Order
logic_row = LogicRow(row=pre_order, old_row=pre_order,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
logic_row.log("starting")
session.expunge(pre_alfki)
session.expunge(pre_anatr)
session.expunge(pre_order)

print("")

test_order = session.query(models.Order).filter(models.Order.Id == 11011).one()  # type : Order
test_order_details = test_order.OrderDetailList
changed_order_detail = None
for each_order_detail in test_order_details:
    if each_order_detail.ProductId == 58:  # Escargots de Bourgogne, @ $13.25
        each_order_detail.ProductId = 48   # Chocolade, @ $12.75
        each_order_detail.Quantity = 10    # 40 x 13.25 => 10 x 12.75
        break

pre_amount_total = test_order.AmountTotal
post_amount_total = pre_amount_total -\
                    Decimal(40.0) * Decimal(13.25) +\
                    Decimal(10.0) * Decimal(12.75)

test_order.CustomerId = "ANATR"

print("\n" + prt("Reparenting *altered* order - new CustomerId: " + test_order.CustomerId))
print(f'order amount {pre_amount_total} projected to be {post_amount_total}')
insp = inspect(test_order)

session.commit()
print('')

msg = 'Committed... order.amountTotal ' + \
      str(pre_amount_total) + ' -> ' + \
      str(post_amount_total)
logic_row = LogicRow(row=test_order, old_row=pre_order,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
logic_row.log(msg)
print("\n")


post_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
logic_row = LogicRow(row=post_alfki, old_row=pre_alfki,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if post_alfki.Balance == 56:
    logic_row.log("Correct non-adjusted Customer Result")
    assert True
else:
    print("\n*** ERROR***")
    msg = "ERROR - incorrect adjusted Customer Result, " + "should be 56"
    logic_row.log(msg)
    assert False

post_anatr = session.query(models.Customer).filter(models.Customer.Id == "ANATR").one()
logic_row = LogicRow(row=post_anatr, old_row=pre_anatr,
                     ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if post_anatr.Balance == 557.50:
    logic_row.log("Correct non-adjusted Customer Result")
    assert True
else:
    print("\n*** ERROR***")
    msg = "ERROR - incorrect adjusted Customer Result, " + "should be 557.50"
    logic_row.log(msg)
    assert False

print("\nupd_order_customer_reuse, ran to completion")

"""
This test uncovered a dragon - a serious and subtle bug.
    Other resources: see....
        logic_bank/exec_row_logic/logic_row#save_altered_parents
        logic_bank/exec_trans_logic/listeners

The origin of the bug is that listener dirty rows are not returned in defined order.
    The symptom was that the tests would fail about half the time.
    Under one of the scenarios, the sum adjustment would be incorrect.
        See the log excerpts below.
    In the failed run, OrderDetail is processed first.
        But the Order is the "new" row (ANATR), so we incorrectly adjusted that.
    The fix was to
        1 - denote all "submitted" rows in RowSets
        2 - defer adjustments if parent in submitted rows (with a log statement to that effect)

In order to test and make the execution reliably choose the wrong path,
use the following code in logic_bank/exec_trans_logic/listeners
and rem

    bug_explore = [None, None]   # None (vs [None, None]) means don't activate the bug-catching logic
    if bug_explore is not None:  # temp hack - order rows to explore bug (upd_order_reuse)
        temp_debug(a_session, bug_explore, row_sets)
    else:
        for each_instance in a_session.dirty:
            table_name = each_instance.__tablename__
            old_row = get_old_row(each_instance)
            logic_row = LogicRow(row=each_instance, old_row=old_row, ins_upd_dlt="upd",
                                 nest_level=0, a_session=a_session, row_sets=row_sets)
            logic_row.update(reason="client")    
    
Failed run:
    @upd_order_reuse.py#<module>(): Reparenting *altered* order - new CustomerId: ANATR
    order amount 960.0000000000 projected to be 557.5000000000
    Logic Phase (sqlalchemy before_flush)			 - 2020-09-20 19:26:16,279 - logic_logger - DEBUG
    ..OrderDetail[1972] {Update - client} Amount: 530.0000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice: 13.2500000000  row@: 0x105f620d0 - 2020-09-20 19:26:16,281 - logic_logger - DEBUG
    ..OrderDetail[1972] {copy_rules for role: ProductOrdered} Amount: 530.0000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice: 13.2500000000  row@: 0x105f620d0 - 2020-09-20 19:26:16,282 - logic_logger - DEBUG
    ..OrderDetail[1972] {Formula Amount} Amount:  [530.0000000000-->] 127.5000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice:  [13.2500000000-->] 12.7500000000  row@: 0x105f620d0 - 2020-09-20 19:26:16,289 - logic_logger - DEBUG
    ..OrderDetail[1972] {Prune Formula: ShippedDate [['OrderHeader.ShippedDate']]} Amount:  [530.0000000000-->] 127.5000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice:  [13.2500000000-->] 12.7500000000  row@: 0x105f620d0 - 2020-09-20 19:26:16,290 - logic_logger - DEBUG
    ....Order[11011] {Update - Adjusting OrderHeader} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId: ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x105f4eb80 - 2020-09-20 19:26:16,291 - logic_logger - DEBUG
    ......Customer[ANATR] {Update - Adjusting Customer} Address: Avda. de la Constitución 2222, Balance:  [0E-10-->] -402.5000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x105f7e880 - 2020-09-20 19:26:16,295 - logic_logger - DEBUG
                    ^
                    -- that's it... adjusting the new (wrong) customer, works when Order goes first (below)

    reparent order (upd_order_customer) worked...
    ..Order[11011] {Update - client} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x105f4eb80 - 2020-09-20 19:26:16,298 - logic_logger - DEBUG
    ....Customer[ANATR] {Update - Adjusting Customer} Address: Avda. de la Constitución 2222, Balance:  [-402.5000000000-->] 155.0000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x105f7e880 - 2020-09-20 19:26:16,303 - logic_logger - DEBUG
    ....Customer[ALFKI] {Update - Adjusting Customer} Address: Obere Str. 57, Balance:  [960.0000000000-->] 0E-10, City: Berlin, CompanyName: Alfreds Futterkiste, ContactName: Maria Anders, ContactTitle: Sales Representative, Country: Germany, CreditLimit: 2000.0000000000, Fax: 030-0076545, Id: ALFKI, Phone: 030-0074321, PostalCode: 12209, Region: Western Europe  row@: 0x105f7e5b0 - 2020-09-20 19:26:16,304 - logic_logger - DEBUG
    Commit Logic Phase   			 - 2020-09-20 19:26:16,305 - logic_logger - DEBUG
    ....Order[11011] {Commit Event} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId: ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x105f4eb80 - 2020-09-20 19:26:16,305 - logic_logger - DEBUG
    ....Order[11011] {Hi, Andrew, congratulate Janet on their new order} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId: ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x105f4eb80 - 2020-09-20 19:26:16,316 - logic_logger - DEBUG
    Flush Phase          			 - 2020-09-20 19:26:16,316 - logic_logger - DEBUG
    ..Order[11011] {Committed... order.amountTotal 960.0000000000 -> 557.5000000000} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x105f4eb80 - 2020-09-20 19:26:16,333 - logic_logger - DEBUG
    ..Customer[ALFKI] {Correct non-adjusted Customer Result} Address: Obere Str. 57, Balance:  [960.0000000000-->] 0E-10, City: Berlin, CompanyName: Alfreds Futterkiste, ContactName: Maria Anders, ContactTitle: Sales Representative, Country: Germany, CreditLimit: 2000.0000000000, Fax: 030-0076545, Id: ALFKI, Phone: 030-0074321, PostalCode: 12209, Region: Western Europe  row@: 0x105f7e5b0 - 2020-09-20 19:26:16,336 - logic_logger - DEBUG
    *** ERROR***
    ..Customer[ANATR] {ERROR - incorrect adjusted Customer Result, should be 1362.50} Address: Avda. de la Constitución 2222, Balance:  [0E-10-->] 155.0000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x105f7e880 - 2020-09-20 19:26:16,339 - logic_logger - DEBUG
    python-BaseException
    Traceback (most recent call last):
      File "/Applications/PyCharm CE.app/Contents/plugins/python-ce/helpers/pydev/pydevd.py", line 1448, in _exec
        pydev_imports.execfile(file, globals, locals)  # execute the script
      File "/Applications/PyCharm CE.app/Contents/plugins/python-ce/helpers/pydev/_pydev_imps/_pydev_execfile.py", line 18, in execfile
        exec(compile(contents+"\n", file, 'exec'), glob, loc)
      File "/Users/val/python/pycharm/logic-bank/nw/tests/upd_order_reuse.py", line 136, in <module>
        assert False
    AssertionError

Good run:
    @__init__.py#<module>(): session created, listeners registered

    ..Customer[ALFKI] {starting} Address: Obere Str. 57, Balance: 960.0000000000, City: Berlin, CompanyName: Alfreds Futterkiste, ContactName: Maria Anders, ContactTitle: Sales Representative, Country: Germany, CreditLimit: 2000.0000000000, Fax: 030-0076545, Id: ALFKI, Phone: 030-0074321, PostalCode: 12209, Region: Western Europe  row@: 0x105074100 - 2020-09-20 19:36:30,581 - logic_logger - DEBUG
    ..Customer[ANATR] {starting} Address: Avda. de la Constitución 2222, Balance: 0E-10, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x105074970 - 2020-09-20 19:36:30,582 - logic_logger - DEBUG
    /Users/val/python/pycharm/logic-bank/venv/lib/python3.8/site-packages/sqlalchemy/sql/sqltypes.py:661: SAWarning: Dialect sqlite+pysqlite does *not* support Decimal objects natively, and SQLAlchemy must convert from floating point - rounding errors and other issues may occur. Please consider storing Decimal numbers as strings or integers on this platform for lossless storage.
      util.warn(
    ..Order[11011] {starting} AmountTotal: 960.0000000000, CustomerId: ALFKI, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbb50 - 2020-09-20 19:36:30,590 - logic_logger - DEBUG


    @upd_order_reuse.py#<module>(): Reparenting *altered* order - new CustomerId: ANATR
    order amount 960.0000000000 projected to be 557.5000000000

    Logic Phase (sqlalchemy before_flush)			 - 2020-09-20 19:36:30,601 - logic_logger - DEBUG
    ..Order[11011] {Update - client} AmountTotal: 960.0000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbc40 - 2020-09-20 19:36:30,602 - logic_logger - DEBUG
    ....Customer[ANATR] {Update - Adjusting Customer} Address: Avda. de la Constitución 2222, Balance:  [0E-10-->] 960.0000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x1050cf460 - 2020-09-20 19:36:30,611 - logic_logger - DEBUG
    ....Customer[ALFKI] {Update - Adjusting Customer} Address: Obere Str. 57, Balance:  [960.0000000000-->] 0E-10, City: Berlin, CompanyName: Alfreds Futterkiste, ContactName: Maria Anders, ContactTitle: Sales Representative, Country: Germany, CreditLimit: 2000.0000000000, Fax: 030-0076545, Id: ALFKI, Phone: 030-0074321, PostalCode: 12209, Region: Western Europe  row@: 0x1050cfa00 - 2020-09-20 19:36:30,613 - logic_logger - DEBUG
    ..OrderDetail[1972] {Update - client} Amount: 530.0000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice: 13.2500000000  row@: 0x1050cf190 - 2020-09-20 19:36:30,616 - logic_logger - DEBUG
    ..OrderDetail[1972] {copy_rules for role: ProductOrdered} Amount: 530.0000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice: 13.2500000000  row@: 0x1050cf190 - 2020-09-20 19:36:30,616 - logic_logger - DEBUG
    ..OrderDetail[1972] {Formula Amount} Amount:  [530.0000000000-->] 127.5000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice:  [13.2500000000-->] 12.7500000000  row@: 0x1050cf190 - 2020-09-20 19:36:30,623 - logic_logger - DEBUG
    ..OrderDetail[1972] {Prune Formula: ShippedDate [['OrderHeader.ShippedDate']]} Amount:  [530.0000000000-->] 127.5000000000, Discount: 0.05, Id: 1972, OrderId: 11011, ProductId:  [58-->] 48, Quantity:  [40-->] 10, ShippedDate: None, UnitPrice:  [13.2500000000-->] 12.7500000000  row@: 0x1050cf190 - 2020-09-20 19:36:30,623 - logic_logger - DEBUG
    ....Order[11011] {Update - Adjusting OrderHeader} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId: ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbc40 - 2020-09-20 19:36:30,625 - logic_logger - DEBUG
    ......Customer[ANATR] {Update - Adjusting Customer} Address: Avda. de la Constitución 2222, Balance:  [960.0000000000-->] 557.5000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x1050cf460 - 2020-09-20 19:36:30,627 - logic_logger - DEBUG
    Commit Logic Phase   			 - 2020-09-20 19:36:30,628 - logic_logger - DEBUG
    ..Order[11011] {Commit Event} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbc40 - 2020-09-20 19:36:30,628 - logic_logger - DEBUG
    ..Order[11011] {Hi, Andrew, congratulate Janet on their new order} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbc40 - 2020-09-20 19:36:30,641 - logic_logger - DEBUG
    Flush Phase          			 - 2020-09-20 19:36:30,642 - logic_logger - DEBUG

    ..Order[11011] {Committed... order.amountTotal 960.0000000000 -> 557.5000000000} AmountTotal:  [960.0000000000-->] 557.5000000000, CustomerId:  [ALFKI-->] ANATR, EmployeeId: 3, Freight: 1.2100000000, Id: 11011, OrderDate: 2014-04-09, RequiredDate: 2014-05-07, ShipAddress: Obere Str. 57, ShipCity: Berlin, ShipCountry: Germany, ShipName: Alfred's Futterkiste, ShipPostalCode: 12209, ShipRegion: Western Europe, ShipVia: 1, ShippedDate: None  row@: 0x1050bbc40 - 2020-09-20 19:36:30,661 - logic_logger - DEBUG


    ..Customer[ALFKI] {Correct non-adjusted Customer Result} Address: Obere Str. 57, Balance:  [960.0000000000-->] 0E-10, City: Berlin, CompanyName: Alfreds Futterkiste, ContactName: Maria Anders, ContactTitle: Sales Representative, Country: Germany, CreditLimit: 2000.0000000000, Fax: 030-0076545, Id: ALFKI, Phone: 030-0074321, PostalCode: 12209, Region: Western Europe  row@: 0x1050cfa00 - 2020-09-20 19:36:30,666 - logic_logger - DEBUG
    ..Customer[ANATR] {Correct non-adjusted Customer Result} Address: Avda. de la Constitución 2222, Balance:  [0E-10-->] 557.5000000000, City: México D.F., CompanyName: Ana Trujillo Emparedados y helados, ContactName: Ana Trujillo, ContactTitle: Owner, Country: Mexico, CreditLimit: 1000.0000000000, Fax: (5) 555-3745, Id: ANATR, Phone: (5) 555-4729, PostalCode: 05021, Region: Central America  row@: 0x1050cf460 - 2020-09-20 19:36:30,669 - logic_logger - DEBUG

    upd_order_customer_reuse, ran to completion

    Process finished with exit code 0

"""


