# app/models/teacher_unavailable_slot_model.py
from sqlalchemy import Column, Table, String, ForeignKey, Integer
from .model import Base

teacher_unavailable_slot_association = Table(
    "teacher_unavailable_slots",
    Base.metadata,
    Column("teacher_code", String, ForeignKey("teachers.code")),
    Column("slot_id", Integer, ForeignKey("timetable_slots.id")),
)
