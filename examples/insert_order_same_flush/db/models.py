# coding: utf-8
"""
Schema for the insert-order-same-flush regression suite - GitHub issue #35
(https://github.com/valhuber/LogicBank/issues/35) and
system/LogicBank-Internal-Dev/insert-order-same-flush-issue-35.md.

Order/OrderDetail, matching the issue's own repro shape: Order.apply_tax is a
formula computed from the order itself, OrderDetail.apply_tax is a formula
that copies it via row.Order.apply_tax. When both rows are added in the same
flush, the child's formula must run AFTER the parent's - which depends on
`RowSets.client_inserts` preserving the order rows were added in.
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    apply_tax = Column(Integer)
    OrderDetailList = relationship('OrderDetail', back_populates='Order')


class OrderDetail(Base):
    __tablename__ = 'order_detail'

    id = Column(Integer, primary_key=True)
    order_id = Column(ForeignKey('order.id'))
    apply_tax = Column(Integer)
    Order = relationship('Order', back_populates='OrderDetailList')
