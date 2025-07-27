from sqlalchemy import Column, Integer, String, Boolean, ARRAY
from .model import Base

# ====== Models ======

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    code = Column(String)
    required = Column(String)
    num_periods_per_week = Column(Integer, nullable=True)
    subject_group = Column(String, nullable=True)  # Nhóm môn học
    exam_required = Column(Boolean, default=False)  # Có cần thi cuối kỳ không
    description = Column(String, nullable=True)
    status = Column(String, default="active")  # active, retired, inactive

