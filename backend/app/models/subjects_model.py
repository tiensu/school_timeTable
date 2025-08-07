from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .model import Base
from .teacher_subject_model import teacher_subject_association

# ====== Models ======

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True)
    name = Column(String)
    teachers = relationship("Teacher", secondary=teacher_subject_association, back_populates="subjects")
    required = Column(String)
    num_periods_per_week = Column(Integer, nullable=True)
    subject_group = Column(String, nullable=True)  # Nhóm môn học
    exam_required = Column(Boolean, default=False)  # Có cần thi cuối kỳ không
    description = Column(String, nullable=True)
    status = Column(String, default="active")  # active, retired, inactive

