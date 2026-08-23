import sys, unittest
import logic_bank_utils.util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.concurrent_adjust.tests.test_for_update_sql")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Tier 1.5 (see internal_dev/locking_strategy.md, ApiLogicServer-src): pure SQL-compilation
    check, NO database connection at all (no engine.connect(), no live Postgres, no Docker) -
    milliseconds to run, same speed class as every other LogicBank test.

    What this proves: when TRANS_UPDATE_LOCKING=pessimistic, LogicBank's parent-fetch query
    (logic_row.py's _get_parent_logic_row) actually COMPILES to include a FOR UPDATE clause
    when rendered against the Postgres dialect - i.e. LogicBank genuinely ASKS the database to
    lock the row. This is the one thing under this codebase's control to verify.

    What this does NOT prove: that a live Postgres server actually GRANTS/HONORS that lock by
    blocking a second concurrent writer. That is Postgres's and SQLAlchemy's own long-established,
    externally-documented contract - not a novel claim this codebase introduces - so it is
    deliberately NOT re-verified here via a live connection. See locking_strategy.md's Tier 2
    for why a live-Postgres/real-thread test is documented, not built.

    This test compiles the query directly via SQLAlchemy's public compile() API against
    dialect objects (sqlalchemy.dialects.postgresql.dialect(), sqlalchemy.dialects.sqlite.dialect())
    - these are pure Python SQL-rendering rule objects, not connections.
    """

    def test_with_for_update_compiles_to_FOR_UPDATE_on_postgres_dialect(self):
        """ The exact with_for_update().populate_existing() shape used by
        logic_row.py's _get_parent_logic_row (under TRANS_UPDATE_LOCKING=pessimistic)
        must render literal "FOR UPDATE" when compiled against the Postgres dialect.
        """
        from sqlalchemy import create_engine, Column, Integer, String
        from sqlalchemy.orm import sessionmaker, declarative_base
        from sqlalchemy.dialects import postgresql

        Base = declarative_base()

        class Customer(Base):
            __tablename__ = 'customer_for_update_check'
            id = Column(Integer, primary_key=True)
            balance = Column(String)

        # in-memory SQLite engine used ONLY to build a real Session/Query object to compile from -
        # no query is ever executed against it; compilation targets the postgres dialect explicitly
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        query = session.query(Customer).filter_by(id=1).with_for_update().populate_existing()
        compiled_sql = str(query.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

        assert "FOR UPDATE" in compiled_sql, \
            f'Expected with_for_update() to compile to a FOR UPDATE clause under the Postgres ' \
            f'dialect - got: {compiled_sql}'

        session.close()
        engine.dispose()

        print("\n...test_with_for_update_compiles_to_FOR_UPDATE_on_postgres_dialect ran to completion\n\n")

    def test_with_for_update_is_dropped_on_sqlite_dialect(self):
        """ Pins down the documented SQLite limitation (locking_strategy.md Section 5/6):
        the SAME with_for_update() query compiled against the SQLite dialect must NOT contain
        a FOR UPDATE clause - SQLAlchemy's SQLite dialect silently drops it (no error). This is
        the reason Tier 1's interleaved-session test cannot prove real row-locking on SQLite -
        only the fresh-read effect of populate_existing() is observable there (see
        test_interleaved_race.py's test_pessimistic_locking_closes_the_race_even_on_sqlite).

        This test exists so a future SQLAlchemy version that starts emitting SOMETHING for
        SQLite's with_for_update() is caught here as a behavior change, not silently assumed.
        """
        from sqlalchemy import create_engine, Column, Integer, String
        from sqlalchemy.orm import sessionmaker, declarative_base
        from sqlalchemy.dialects import sqlite

        Base = declarative_base()

        class Customer(Base):
            __tablename__ = 'customer_for_update_check_sqlite'
            id = Column(Integer, primary_key=True)
            balance = Column(String)

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        query = session.query(Customer).filter_by(id=1).with_for_update().populate_existing()
        compiled_sql = str(query.statement.compile(
            dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

        assert "FOR UPDATE" not in compiled_sql, \
            f'Expected the SQLite dialect to silently drop with_for_update() (documented ' \
            f'limitation) - got a FOR UPDATE clause: {compiled_sql}. If this assertion now ' \
            f'fails, SQLite/SQLAlchemy behavior has changed - re-read locking_strategy.md ' \
            f'Section 5 before treating this as an improvement.'

        session.close()
        engine.dispose()

        print("\n...test_with_for_update_is_dropped_on_sqlite_dialect ran to completion\n\n")
