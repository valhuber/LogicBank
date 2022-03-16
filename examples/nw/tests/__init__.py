import os
from shutil import copyfile

import sqlalchemy

from logic_bank.util import prt
from datetime import datetime


def copy_gold_over_db():
    """ copy db/database-gold.db over db/database.db"""

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - copy_gold_over_db: copy db/database.db from db/database-gold.db in " + basedir + "/nw/db/\n" +
          "            - from -- " + prt("") + " at: " + str(datetime.now()) +
          "\n********************************")

    nw_loc = os.path.join(basedir, "db/database.db")
    nw_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=nw_source, dst=nw_loc)


def setUp(file: str):
    """ copy gold over db, setup-complete banner
    """
    copy_gold_over_db()

    print("\n")
    print("**********************")
    print("** Setup complete - test execution begins for: " + file)
    print("** Started: " + str(datetime.now()))
    print("** Following log best viewed without word wrap")
    print("**********************")


def tearDown(file: str, started_at: str, engine: sqlalchemy.engine.base.Engine, session: sqlalchemy.orm.session.Session):
    """
    close session & engine, banner

    :param file: caller, usually __file__
    :param started_at: eg, str(datetime.now())
    :param engine: eg, nw.logic import session, engine
    :param session: from nw.logic import session, engine
    :return:
    """
    session.close()
    engine.dispose()
    print("\n")
    print("**********************")
    print("** Test complete, SQLAlchemy session/engine closed for: " + file)
    print("** Started: " + started_at + " Ended: " + str(datetime.now()))
    print("**********************")
