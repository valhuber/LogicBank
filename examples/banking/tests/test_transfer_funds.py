from datetime import datetime
from decimal import Decimal
import logging, sys, os
from shutil import copyfile

import sqlalchemy
# import sqlalchemy_utils

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from logic_bank.logic_bank import LogicBank
from logic_bank.util import row_prt, prt
from logic_bank.exec_row_logic.logic_row import LogicRow

import examples.banking.db.models as models

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

from examples.banking.logic.rules_bank import activate_basic_rules
LogicBank.activate(session=session, activator=activate_basic_rules)

pre_cust = session.query(models.CUSTOMER).filter(models.CUSTOMER.CustNum == 1).one()
session.expunge(pre_cust)

"""
    ********* Customer Account Deposit Checking Setup - Deposit $100 to CHECKINGTRANS *********
"""

trans_date = datetime(2020, 10, 1)
deposit = models.CHECKINGTRANS(TransId=1, CustNum=1, AcctNum=1,
                               DepositAmt=100, WithdrawlAmt=0, TransDate=trans_date)
print("\n\nCustomer Account Deposit Checking Setup - Deposit $100 to CHECKINGTRANS ")
session.add(deposit)
session.commit()

print("")
verify_cust = session.query(models.CUSTOMER).filter(models.CUSTOMER.CustNum == 1).one()
logic_row = LogicRow(row=verify_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
if verify_cust.TotalBalance == 100.0:
    logic_row.log("Customer Account Deposit Checking Setup OK - balance is 100")
    assert True
else:
    logic_row.log("Customer Account Deposit Checking Setup OK fails - balance not 100")
    assert False
session.expunge(verify_cust)

"""
    ********* Transfer 10 from checking to savings (main test) *********
"""
transfer = models.TRANSFERFUND(TransId=2, FromCustNum=1, FromAcct=1, ToCustNum=1, ToAcct=1, TransferAmt=10, TransDate=trans_date)
print("\n\nTransfer 10 from checking to savings (main test) ")
session.add(transfer)
session.commit()

print("")
verify_cust = session.query(models.CUSTOMER).filter(models.CUSTOMER.CustNum == 1).one()
logic_row = LogicRow(row=verify_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)
if verify_cust.TotalBalance == 100.0:
    logic_row.log("Transfer 10 from checking to savings ok - balance is 100")
    assert True
else:
    logic_row.log("Transfer 10 from checking to savings fails - balance not 100")
    assert False
session.expunge(verify_cust)

"""
    ********* Overdraft Funds Test *********
"""

print("\n\n********* Overdraft Funds Test ********* Verify constraint makes commit fail")
trasfer2 = models.TRANSFERFUND(TransId=3, FromCustNum=1, FromAcct=1, ToCustNum=1, ToAcct=1, TransferAmt=1000, TransDate=trans_date)
session.add(trasfer2)
did_fail_as_expected = False
try:
    session.commit()
except:
    session.rollback()
    did_fail_as_expected = True

print("")
verify_cust = session.query(models.CUSTOMER).filter(models.CUSTOMER.CustNum == 1).one()
logic_row = LogicRow(row=verify_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

if not did_fail_as_expected:
    logic_row.log("ERROR -overdraft checking expected to fail, but succeeded")
    assert False
else:
    logic_row.log("Overdraft Funds Test properly rolled back invalid transfer")
