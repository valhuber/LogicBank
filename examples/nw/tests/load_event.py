from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, event, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, scoped_session, sessionmaker, relationship, joinedload

# adapted from https://github.com/sqlalchemy/sqlalchemy/issues/5008

engine = create_engine('sqlite:///load_event.db')
engine.connect()

Base = declarative_base()
metadata = Base.metadata


class UserType(Base):
    __tablename__ = 'UserType'

    UserTypeId = Column(String(16), primary_key=True)

    UserList = relationship("User", cascade_backrefs=True, backref="UserType")


class User(Base):
    __tablename__ = 'User'

    UserId = Column(String(16), primary_key=True)
    UserName = Column(String(32))
    Salary = Column(Integer)
    UserTypeId = Column(String(16), ForeignKey('UserType.UserTypeId'))


def receive_load(target, context, only_load_props=None):
    print("  got load event for: " + str(target))
    if isinstance(target, User):
        if target.UserId == "U1":
            target.Salary = None


event.listen(Base, 'load', receive_load, propagate=True)

session_factory = scoped_session(sessionmaker(engine),)

session = session_factory()

print("\nGot session, do query (row events fire here):\n")
users = session.query(User). \
    join(UserType).options(joinedload(User.UserType)). \
    all()
print("\n\nRow events fired, results:\n")
for each_user in users:
    print(f'  got User[{each_user.UserId}] with salary: {each_user.Salary}')
