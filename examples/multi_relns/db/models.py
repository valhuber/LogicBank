# coding: utf-8
"""
Minimal schema for the multi-relationship regression suite (see
system/LogicBank-Internal-Dev/multi-relationship-bug.md in the repo root).

Department <-> Employee, via TWO distinct relationships in each direction:
    Employee.works_for_id -> Department  (role: works_for_dept / EmployeeWorksForList)
    Employee.on_loan_id   -> Department  (role: on_loan_dept   / EmployeeOnLoanList)

Both roles get a Sum and a Count (exercises issue #20 - Rule.sum previously
ignored child_role_name when 2+ relationships target the same parent class).

Employee also carries a copy-vs-live pair sourced from the SAME multi-relationship
parent pair, to exercise the parent->child cascade disambiguation (Rule.formula
live reference) separately from the child->parent aggregate disambiguation
(Rule.sum/Rule.count) - see "A third direction" in multi-relationship-bug.md.
"""

from sqlalchemy import Column, DECIMAL, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List

from logic_bank import logic_bank  # import this first - import ordering

Base = declarative_base()
metadata = Base.metadata


class Department(Base):
    __tablename__ = 'department'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), nullable=False)

    # Sum/Count for the "works_for" role
    works_for_salary_total = Column(DECIMAL(10, 2), server_default="0")
    works_for_count = Column(Integer, server_default="0")

    # Sum/Count for the "on_loan" role
    on_loan_salary_total = Column(DECIMAL(10, 2), server_default="0")
    on_loan_count = Column(Integer, server_default="0")

    # child relationships (access children) - two distinct relationships to Employee
    EmployeeWorksForList: Mapped[List["Employee"]] = relationship(
        "Employee", foreign_keys="[Employee.works_for_id]", back_populates="works_for_dept")
    EmployeeOnLoanList: Mapped[List["Employee"]] = relationship(
        "Employee", foreign_keys="[Employee.on_loan_id]", back_populates="on_loan_dept")


class Employee(Base):
    __tablename__ = 'employee'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), nullable=False)
    salary = Column(DECIMAL(10, 2), nullable=False, server_default="0")

    works_for_id = Column(ForeignKey('department.id'), nullable=False)
    on_loan_id = Column(ForeignKey('department.id'), nullable=True)

    # Rule.copy snapshot - from works_for_dept (frozen at insert/update time)
    works_for_dept_name_copy = Column(String(40))

    # Rule.formula live reference - from on_loan_dept (re-derives if parent changes)
    on_loan_dept_name_live = Column(String(40))

    # parent relationships (access parent) - two distinct relationships to Department
    works_for_dept: Mapped["Department"] = relationship(
        "Department", foreign_keys=[works_for_id], back_populates="EmployeeWorksForList")
    on_loan_dept: Mapped["Department"] = relationship(
        "Department", foreign_keys=[on_loan_id], back_populates="EmployeeOnLoanList")
