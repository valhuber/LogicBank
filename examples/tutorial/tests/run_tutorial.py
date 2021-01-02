from decimal import Decimal

import logic_bank_utils.util as logic_bank_utils
from logic_bank.util import row_prt, prt

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")
import os
from shutil import copyfile
# from logic_bank.util import prt


def setup_db():
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

setup_db()

import sqlalchemy_utils

import examples.tutorial.db.models as models
from logic_bank.exec_row_logic.logic_row import LogicRow
from examples.tutorial.logic import session  # opens db, activates logic listener <--

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

print("\nadd_order, update completed\n\n")

logic_row = LogicRow(row=post_cust, old_row=pre_cust, ins_upd_dlt="*", nest_level=0, a_session=session, row_sets=None)

assert post_cust.Balance == pre_cust.Balance + amount_total,\
    "ERROR - incorrect adjusted Customer Result (EXPECTED - now add rules)"

logic_row.log("Correct adjusted Customer Result")

print("\nadd_order, ran to completion\n\n")
