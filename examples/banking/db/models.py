# coding: utf-8
from sqlalchemy import Column, DECIMAL, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, text
from sqlalchemy.dialects.mysql import INTEGER, MEDIUMINT, SMALLINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from sqlalchemy.orm import Mapped

from logic_bank import logic_bank  # import this first - import ordering


Base = declarative_base()
metadata = Base.metadata


class ValidAcctType(Base):
    __tablename__ = 'ValidAcctType'

    AcctType = Column(String(2), primary_key=True)
    AcctDescription = Column(String(45))


class ValidCredit(Base):
    __tablename__ = 'ValidCredit'

    creditCode = Column(SMALLINT(6), primary_key=True)
    displayValue = Column(String(50))
    MaxCreditLimit = Column(DECIMAL(10, 2), server_default=text("'0.00'"))


class ValidState(Base):
    __tablename__ = 'ValidState'

    stateCode = Column(String(2), primary_key=True)
    stateName = Column(String(255), nullable=False)


class TRANSFERFUND(Base):
    __tablename__ = 'TRANSFERFUND'

    TransId = Column(INTEGER(9), primary_key=True)
    FromAcct = Column(INTEGER(9), nullable=False)
    FromCustNum = Column(ForeignKey('CUSTOMER.CustNum'), nullable=False, index=True)
    ToAcct = Column(INTEGER(9), nullable=False)
    ToCustNum = Column(ForeignKey('CUSTOMER.CustNum'), nullable=False, index=True)
    TransferAmt = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    TransDate = Column(DateTime)

    # parent relationships (access parent)
    FROMCUSTOMER : Mapped["CUSTOMER"] = relationship('CUSTOMER', foreign_keys=[FromCustNum], back_populates="TRANSFERFUNDFROMLIST")
    TOCUSTOMER : Mapped["CUSTOMER"] = relationship('CUSTOMER', foreign_keys=[ToCustNum], back_populates="TRANSFERFUNDTOLIST")


class CUSTOMER(Base):
    __tablename__ = 'CUSTOMER'

    CustNum = Column(INTEGER(9), primary_key=True)
    Name = Column(String(50), nullable=False, unique=True)
    CheckingAcctBal = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    SavingsAcctBal = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    TotalBalance = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    Street = Column(String(32))
    City = Column(String(24), server_default=text("'ORLANDO'"))
    State = Column(String(2), server_default=text("'FL'"))
    ZIP = Column(INTEGER(11), server_default=text("'32751'"))
    Phone = Column(String(45))
    emailAddress = Column(String(45))

    CHECKINGLIST : Mapped[List["CHECKING"]] = relationship("CHECKING", back_populates="CUSTOMER")
    ALERTLIST : Mapped[List["ALERT"]] = relationship("ALERT", back_populates="CUSTOMER")
    LINEOFCREDITLIST : Mapped[List["LINEOFCREDIT"]] = relationship("LINEOFCREDIT", back_populates="CUSTOMER")
    SAVINGLIST : Mapped[List["SAVING"]] = relationship("SAVING", back_populates="CUSTOMER")

    # https://docs.sqlalchemy.org/en/13/orm/join_conditions.html
    TRANSFERFUNDFROMLIST : Mapped[List["TRANSFERFUND"]] = relationship('TRANSFERFUND', back_populates="FROMCUSTOMER", foreign_keys="TRANSFERFUND.FromCustNum")
    TRANSFERFUNDTOLIST : Mapped[List["TRANSFERFUND"]] = relationship('TRANSFERFUND', back_populates="TOCUSTOMER", foreign_keys="TRANSFERFUND.ToCustNum")


class ALERT(Base):
    __tablename__ = 'ALERT'
    __table_args__ = (
        Index('idx_alter_custAcct', 'CustNum', 'AcctNum'),
    )

    AlertID = Column(INTEGER(9), primary_key=True)
    CustNum = Column(ForeignKey('CUSTOMER.CustNum', ondelete='CASCADE'), nullable=False, index=True)
    AcctNum = Column(INTEGER(9), nullable=False)
    WhenBalance = Column(DECIMAL(10, 2), nullable=False)
    AccountBalance = Column(DECIMAL(10, 2))
    EmailAddress = Column(String(45))

    # parent relationships (access parent)
    CUSTOMER : Mapped["CUSTOMER"] = relationship("CUSTOMER", back_populates="ALERTLIST")


class CHECKING(Base):
    __tablename__ = 'CHECKING'

    AcctNum = Column(INTEGER(9), primary_key=True, nullable=False)
    CustNum = Column(ForeignKey('CUSTOMER.CustNum', ondelete='CASCADE'), primary_key=True, nullable=False, index=True)
    Deposits = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    Withdrawls = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    CurrentBalance = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    AvailableBalance = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    ItemCount = Column(INTEGER(9), server_default=text("'0'"))
    CreditCode = Column(SMALLINT, server_default=text("'1'"))
    CreditLimit = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    AcctType = Column(String(2), nullable=False, index=True)

    # parent relationships (access parent)
    CUSTOMER : Mapped["CUSTOMER"] = relationship("CUSTOMER", back_populates="CHECKINGLIST")

    # child relationships (access children)
    CHECKINGTRANSLIST : Mapped[List["CHECKINGTRANS"]] = relationship('CHECKINGTRANS', back_populates="CHECKING")


