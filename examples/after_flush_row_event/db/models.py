# coding: utf-8

from logic_bank import logic_bank  # import this first - import ordering

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Order(Base):
    """ Mirrors the basic_demo Order.date_shipped / Kafka-on-ship scenario from the bug report """
    __tablename__ = 'Order'

    id = Column(Integer, primary_key=True)
    amount_total = Column(Integer, server_default="0")
    date_shipped = Column(DateTime, nullable=True)
    notes = Column(String(64), nullable=True)
