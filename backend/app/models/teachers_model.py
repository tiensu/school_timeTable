from sqlalchemy import Column, Integer, String, Boolean, ARRAY
from sqlalchemy.orm import relationship
from .model import Base
from .teacher_unavailable_slot_model import teacher_unavailable_slot_association

# ====== Models ======

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True)  # Mã giáo viên duy nhất
    name = Column(String)
    class_advisor = Column(String)  # Giáo viên chủ nhiệm
    max_weekly_lessons = Column(Integer, default=17)       # Số tiết tối đa/tuần
    max_weekly_x = Column(Integer, default=0)         # Số tiết tối đa/tuần cho môn X
    unavailable_slots = relationship(
        "TimetableSlot", 
        secondary=teacher_unavailable_slot_association, 
        backref="unavailable_teachers"
    )

