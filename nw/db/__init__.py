import os
import sqlalchemy
# from sqlalchemy.engine import Engine
# from sqlalchemy.orm import session


# db_engine = None  # used globally (e.g., open_db() and destroy_session_and_engine() )
# db_session = None

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

nw_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + nw_loc
db_engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=db_engine)
db_session = session_maker()



def open_db():
    # def open_database() -> (sqlalchemy.orm.session.Session, sqlalchemy.engine.base.Engine):
    global db_engine, db_session
    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    nw_loc = os.path.join(basedir, "db/database.db")

    conn_string = "sqlite:///" + nw_loc
    db_engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

    session_maker = sqlalchemy.orm.sessionmaker()
    session_maker.configure(bind=db_engine)
    db_session = session_maker()
    return (db_session, db_engine)


def destroy_session_and_engine():
    global db_engine, db_session
    db_session.close()
    db_engine.dispose()

    db_session = None
    db_engine = None
    pass
