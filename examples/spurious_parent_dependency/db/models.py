# coding: utf-8
"""
Schema for the spurious-parent-dependency regression suite - GitHub issue #21
(https://github.com/valhuber/LogicBank/issues/21) and
system/LogicBank-Internal-Dev/spurious-parent-dependency.md.

Customer/Item, matching the issue's own repro shape: Item.code is a plain
column whose chained method call (row.code.zfill(8)) used to be misparsed as
a parent reference; Customer has a real relationship (item_list) to
contrast against.
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

    id_customer = Column(Integer, primary_key=True)
    name = Column(String(50))
    unknown_customer = Column(Integer, server_default="0")

    item_list: Mapped[List["Item"]] = relationship("Item", back_populates="customer")


class Item(Base):
    __tablename__ = 'item'

    id_item = Column(Integer, primary_key=True)
    id_customer = Column(ForeignKey('customer.id_customer'))
    code = Column(String(20))
    padded_code = Column(String(20))
    price = Column(DECIMAL(10, 2), server_default="0")

    customer: Mapped["Customer"] = relationship("Customer", back_populates="item_list")
