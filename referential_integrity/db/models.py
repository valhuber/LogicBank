# coding: utf-8

from logic_bank import logic_bank  # import this first - import ordering

import sqlalchemy_utils
from sqlalchemy import Boolean, Column, DECIMAL, DateTime, Float, ForeignKey, Integer, LargeBinary, String, \
    UniqueConstraint, select, func, ForeignKeyConstraint
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.testing import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

Base = declarative_base()
metadata = Base.metadata


class Parent(Base):
    """
    https://docs.sqlalchemy.org/en/13/orm/cascades.html#unitofwork-cascades
    The all symbol is a synonym for
    save-update, merge, refresh-expire, expunge, delete,
    and using it in conjunction with delete-orphan indicates that
    the child object should follow along with its parent in all cases,
    and be deleted once it is no longer associated with that parent.
    """
    __tablename__ = 'Parent'

    parent_attr_1 = Column(String(16), primary_key=True)
    parent_attr_2 = Column(String(16), primary_key=True)

    ChildList = relationship("Child"
                             , backref="Parent"
                             , cascade="delete"  # cascade delete
                             , cascade_backrefs=True
                             )
    ChildOrphanList = relationship("ChildOrphan"
                                   , backref="Parent"
                                   # cascade nullify
                                   , cascade_backrefs=True
                                   )


class Child(Base):
    __tablename__ = 'Child'

    child_key = Column(String(16), primary_key=True)
    parent_1 = Column(String(16))
    parent_2 = Column(String(16))
    __table_args__ = (ForeignKeyConstraint([parent_1, parent_2],
                                           [Parent.parent_attr_1, Parent.parent_attr_2]),
                      {})



class ChildOrphan(Base):
    __tablename__ = 'ChildOrphan'

    child_key = Column(String(16), primary_key=True)
    parent_1 = Column(String(16))
    parent_2 = Column(String(16))
    __table_args__ = (ForeignKeyConstraint([parent_1, parent_2],
                                           [Parent.parent_attr_1, Parent.parent_attr_2]),
                      {})