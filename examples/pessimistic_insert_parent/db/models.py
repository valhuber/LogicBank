# coding: utf-8
"""
Schema for the pessimistic-locking / insert_parent regression suite - GitHub
issue #30 (https://github.com/valhuber/LogicBank/issues/30) and
system/LogicBank-Internal-Dev/pessimistic-locking-insert-parent.md.

Stock/SaleLine, single-column FK (deliberately simpler than #29's composite
key, to isolate the locking interaction on its own): SaleLine.product_id
references a Stock row that does not exist yet - Rule.sum(insert_parent=True)
must create it, whether trans_update_locking is "ignored" (default) or
"pessimistic".
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Stock(Base):
    __tablename__ = 'stock'

    product_id = Column(Integer, primary_key=True)
    sold = Column(Integer, server_default="0")

    sale_line_list: Mapped[List["SaleLine"]] = relationship("SaleLine", back_populates="stock")


class SaleLine(Base):
    __tablename__ = 'sale_line'

    id_sale_line = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey('stock.product_id'))
    qty = Column(Integer)

    stock: Mapped["Stock"] = relationship("Stock", back_populates="sale_line_list")
