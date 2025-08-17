# coding: utf-8

"""
WARNING: used in logic, but FAB uses version in basic_web_app/app
The primary copy is here -- copy changes to basic_web_app/app.

on relationships...
  * declare them in the parent (not child), eg, for Order:
  *    OrderDetailList = relationship("OrderDetail", back_populates="OrderHeader")

"""

from logic_bank import logic_bank  # import this first - import ordering

# import sqlalchemy_utils
from sqlalchemy import Boolean, Column, DECIMAL, DateTime, Float, ForeignKey, Integer, LargeBinary, String, \
    UniqueConstraint, select, func
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.testing import db
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from typing import List
from sqlalchemy.orm import Mapped

Base = declarative_base()
metadata = Base.metadata



class Customer(Base):
    __tablename__ = 'Customer'

    Id = Column(String(8000), primary_key=True)
    CompanyName = Column(String(8000))
    Balance = Column(DECIMAL(10, 2))
    CreditLimit = Column(DECIMAL(10, 2))

    OrderList : Mapped[List["Order"]] = relationship("Order",
                             back_populates="Customer",
                             cascade="all, delete",
                             passive_deletes=True)  # means database RI will do the deleting

    PaymentList : Mapped[List["Payment"]] = relationship("Payment",
                             back_populates="Customer",
                             cascade="all, delete",
                             passive_deletes=True)  # means database RI will do the deleting


class Payment(Base):
    __tablename__ = 'Payment'

    Id = Column(Integer, primary_key=True)  #, autoincrement=True)
    Amount = Column(DECIMAL(10, 2))
    AmountUnAllocated = Column(DECIMAL(10, 2), default=0)
    CustomerId = Column(ForeignKey('Customer.Id'))
    CreatedOn = Column(String(80))

    # parent relationships (access parent)
    Customer : Mapped["Customer"] = relationship("Customer", back_populates="PaymentList")

    # child relationships (access children)
    AllocationList : Mapped[List["PaymentAllocation"]] = relationship("PaymentAllocation",
                                   back_populates="Payment",
                                   cascade="all, delete",
                                   passive_deletes=True)  # means database RI will do the deleting


class PaymentAllocation(Base):
    __tablename__ = 'PaymentAllocation'

    Id = Column(Integer, primary_key=True)  #, autoincrement=True)
    AmountAllocated = Column(DECIMAL(10, 2))
    OrderId = Column(ForeignKey('Order.Id'))
    PaymentId = Column(ForeignKey('Payment.Id'))

    # parent relationships (access parent)
    Payment : Mapped["Payment"] = relationship("Payment", back_populates="AllocationList")
    Order : Mapped["Order"] = relationship("Order", back_populates="AllocationList")


class Order(Base):
    __tablename__ = 'Order'

    Id = Column(Integer, primary_key=True)  #, autoincrement=True)
    CustomerId = Column(ForeignKey('Customer.Id'))
    OrderDate = Column(String(8000))
    AmountTotal = Column(DECIMAL(10, 2))

    # parent relationships (access parent)
    Customer : Mapped["Customer"] = relationship("Customer", back_populates="OrderList")

    # child relationships (access children)
    AllocationList : Mapped[List["PaymentAllocation"]] = relationship("PaymentAllocation",
                                   back_populates="Order",
                                   cascade="all, delete",
                                   passive_deletes=True)  # means database RI will do the deleting


class AbPermission(Base):
    __tablename__ = 'ab_permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)


class AbRegisterUser(Base):
    __tablename__ = 'ab_register_user'

    id = Column(Integer, primary_key=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(256))
    email = Column(String(64), nullable=False)
    registration_date = Column(DateTime)
    registration_hash = Column(String(256))


class AbRole(Base):
    __tablename__ = 'ab_role'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)


class AbUser(Base):
    __tablename__ = 'ab_user'

    id = Column(Integer, primary_key=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(256))
    active = Column(Boolean)
    email = Column(String(64), nullable=False, unique=True)
    last_login = Column(DateTime)
    login_count = Column(Integer)
    fail_login_count = Column(Integer)
    created_on = Column(DateTime)
    changed_on = Column(DateTime)
    created_by_fk = Column(ForeignKey('ab_user.id'))
    changed_by_fk = Column(ForeignKey('ab_user.id'))

    parent = relationship('AbUser', remote_side=[id], primaryjoin='AbUser.changed_by_fk == AbUser.id')
    parent1 = relationship('AbUser', remote_side=[id], primaryjoin='AbUser.created_by_fk == AbUser.id')


class AbViewMenu(Base):
    __tablename__ = 'ab_view_menu'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False, unique=True)

class AbPermissionView(Base):
    __tablename__ = 'ab_permission_view'
    __table_args__ = (
        UniqueConstraint('permission_id', 'view_menu_id'),
    )

    id = Column(Integer, primary_key=True)
    permission_id = Column(ForeignKey('ab_permission.id'))
    view_menu_id = Column(ForeignKey('ab_view_menu.id'))

    permission = relationship('AbPermission')
    view_menu = relationship('AbViewMenu')


class AbUserRole(Base):
    __tablename__ = 'ab_user_role'
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('ab_user.id'))
    role_id = Column(ForeignKey('ab_role.id'))

    role = relationship('AbRole')
    user = relationship('AbUser')


class AbPermissionViewRole(Base):
    __tablename__ = 'ab_permission_view_role'
    __table_args__ = (
        UniqueConstraint('permission_view_id', 'role_id'),
    )

    id = Column(Integer, primary_key=True)
    permission_view_id = Column(ForeignKey('ab_permission_view.id'))
    role_id = Column(ForeignKey('ab_role.id'))

    permission_view = relationship('AbPermissionView')
    role = relationship('AbRole')

