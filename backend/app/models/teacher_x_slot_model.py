# app/models/teacher_unavailable_slot_model.py
from sqlalchemy import Column, Table, String, ForeignKey, Integer
from .model import Base

class Teacher_X_Slot(Base):
    __tablename__ = "teacher_x_slots"
    teacher_code = Column(String, ForeignKey("teachers.code"), primary_key=True)
    slot_id = Column(Integer, ForeignKey("timetable_slots.id"), primary_key=True)