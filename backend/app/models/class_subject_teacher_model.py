# quy định môn nào được dạy cho lớp nào bởi giáo viên nào

from sqlalchemy import Column, String, Integer, ForeignKey
from .model import Base

class ClassSubjectTeacher(Base):
    __tablename__ = "class_subject_teacher"
    id = Column(Integer, primary_key=True)
    teacher_code = Column(String, ForeignKey("teachers.code"))
    subject_code = Column(String, ForeignKey("subjects.code"))
    class_name = Column(String, ForeignKey("classes.name"))
