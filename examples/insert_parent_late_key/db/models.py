# coding: utf-8
"""
Same shape as examples/insert_parent, but Child.period (part of the composite FK to
Parent) is NOT set at construction time - it is set by an early_row_event, like a
real-world computed key component (e.g. a year_month bucket key derived from a date).

This reproduces the case examples/insert_parent's own test does not cover: when a
composite-FK column is still null at the moment LogicRow._load_parents_on_insert()
first runs (before early_row_events fire), _is_foreign_key_null() correctly defers
insert_parent - and the aggregate adjustment that runs later (once the FK is fully
set) must itself be able to trigger insert_parent. See
internal_dev/composite_key_issue/composite_key_issue.md (ApiLogicServer-src) for the
full investigation and the real-world case (a sales-rep monthly rollup) that
surfaced this.
"""

from logic_bank import logic_bank  # import this first - import ordering

from sqlalchemy import Column, ForeignKeyConstraint, Integer, String, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from sqlalchemy.orm import Mapped

Base = declarative_base()
metadata = Base.metadata


class Parent(Base):
    """ Composite natural-key parent - eg, a per-rep-per-month rollup bucket. """
    __tablename__ = 'Parent'

    parent_attr_1 = Column(String(16), primary_key=True)  # eg, sales_rep_id
    period = Column(String(16), primary_key=True)          # eg, year_month
    child_sum = Column(Integer, server_default="0")
    child_count = Column(Integer, server_default="0")

    ChildList: Mapped[List["Child"]] = relationship("Child",
                             back_populates="Parent",
                             cascade="all")


class Child(Base):
    """ Child.period is set by an early_row_event (like an order's year_month
    bucket key, computed from order_date) - never present at Child() construction
    time, unlike examples/insert_parent's Child.parent_2. """
    __tablename__ = 'ChildTable'

    child_key = Column(String(16), primary_key=True)
    parent_1 = Column(String(16))
    period = Column(String(16))  # set later, by early_row_event - NOT at construction
    summed = Column(Integer)
    __table_args__ = (ForeignKeyConstraint([parent_1, period],
                                           [Parent.parent_attr_1, Parent.period]),
                      {})

    # parent relationships (access parent)
    Parent: Mapped["Parent"] = relationship("Parent", back_populates="ChildList")
