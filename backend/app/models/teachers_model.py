from sqlalchemy import Column, Integer, String, Boolean, ARRAY
from sqlalchemy.orm import relationship
from .model import Base
from .teacher_subject_model import teacher_subject_association

# ====== Models ======

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True)  # Mã giáo viên duy nhất
    name = Column(String)
    subjects = relationship("Subject", secondary=teacher_subject_association, back_populates="teachers")
    status = Column(String, default="active")  # active, retired, inactive
     # ➕ Ràng buộc thời gian & số tiết dạy
    max_weekly_lessons = Column(Integer, default=18)       # Số tiết tối đa/tuần
    available_morning = Column(Boolean, default=True)      # Có thể dạy buổi sáng
    available_afternoon = Column(Boolean, default=True)    # Có thể dạy buổi chiều
    unavailable_days = Column(ARRAY(String), default=[])  # ['Monday', 'Thursday']

