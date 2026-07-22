import os
from shutil import copyfile

import sqlalchemy

from logic_bank.logic_bank import LogicBank
from logic_bank.util import prt
from datetime import datetime


def copy_gold_over_db():
    """ copy db/database-gold.db over db/database.db"""

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - copy_gold_over_db: copy db/database.db from db/database-gold.db in " + basedir + "/min_cardinality/db/\n" +
          "            - from -- " + prt("") + " at: " + str(datetime.now()) +
          "\n********************************")

    db_loc = os.path.join(basedir, "db/database.db")
    db_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=db_source, dst=db_loc)


def new_session_from_gold():
    """ Copy gold over db, then build a FRESH engine/session with LogicBank activated.

    Each test method gets a genuinely fresh engine+session+activate() cycle (not
    just a fresh file underneath a stale connection) - see multi_relns/tests/__init__.py
    for the full rationale.

    Returns (session, engine) - caller's tearDown should session.close(); engine.dispose().
    """
    copy_gold_over_db()

    from examples.min_cardinality.logic.rules_bank import declare_logic

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)
    db_loc = os.path.join(basedir, "db/database.db")

    engine = sqlalchemy.create_engine("sqlite:///" + db_loc, echo=False)
    session_maker = sqlalchemy.orm.sessionmaker()
    session_maker.configure(bind=engine)
    session = session_maker()

    LogicBank.activate(session=session, activator=declare_logic,
                        aggregate_defaults=True, all_defaults=False)
    return session, engine


def setUp(file: str):
    """ banner only - callers needing a fresh session should use new_session_from_gold() """
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
    :param engine: eg, from new_session_from_gold()
    :param session: eg, from new_session_from_gold()
    :return:
    """
    session.close()
    engine.dispose()
    print("\n")
    print("**********************")
    print("** Test complete, SQLAlchemy session/engine closed for: " + file)
    print("** Started: " + started_at + " Ended: " + str(datetime.now()))
    print("**********************")
