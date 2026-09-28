# coding: utf-8
"""
Schema for the pessimistic-locking / multi-child-adjust regression suite -
GitHub issue #36 (https://github.com/valhuber/LogicBank/issues/36) and
system/LogicBank-Internal-Dev/pessimistic-locking-issues-36-37.md.

Customer/Order, single-column FK: two Orders for the same Customer, summed
into Customer.balance, committed in the SAME flush - trans_update_locking
="pessimistic" must not let the second child's locking read on Customer
discard the first child's (not-yet-flushed) adjustment.
"""

from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Customer(Base):
    __tablename__ = 'customer'

    id = Column(Integer, primary_key=True)
    name = Column(Integer)  # exercised as a client-edited column (see test)
    balance = Column(Numeric(10, 2), server_default="0")

    order_list: Mapped[List["Order"]] = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = 'order_'

    id = Column(Integer, primary_key=True)
    customer_id = Column(ForeignKey('customer.id'))
    amount = Column(Numeric(10, 2))

    customer: Mapped["Customer"] = relationship("Customer", back_populates="order_list")
