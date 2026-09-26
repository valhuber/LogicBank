# coding: utf-8
"""
Schema for the formula-no-python_type regression suite - GitHub issue #32
(https://github.com/valhuber/LogicBank/issues/32) and
system/LogicBank-Internal-Dev/formula-no-python-type-issue-32.md.

Item.is_active is a MySQL BIT(1) column, whose SQLAlchemy type does not
implement `python_type` (raises NotImplementedError). Rule.formula derives it
from Item.code; when the derived value does not change (True -> True), the old
code path read `.type.python_type` unconditionally to check for a stray float,
crashing the commit for column types that don't support it.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import BIT
from sqlalchemy.ext.declarative import declarative_base

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    code = Column(String(20))
    is_active = Column(BIT(1))  # MySQL BIT: type.python_type raises NotImplementedError
