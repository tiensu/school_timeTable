from sqlalchemy import Column, Integer, String, Boolean, ARRAY
from .model import Base

# ====== Models ======

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    subject = Column(String)
    phone = Column(String)
    email = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    address = Column(String, nullable=True)
    status = Column(String, default="active")  # active, retired, inactive
     # ➕ Ràng buộc thời gian & số tiết dạy
    max_weekly_lessons = Column(Integer, default=18)       # Số tiết tối đa/tuần
    available_morning = Column(Boolean, default=True)      # Có thể dạy buổi sáng
    available_afternoon = Column(Boolean, default=True)    # Có thể dạy buổi chiều
    unavailable_days = Column(ARRAY(String), default=[])  # ['Monday', 'Thursday']

