"""
One-off to create schema from models.py - no longer used
"""

from examples import banking as models

# https://stackoverflow.com/questions/16284537/sqlalchemy-creating-an-sqlite-database-if-it-doesnt-exist

# engine = create_engine('sqlite:///database.db', echo=True)

Base = models.Base

from examples.banking import logic

Base.metadata.create_all(logic.engine)