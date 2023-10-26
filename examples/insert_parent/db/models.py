# coding: utf-8

from logic_bank import logic_bank  # import this first - import ordering

# import sqlalchemy_utils
from sqlalchemy import Boolean, Column, DECIMAL, DateTime, Float, ForeignKey, Integer, LargeBinary, String, \
    UniqueConstraint, select, func, ForeignKeyConstraint
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.testing import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

Base = declarative_base()
metadata = Base.metadata

print("hello")
class Parent(Base):
    """
    https://docs.sqlalchemy.org/en/14/orm/cascades.html
    The default behavior of cascade is limited to cascades of the so-called
    save-update and merge settings.
    The typical “alternative” setting for cascade is to
    add the delete and delete-orphan options;
    these settings are appropriate for related objects which only exist
    as long as they are attached to their parent, and are otherwise deleted.

    #unitofwork-cascades.
    The all symbol is a synonym for
    save-update, merge, refresh-expire, expunge, delete,
    and using it in conjunction with delete-orphan indicates that
    the child object should follow along with its parent in all cases,
    and be deleted once it is no longer associated with that parent.
    """
    __tablename__ = 'Parent'

    parent_attr_1 = Column(String(16), primary_key=True)
    parent_attr_2 = Column(String(16), primary_key=True)
    child_sum = Column(Integer)
    child_count = Column(Integer)

    ChildList = relationship("Child"
                             , backref="Parent"
                             , cascade="all"  # cascade delete
                             # , passive_deletes=True  use *only* when DBMS does the cascade delete
                             # for LogicBank delete logic
                             , cascade_backrefs=True
                             )
    ChildOrphanList = relationship("ChildOrphan"
                                   , backref="Parent"
                                   , cascade="save-update, merge, refresh-expire, expunge"
                                   # no delete option means "nullify"
                                   , cascade_backrefs=True
                                   )


class Child(Base):
    __tablename__ = 'ChildTable'

    child_key = Column(String(16), primary_key=True)
    parent_1 = Column(String(16))
    parent_2 = Column(String(16))
    summed = Column(Integer)
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