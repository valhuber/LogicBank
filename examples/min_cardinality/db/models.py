# coding: utf-8
"""
Minimal schema for the CommitConstraint regression suite (see
system/LogicBank-Internal-Dev/commit-constraint.md and
logic_bank/rule_type/constraint.py).

Order <-> OrderDetail: a classic min-cardinality scenario. "Order must have
at least one OrderDetail" cannot be expressed with a plain Rule.constraint on
Order - Order's own insert is processed before its OrderDetails exist in the
same transaction, so a mid-cascade check on ItemCount always sees 0 at that
point. Rule.commit_constraint defers the check to after the transaction's
cascade has settled.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    notes = Column(String(80))

    item_count = Column(Integer, server_default="0")

    OrderDetailList: Mapped[List["OrderDetail"]] = relationship(
        "OrderDetail", back_populates="order", cascade="all, delete-orphan")


class OrderDetail(Base):
    __tablename__ = 'order_detail'

    id = Column(Integer, primary_key=True)
    order_id = Column(ForeignKey('order.id'), nullable=False)
    product_name = Column(String(40), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="OrderDetailList")
