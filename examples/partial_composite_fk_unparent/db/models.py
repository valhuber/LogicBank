# coding: utf-8
"""
Schema for the partial-composite-fk-unparent regression suite - GitHub issue
#34 (https://github.com/valhuber/LogicBank/issues/34) and
system/LogicBank-Internal-Dev/partial-composite-fk-unparent-issue-34.md.

MenuOption is self-referencing, chained to its parent by the composite key
(app, parent_id): `app` also identifies the row itself (part of the primary
key) and is never nulled, `parent_id` is the only column that gets nulled when
an option becomes top-level. Rule.count sums the children onto sub_count -
which is what surfaced Aggregate._fk_is_null misreading a partially-null
composite FK as "parent not found" on the UPDATE path.
"""

from sqlalchemy import Column, Integer, String, and_
from sqlalchemy.orm import foreign, relationship, remote
from sqlalchemy.ext.declarative import declarative_base

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class MenuOption(Base):
    """Menu options, chained to their parent option by (app, parent_id)."""
    __tablename__ = 'menu_option'

    app = Column(String(20), primary_key=True)  # part of the key AND of the FK
    id = Column(String(20), primary_key=True)
    parent_id = Column(String(20))              # the only column that gets nulled
    sub_count = Column(Integer)


MenuOption.ChildList = relationship(
    MenuOption,
    primaryjoin=and_(MenuOption.app == remote(foreign(MenuOption.app)),
                     MenuOption.id == remote(foreign(MenuOption.parent_id))),
    back_populates='Parent',
    passive_deletes='all')
MenuOption.Parent = relationship(
    MenuOption,
    primaryjoin=and_(foreign(MenuOption.app) == remote(MenuOption.app),
                     foreign(MenuOption.parent_id) == remote(MenuOption.id)),
    back_populates='ChildList')
