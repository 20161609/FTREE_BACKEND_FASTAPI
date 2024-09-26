from sqlalchemy import Column, String, Integer, Date, String, Text, LargeBinary, ForeignKey, TIMESTAMP, Boolean
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.db.init import Base
from datetime import datetime

# Transaction model
class Transaction(Base):
    __tablename__ = 'transaction'
    
    tid = Column(Integer, primary_key=True, autoincrement=True)
    t_date = Column(Date, nullable=False)
    branch = Column(String(255), nullable=False)
    cashflow = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    receipt = Column(String(255), nullable=True)
    c_date = Column(TIMESTAMP, default=datetime.utcnow)
    uid = Column(String(255), ForeignKey('authentification.uid'), nullable=False)

# Authentification model
class Authentification(Base):
    __tablename__ = 'authentification'
    uid = Column(String(255), primary_key=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    useai = Column(Boolean, default=True)

# Branch model
class Branch(Base):
    __tablename__ = 'branch'
    bid = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)