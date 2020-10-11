import os

import sqlalchemy
from sqlalchemy.orm import session

from logic_bank.logic_bank import LogicBank
from logic_bank.rule_bank import rule_bank_withdraw  # FIXME design why required to avoid circular imports??
# from logic_bank.rule_bank import logic_bank_setup
from nw.logic.rules_bank import declare_logic

import nw.logic.legacy.setup as legacy_setup

from logic_bank.util import prt

""" Initialization
1 - Connect
2 - Register listeners (either hand-coded ones above, or the logic-engine listeners).
"""

print("\n" + prt("BEGIN - setup logging, connect to db, register listeners"))

# Initialize Logging
import logging
import sys

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

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

nw_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + nw_loc
engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

by_rules = True  # True => use rules, False => use legacy hand code (for comparison)
rule_list = None
db = None
if by_rules:
    LogicBank.activate(session=session, activator=declare_logic)
else:
    legacy_setup.setup(session)  # test asserts fail due to counts (else ok)

print("\n" + prt("END - connected, session created, listeners registered\n"))
