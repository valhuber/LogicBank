# coding: utf-8
"""
Schema for the cascade-delete / multiple-parent-tables regression suite -
GitHub issue #38 (https://github.com/valhuber/LogicBank/issues/38) and
system/LogicBank-Internal-Dev/cascade-delete-is-in-list-issue-38.md.

Order cascade-deletes to OrderLine, whose qty is summed into BOTH
Order.qty_total and Product.qty_sold - matching the issue's own repro shape,
with deliberately different primary-key column names (id_order / id_product)
so the unfixed code raises AttributeError rather than silently under-adjusting.
"""

from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Product(Base):
    __tablename__ = 'product'

    id_product = Column(Integer, primary_key=True)
    qty_sold = Column(Numeric(10, 2), server_default="0")

    order_line_list: Mapped[List["OrderLine"]] = relationship("OrderLine", back_populates="product")


class Order(Base):
    __tablename__ = 'order_'

    id_order = Column(Integer, primary_key=True)
    qty_total = Column(Numeric(10, 2), server_default="0")

    order_line_list: Mapped[List["OrderLine"]] = relationship(
        "OrderLine", back_populates="order", cascade="all, delete", passive_deletes=True)


class OrderLine(Base):
    __tablename__ = 'order_line'

    id_line = Column(Integer, primary_key=True)
    id_order = Column(ForeignKey('order_.id_order'))
    id_product = Column(ForeignKey('product.id_product'))
    qty = Column(Numeric(10, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="order_line_list")
    product: Mapped["Product"] = relationship("Product", back_populates="order_line_list")