class LINEOFCREDIT(Base):
    __tablename__ = 'LINEOFCREDIT'
    __table_args__ = (
        Index('idx_loc_custAcct', 'CustNum', 'AcctNum'),
    )

    CustNum = Column(ForeignKey('CUSTOMER.CustNum', ondelete='CASCADE'), nullable=False, index=True)
    AcctNum = Column(INTEGER(9))
    OverdaftFeeAmt = Column(DECIMAL(10, 2))
    LineOfCreditAmt = Column(DECIMAL(10, 2))
    TotalCharges = Column(DECIMAL(10, 2))
    TotalPayments = Column(DECIMAL(10, 2))
    AvailableBalance = Column(DECIMAL(10, 2))
    Id = Column(INTEGER(9), primary_key=True)

    # parent relationships (access parent)
    CUSTOMER : Mapped["CUSTOMER"] = relationship("CUSTOMER", back_populates="LINEOFCREDITLIST")

    # child relationships (access children)
    LOCTRANSACTIONLIST : Mapped[List["LOCTRANSACTION"]] = relationship("LOCTRANSACTION", back_populates="LINEOFCREDIT")


class SAVING(Base):
    __tablename__ = 'SAVING'

    AcctNum = Column(INTEGER(9), primary_key=True, nullable=False)
    CustNum = Column(ForeignKey('CUSTOMER.CustNum', ondelete='CASCADE'), primary_key=True, nullable=False, index=True)
    Deposits = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    Withdrawls = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    CurrentBalance = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    AvailableBalance = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    ItemCount = Column(INTEGER(9), nullable=False, server_default=text("'0'"))
    AcctType = Column(String(2), index=True)

    # parent relationships (access parent)
    CUSTOMER : Mapped["CUSTOMER"] = relationship("CUSTOMER", back_populates="SAVINGLIST")

    # child relationships (access children)
    SAVINGSTRANSLIST : Mapped[List["SAVINGSTRANS"]] = relationship("SAVINGSTRANS", back_populates="SAVING")

class CHECKINGTRANS(Base):
    __tablename__ = 'CHECKINGTRANS'
    __table_args__ = (
        ForeignKeyConstraint(['AcctNum', 'CustNum'], ['CHECKING.AcctNum', 'CHECKING.CustNum'], ondelete='CASCADE'),
        Index('U_Name_CHKG_CUST', 'AcctNum', 'CustNum')
    )

    TransId = Column(INTEGER(9), primary_key=True)
    AcctNum = Column(INTEGER(9), nullable=False)
    CustNum = Column(INTEGER(9), nullable=False)
    TransDate = Column(DateTime)
    DepositAmt = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    WithdrawlAmt = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    Total = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    ChkNo = Column(String(9))
    ImageURL = Column(String(45))

    # parent relationships (access parent)
    CHECKING : Mapped["CHECKING"] = relationship('CHECKING', back_populates="CHECKINGTRANSLIST")


class LOCTRANSACTION(Base):
    __tablename__ = 'LOCTRANSACTION'
    __table_args__ = (
        ForeignKeyConstraint(['CustNum', 'AcctNum'], ['LINEOFCREDIT.CustNum', 'LINEOFCREDIT.AcctNum'], ondelete='CASCADE'),
        Index('fk_LOC_TRANSACTIONS_LINE_OF_CREDIT1_idx', 'CustNum', 'AcctNum')
    )

    TransId = Column(INTEGER(9), primary_key=True)
    TransDate = Column(DateTime)
    PaymentAmt = Column(DECIMAL(10, 2))
    ChargeAmt = Column(DECIMAL(10, 2))
    ChargeType = Column(String(45), comment='fee, OD, Payment')
    CustNum = Column(INTEGER(9), nullable=False)
    AcctNum = Column(INTEGER(9), nullable=False)

    # parent relationships (access parent)
    LINEOFCREDIT : Mapped["LINEOFCREDIT"] = relationship("LINEOFCREDIT", back_populates="LOCTRANSACTIONLIST")

class SAVINGSTRANS(Base):
    __tablename__ = 'SAVINGSTRANS'
    __table_args__ = (
        ForeignKeyConstraint(['AcctNum', 'CustNum'], ['SAVING.AcctNum', 'SAVING.CustNum'], ondelete='CASCADE'),
        Index('U_Name_SAVINGS_CUST', 'AcctNum', 'CustNum')
    )

    TransId = Column(INTEGER(9), primary_key=True)
    AcctNum = Column(INTEGER(9), nullable=False)
    CustNum = Column(INTEGER(9), nullable=False)
    TransDate = Column(DateTime)
    DepositAmt = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    WithdrawlAmt = Column(DECIMAL(10, 2), server_default=text("'0.00'"))
    Total = Column(DECIMAL(10, 2), server_default=text("'0.00'"))

    # parent relationships (access parent)
    SAVING : Mapped["SAVING"] = relationship("SAVING", back_populates="SAVINGSTRANSLIST")
