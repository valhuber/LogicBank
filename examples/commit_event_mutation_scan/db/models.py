# coding: utf-8
"""
Minimal single-table schema for the RowEvent/CommitRowEvent mutation-scan
regression suite - see logic_bank/rule_type/row_event.py's
AbstractRowEvent._check_row_mutation() and
system/LogicBank-Internal-Dev/commit-event-mutation-gap.md.

No relationships needed - this suite tests activation-time scanning
(LBActivateException), not the rule cascade itself.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    notes = Column(String(80))
    item_count = Column(Integer, server_default="0")
