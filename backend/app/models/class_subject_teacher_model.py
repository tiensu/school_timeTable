# quy định môn nào được dạy cho lớp nào bởi giáo viên nào

from sqlalchemy import Column, Integer, ForeignKey
from .model import Base

class ClassSubjectTeacher(Base):
    __tablename__ = "class_subject_teacher"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
