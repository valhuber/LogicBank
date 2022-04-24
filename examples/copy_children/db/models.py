# coding: utf-8
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.ext.declarative import declarative_base


########################################################################################################################
# Classes describing database for SqlAlchemy ORM, initially created by schema introspection.
#
from safrs import SAFRSBase

import safrs

Base = declarative_base()
metadata = Base.metadata

#NullType = db.String  # datatype fixup
#TIMESTAMP= db.TIMESTAMP

from sqlalchemy.dialects.mysql import *
########################################################################################################################



class Project(SAFRSBase, Base):
    __tablename__ = 'Project'

    name = Column(String(16))
    notes = Column(String(512))
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('Project.id'))

    # see backref on parent: project_ = relationship('Project', remote_side=[id], cascade_backrefs=True, backref='ProjectList')

    project_ = relationship('Project', remote_side=[id], cascade_backrefs=True, backref='ProjectList')  # special handling for self-relationships
    MileStoneList = relationship('MileStone', cascade_backrefs=True, backref='project')
    StaffList = relationship('Staff', cascade_backrefs=True, backref='project')


t_sqlite_sequence = Table(
    'sqlite_sequence', metadata,
    Column('name', NullType),
    Column('seq', NullType)
)


class MileStone(SAFRSBase, Base):
    __tablename__ = 'MileStone'

    milestone_name = Column(String(16))
    notes = Column(String(256))
    id = Column(Integer, primary_key=True)
    project_id = Column(ForeignKey('Project.id'))

    # see backref on parent: project = relationship('Project', cascade_backrefs=True, backref='MileStoneList')

    DeliverableList = relationship('Deliverable', cascade_backrefs=True, backref='milestone')


class Staff(SAFRSBase, Base):
    __tablename__ = 'Staff'

    id = Column(Integer, primary_key=True)
    Description = Column(String(16))
    project_id = Column(ForeignKey('Project.id'))

    # see backref on parent: project = relationship('Project', cascade_backrefs=True, backref='StaffList')


class Deliverable(SAFRSBase, Base):
    __tablename__ = 'Deliverable'

    id = Column(Integer, primary_key=True)
    milestone_id = Column(ForeignKey('MileStone.id'))
    Name = Column(String(16))

    # see backref on parent: milestone = relationship('MileStone', cascade_backrefs=True, backref='DeliverableList')


from database import customize_models
