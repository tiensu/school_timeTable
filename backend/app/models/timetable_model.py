from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from .model import Base

class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(Integer, primary_key=True)
    class_name = Column(String, ForeignKey("classes.name"))
    subject_code = Column(String, ForeignKey("subjects.code"))
    teacher_code = Column(String, ForeignKey("teachers.code"))
    slot_id = Column(Integer, ForeignKey("timetable_slots.id"))
