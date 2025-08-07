# mỗi tuần có bao nhiêu tiết? Ví dụ: 5 ngày * 5 tiết/ngày = 25 slots

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from .model import Base

class TimetableSlot(Base):
    __tablename__ = "time_slots"
    id = Column(Integer, primary_key=True)
    day_of_week = Column(String)  # e.g., 'Monday'
    period = Column(Integer)      # e.g., 1, 2, 3, ...
