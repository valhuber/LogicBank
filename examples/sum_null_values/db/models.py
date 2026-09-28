# coding: utf-8
"""
Schema for the sum-null-values regression suite - GitHub issue #39
(https://github.com/valhuber/LogicBank/issues/39) and
system/LogicBank-Internal-Dev/sum-null-values-issue-39.md.

Customer/Order, matching the issue's own repro shape: Rule.sum of Order.amount
into Customer.balance. amount is nullable - insert already tolerated NULL;
delete, update-to-NULL and reparent (with a NULL summed value) did not.
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
    balance = Column(Numeric(10, 2), server_default="0")

    order_list: Mapped[List["Order"]] = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = 'order_'

    id = Column(Integer, primary_key=True)
    customer_id = Column(ForeignKey('customer.id'))
    amount = Column(Numeric(10, 2), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="order_list")
