# coding: utf-8
"""
Schema for the insert_parent-partially-null-composite-FK regression suite -
GitHub issue #29 (https://github.com/valhuber/LogicBank/issues/29) and
system/LogicBank-Internal-Dev/insert-parent-partial-null-fk.md.

Stock/SaleLine, matching the issue's own repro shape: Stock has a composite
natural key (product_id, store_id); SaleLine.product_id is nullable (a
free-text line has no product) while store_id is always set. This is
distinct from examples/insert_parent_late_key (#26): there, every composite-key
column is EVENTUALLY set (by an early_row_event) before the aggregate adjusts.
Here, product_id legitimately stays null forever - there is no parent to
create or adjust, and insert_parent must not be attempted.
"""

from sqlalchemy import Column, ForeignKeyConstraint, Integer
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Stock(Base):
    """ One row per product and store - composite natural key. """
    __tablename__ = 'stock'

    product_id = Column(Integer, primary_key=True)
    store_id = Column(Integer, primary_key=True)
    sold = Column(Integer, server_default="0")

    sale_line_list: Mapped[List["SaleLine"]] = relationship("SaleLine", back_populates="stock")


class SaleLine(Base):
    """ A free-text line has no product: product_id is null, store_id is not. """
    __tablename__ = 'sale_line'

    id_sale_line = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=True)
    store_id = Column(Integer)
    qty = Column(Integer)
    __table_args__ = (ForeignKeyConstraint(['product_id', 'store_id'],
                                           ['stock.product_id', 'stock.store_id']),)

    stock: Mapped["Stock"] = relationship("Stock", back_populates="sale_line_list")
