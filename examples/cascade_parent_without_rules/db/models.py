# coding: utf-8
"""
Schema for the cascade-parent-without-rules regression suite - GitHub issue #33
(https://github.com/valhuber/LogicBank/issues/33) and
system/LogicBank-Internal-Dev/cascade-parent-without-rules-issue-33.md.

Order/OrderDetail, matching the issue's own repro shape: OrderDetail.shipped_date
is a formula that copies Order.shipped_date, and Order itself has no rules of
its own - which is exactly the case get_referring_children mishandled.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    shipped_date = Column(String(20))
    OrderDetailList = relationship('OrderDetail', back_populates='Order')


class OrderDetail(Base):
    __tablename__ = 'order_detail'

    id = Column(Integer, primary_key=True)
    order_id = Column(ForeignKey('order.id'))
    shipped_date = Column(String(20))
    Order = relationship('Order', back_populates='OrderDetailList')
