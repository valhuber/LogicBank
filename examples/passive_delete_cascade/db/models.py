# coding: utf-8
"""
Schema for the passive_deletes cascade-delete regression suite - GitHub issue #22
(https://github.com/valhuber/LogicBank/issues/22) and
system/LogicBank-Internal-Dev/passive-delete-cascade-typo.md.

Order/OrderDetail with cascade="all, delete" AND passive_deletes=True - the
combination that routes deletes through LogicRow._cascade_delete_children()
(DBMS enforces the cascade via ON DELETE CASCADE, not SQLAlchemy) rather than
through the normal client-delete path in listeners.py.
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    amount_total = Column(Integer, server_default="0")

    OrderDetailList: Mapped[List["OrderDetail"]] = relationship(
        "OrderDetail", back_populates="order",
        cascade="all, delete", passive_deletes=True)


class OrderDetail(Base):
    __tablename__ = 'order_details'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'))
    amount = Column(Integer, server_default="0")

    order: Mapped["Order"] = relationship("Order", back_populates="OrderDetailList")
