from decimal import Decimal
import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from logic_bank.logic_bank import LogicBank
from logic_bank.util import row_prt, prt
from logic_bank.exec_row_logic.logic_row import LogicRow

import examples.payment_allocation.db.models as models

def copy_db_from_gold():
    """ copy db/database-gold.db over db/database.db"""
    print("\n" + prt("restoring database-gold\n"))

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - create database.db from database-gold.db in " + basedir + "/payment_allocation/db/\n" +
          "            - from -- " + prt("") +
          "\n********************************")

    db_loc = os.path.join(basedir, "db/database.db")
    db_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=db_source, dst=db_loc)

def setup_logging():
    logic_logger = logging.getLogger('logic_logger')  # for debugging user logic
    logic_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    logic_logger.addHandler(handler)

    do_engine_logging = False
    engine_logger = logging.getLogger('engine_logger')  # for internals
    if do_engine_logging:
        engine_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
        handler.setFormatter(formatter)
        engine_logger.addHandler(handler)

setup_logging()
copy_db_from_gold()

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

db_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + db_loc
engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

from examples.payment_allocation.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)

pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
session.expunge(pre_cust)


"""
    Test 1 - create allocation row
"""

cust_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

new_payment = models.Payment(Amount=1000)
cust_alfki.PaymentList.append(new_payment)

session.add(new_payment)
session.commit()

post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

print("\nadd_payment, update completed\n\n")
row_prt(new_payment, "\nnew Payment Result")  #
if new_payment.Amount != Decimal(1000):
    print ("==> ERROR - unexpected new_payment.Amount: " + str(new_payment.Amount) +
           "... expected 1000")
else:
    print()

# Check SQLAlchemy version and test PaymentAllocation creation
sqlalchemy_version = sqlalchemy.__version__
print(f"\nSQLAlchemy version: {sqlalchemy_version}")

if sqlalchemy_version.startswith('2.'):
    print("SQLAlchemy 2.0: Testing PaymentAllocation creation")
    
    # Query PaymentAllocations created for this payment
    payment_allocations = session.query(models.PaymentAllocation)\
        .filter(models.PaymentAllocation.PaymentId == new_payment.Id).all()
    
    total_allocated = sum(pa.AmountAllocated for pa in payment_allocations)
    
    print(f"PaymentAllocations created: {len(payment_allocations)}")
    print(f"Total allocated amount: {total_allocated}")
    
    if len(payment_allocations) > 0:
        print("SUCCESS: PaymentAllocations were created and persisted to database")
        for i, pa in enumerate(payment_allocations):
            order = session.query(models.Order).filter(models.Order.Id == pa.OrderId).one()
            print(f"  Allocation {i+1}: ${pa.AmountAllocated} to Order {pa.OrderId} (OrderDate: {order.OrderDate})")
        
        # Verify allocation logic worked correctly
        if total_allocated == Decimal(1000):
            print("SUCCESS: Total allocation amount matches payment amount")
        else:
            print(f"WARNING: Total allocation ${total_allocated} != payment amount $1000")
    else:
        print("ERROR: No PaymentAllocations were created")
        print("CRITICAL: LogicBank allocation extension may need fixes for SQLAlchemy 2.0 compatibility")
        
elif sqlalchemy_version.startswith('1.'):
    print("SQLAlchemy 1.4: Testing PaymentAllocation creation (legacy mode)")
    payment_allocations = session.query(models.PaymentAllocation)\
        .filter(models.PaymentAllocation.PaymentId == new_payment.Id).all()
    print(f"PaymentAllocations created: {len(payment_allocations)}")
    if len(payment_allocations) > 0:
        print("SUCCESS: PaymentAllocations working in SQLAlchemy 1.4")
        total_allocated = sum(pa.AmountAllocated for pa in payment_allocations)
        print(f"Total allocated amount: {total_allocated}")
    else:
        print("ERROR: PaymentAllocations not working in SQLAlchemy 1.4")
else:
    print(f"Unknown SQLAlchemy version: {sqlalchemy_version}")
    payment_allocations = session.query(models.PaymentAllocation)\
        .filter(models.PaymentAllocation.PaymentId == new_payment.Id).all()
    print(f"PaymentAllocations created: {len(payment_allocations)}")

"""
    (10653 owes nothing)
    orderId OrderDate   AmountTotal AmountPaid  AmountOwed  ==> Allocated
    10692   2013-10-03  878         778         100         100
    10702   2013-10-03  330         0           330         330
    10835   2014-01-15  851         0           851         570
    10952   2014-03-16  491.20      0           491.20      *
    11011   2014-04-09  960         0           960         *
"""

logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
if post_cust.Balance == pre_cust.Balance - 1000:  # 1016 -> 16  ?? 794
    logic_row.log("Correct adjusted Customer Result")
    assert True
else:
    logic_row.log("ERROR - Balance not reduced 1000")
    assert False, "Balance not reduced 1000"
print("\nadd_payment, ran to completion\n\n")
