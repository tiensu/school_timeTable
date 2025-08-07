from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from .model import Base

class ClassSubject(Base):
    __tablename__ = "class_subjects"
    id = Column(Integer, primary_key=True)
    class_name = Column(String, ForeignKey("classes.name"))
    subject_code = Column(String, ForeignKey("subjects.code"))
    lessons_per_week = Column(Integer)  # Số tiết môn này cho lớp này mỗi tuần
