# coding: utf-8
"""
Schema for the sum-dequalify regression suite - GitHub issue #27
(https://github.com/valhuber/LogicBank/issues/27) and
system/LogicBank-Internal-Dev/sum-dequalify-decrement.md.

Order/OrderLine, matching the issue's own repro shape: OrderLine.amount is a
Rule.formula that depends on discount, and Order.undiscounted_total is a
Rule.sum of OrderLine.amount where discount == 0 - so the same update that
changes discount (the where-clause attribute) also changes amount (the
summed attribute).
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'order'

    id_order = Column(Integer, primary_key=True)
    undiscounted_total = Column(Integer, server_default="0")

    order_line_list: Mapped[List["OrderLine"]] = relationship("OrderLine", back_populates="order")


class OrderLine(Base):
    __tablename__ = 'order_line'

    id_order_line = Column(Integer, primary_key=True)
    id_order = Column(ForeignKey('order.id_order'))
    qty = Column(Integer)
    price = Column(Integer)
    discount = Column(Integer, server_default="0")
    amount = Column(Integer)

    order: Mapped["Order"] = relationship("Order", back_populates="order_line_list")
