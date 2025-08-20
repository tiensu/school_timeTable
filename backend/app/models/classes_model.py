# app/models/class_model.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .class_subject_model import class_subject_association
from .model import Base

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    specialized_class = Column(String) # Lớp chuyên, ví dụ: "Toán", "Lý", "Hóa"
    # Danh sách các môn học trong lớp
    subjects = relationship(
        "Subject",
        secondary=class_subject_association,
        back_populates="classes",
        lazy="selectin",
    )
