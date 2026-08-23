# coding: utf-8
"""
Minimal schema for the TRANS_UPDATE_LOCKING regression suite (see
internal_dev/locking_strategy.md in ApiLogicServer-src for full background).

This is the framework's own flagship example, deliberately unchanged so the
scenario maps 1:1 onto the doc's Section 3 walkthrough:

    Rule.sum(derive=Customer.balance, as_sum_of=Order.amount_total, where=lambda row: row.date_shipped is None)
    Rule.constraint(validate=Customer, as_condition=lambda row: row.balance <= row.credit_limit)

Two concurrent Order inserts, each individually within the customer's remaining
credit headroom, can - under the unlocked default (TRANS_UPDATE_LOCKING=ignored) -
each read the same stale Customer.balance before either writes, so BOTH commit
successfully even though their combined total exceeds credit_limit.
"""

from sqlalchemy import Column, DECIMAL, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Customer(Base):
    __tablename__ = 'customer'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), nullable=False)
    balance = Column(DECIMAL(10, 2), server_default="0")
    credit_limit = Column(DECIMAL(10, 2), nullable=False)

    OrderList: Mapped[List["Order"]] = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    customer_id = Column(ForeignKey('customer.id'), nullable=False)
    amount_total = Column(DECIMAL(10, 2), server_default="0")
    date_shipped = Column(String(10), nullable=True)  # None = unshipped (included in balance)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="OrderList")
