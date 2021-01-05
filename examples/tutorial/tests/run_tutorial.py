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

import examples.tutorial.db.models as models

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

from examples.tutorial.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)

pre_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()
session.expunge(pre_cust)

"""
    Create Order row
"""

cust_alfki = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

amount_total = 500  # 500 should work; change to 1000 to see constraint fire

new_order = models.Order(AmountTotal=amount_total)
cust_alfki.OrderList.append(new_order)

session.add(new_order)
session.commit()  # this fires the rules (adjust balance, verify <=2000)

post_cust = session.query(models.Customer).filter(models.Customer.Id == "ALFKI").one()

logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

assert post_cust.Balance == pre_cust.Balance + amount_total,\
    "ERROR - incorrect adjusted Customer Result (EXPECTED - now add rules)"

print("\nNote: log shows that sum rule adjusted balance *up* due to order Insert\n")
logic_row.log("Correct adjusted Customer Result")

show_reuse = True  # set True to observe reuse in console log
if not show_reuse:
    pass
    # print("Reuse example disabled")
else:
    new_order.AmountTotal = new_order.AmountTotal - 10
    session.commit()
    print("\nNote: log shows that sum rule adjusted balance *down* due to order Update")

print("\nadd_order, ran to completion\n\n")
