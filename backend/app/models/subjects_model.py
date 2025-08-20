from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .model import Base
from .class_subject_model import class_subject_association

# ====== Models ======

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True)
    name = Column(String, unique=True)
    lesson_per_week = Column(Integer, nullable=True) # Số tiết học mỗi tuần cho lớp không chuyên

    # # Lớp ⇄ Môn học
    classes = relationship(
        "Class",
        secondary=class_subject_association,
        back_populates="subjects",
        lazy="selectin",
    )