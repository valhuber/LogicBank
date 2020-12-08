import os
import sqlalchemy
from sqlalchemy.orm import session


class DB:
    """
    Opens the database

    Sets instance variables session, engine
    """
    def __init__(self):
        # def open_database() -> (sqlalchemy.orm.session.Session, sqlalchemy.engine.base.Engine):
        basedir = os.path.abspath(os.path.dirname(__file__))
        basedir = os.path.dirname(basedir)

        nw_loc = os.path.join(basedir, "db/database.db")

        conn_string = "sqlite:///" + nw_loc
        self.engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

        session_maker = sqlalchemy.orm.sessionmaker()
        session_maker.configure(bind=self.engine)
        self.session = session_maker()
