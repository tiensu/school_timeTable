# app/models/class_model.py

from sqlalchemy import Column, Integer, String
from .model import Base

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    grade = Column(Integer)
    student_count = Column(Integer)
