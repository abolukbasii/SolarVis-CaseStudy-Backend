
from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey


class Users(Base):
    __tablename__ = 'users'

    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String)
    suspended = Column(Boolean)
    suspended_by = Column(Integer, ForeignKey('users.id'))
    last_edited_by = Column(Integer, ForeignKey('users.id'))


class Tasks(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    asigned_to = Column(Integer, ForeignKey('users.id'))
    asigned_by = Column(Integer, ForeignKey('users.id'))
    detail = Column(String)
    due_date = Column(DateTime)
    status = Column(String)


class Organization(Base):
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True, index=True)
    suspended = Column(Boolean)


class DeletedUsers(Base):
    __tablename__ = 'deleted_users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
