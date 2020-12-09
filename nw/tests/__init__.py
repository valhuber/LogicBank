import os
from shutil import copyfile

import sqlalchemy

from logic_bank.util import prt
from datetime import datetime


def copy_gold_over_db():
    """ copy db/database-gold.db over db/database.db"""

    # import time
    # time.sleep(1)

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - copy_gold_over_db: copy db/database.db from db/database-gold.db in " + basedir + "/nw/db/\n" +
          "            - from -- " + prt("") + " at: " + str(datetime.now()) +
          "\n********************************")

    nw_loc = os.path.join(basedir, "db/database.db")
    nw_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=nw_source, dst=nw_loc)

def setup_logging():
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


def setUp(test: object, file: str):
    """
    SETUP - logging, connect to db, register listeners, activate logic
    """

    print("\n")
    print("*********************")
    print("BEGIN SETUP - logging, connect to db, register listeners, activate logic")
    print("*********************")

    copy_gold_over_db()

    setup_logging()

    from logic_bank.logic_bank import LogicBank
    from nw.logic.rules_bank import declare_logic

    import nw.logic.legacy.setup as legacy_setup

    import nw.db as open_db
    test.db = open_db.DB()
    test.session = test.db.session
    test.engine = test.db.engine

    by_rules = True  # True => use rules, False => use legacy hand code (for comparison)
    if by_rules:
        LogicBank.activate(session=test.session, activator=declare_logic)
    else:
        legacy_setup.setup(test.session)  # ignore test asserts that fail due to (unimplemented) counts (else ok)

    print("\n")
    print("**********************")
    print("** END SETUP - logging, database and logic are setup")
    print("** Test execution begins for: " + file)
    print("** Session: " + str(test.session))
    print("** Started: " + str(datetime.now()))
    print("** Following log best viewed without word wrap")
    print("**********************")
    print("\n")


def tearDown(test: object, file: str):
    """
    close session & engine, banner

    :param file: caller, usually __file__
    :param started_at: eg, str(datetime.now())
    :param test: test instance
    :return:
    """
    test.session.close()
    test.engine.dispose()
    print("\n")
    print("**********************")
    print("** Test tearDown complete, SQLAlchemy session/engine closed for: " + file)
    print("** Session: " + str(test.session))
    print("** Started: " + test.started_at + " Ended: " + str(datetime.now()))
    print("**********************")
