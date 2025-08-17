# coding: utf-8
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.ext.declarative import declarative_base
from typing import List
from sqlalchemy.orm import Mapped


########################################################################################################################
# Classes describing database for SqlAlchemy ORM, initially created by schema introspection.
#

Base = declarative_base()
metadata = Base.metadata

#NullType = db.String  # datatype fixup
#TIMESTAMP= db.TIMESTAMP

from sqlalchemy.dialects.mysql import *
########################################################################################################################



class Project(Base):
    __tablename__ = 'Project'

    name = Column(String(16))
    notes = Column(String(512), server_default="not supplied")
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('Project.id'))
    milestone_count = Column(Integer, server_default="0")
    staff_count = Column(Integer)

    # self-referential relationship - parent project
    project_ : Mapped["Project"] = relationship('Project', remote_side=[id], back_populates='ProjectList')
    
    # child relationships
    ProjectList : Mapped[List["Project"]] = relationship('Project', remote_side=[project_id], back_populates='project_')
    MileStoneList : Mapped[List["MileStone"]] = relationship('MileStone', back_populates='project')
    StaffList : Mapped[List["Staff"]] = relationship('Staff', back_populates='project')


t_sqlite_sequence = Table(
    'sqlite_sequence', metadata,
    Column('name', NullType),
    Column('seq', NullType)
)


class MileStone(Base):
    __tablename__ = 'MileStone'

    milestone_name = Column(String(16))
    notes = Column(String(256))
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('Project.id'))

    # parent relationships (access parent)
    project : Mapped["Project"] = relationship('Project', back_populates='MileStoneList')

    # child relationships (access children)
    DeliverableList : Mapped[List["Deliverable"]] = relationship('Deliverable', back_populates='milestone')


class Staff(Base):
    __tablename__ = 'Staff'

    id = Column(Integer, primary_key=True)
    Description = Column(String(16))
    project_id = Column(ForeignKey('Project.id'))

    # parent relationships (access parent)
    project : Mapped["Project"] = relationship('Project', back_populates='StaffList')


class Deliverable(Base):
    __tablename__ = 'Deliverable'

    id = Column(Integer, primary_key=True)
    milestone_id = Column(ForeignKey('MileStone.id'))
    Name = Column(String(16))

    # parent relationships (access parent)
    milestone : Mapped["MileStone"] = relationship('MileStone', back_populates='DeliverableList')


