import os
from shutil import copyfile

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import session

from logic_bank.logic_bank import LogicBank
from banking.logic.rules_bank import activate_basic_rules

from logic_bank.util import prt

""" Initialization
1 - Connect
2 - Register listeners (either hand-coded ones above, or the logic-engine listeners).
"""

# Initialize Logging
import logging
import sys

logic_logger = logging.getLogger('logic_logger')  # for users
logic_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
handler.setFormatter(formatter)
logic_logger.addHandler(handler)

do_engine_logging = False  # TODO move to config file, reconsider level
engine_logger = logging.getLogger('engine_logger')  # for internals
if do_engine_logging:
    engine_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    engine_logger.addHandler(handler)

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

banking_loc = basedir + "/db/database.db"
banking_source = basedir + "/db/database-gold.db"

conn_string = "sqlite:///" + banking_loc
engine = sqlalchemy.create_engine(conn_string,
                                  pool_pre_ping= True,
                                  echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

rule_list = None
db = None
LogicBank.activate(session=session, activator=activate_basic_rules)
print("\n" + prt("session created, listeners registered\n"))

