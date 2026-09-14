# coding: utf-8
"""
Schema for the copy-null-parent regression suite - GitHub issue #28
(https://github.com/valhuber/LogicBank/issues/28) and
system/LogicBank-Internal-Dev/copy-null-parent.md.

Product/OrderLine, matching the issue's own repro shape: OrderLine.product_id
is nullable (a free-text line has no product), and Rule.copy propagates
Product.tax_rate onto OrderLine.tax_rate.
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Product(Base):
    __tablename__ = 'product'

    id_product = Column(Integer, primary_key=True)
    tax_rate = Column(Integer)


class OrderLine(Base):
    __tablename__ = 'order_line'

    id_order_line = Column(Integer, primary_key=True)
    id_product = Column(ForeignKey('product.id_product'), nullable=True)  # free-text lines have no product
    tax_rate = Column(Integer)

    product: Mapped[Optional["Product"]] = relationship("Product")
