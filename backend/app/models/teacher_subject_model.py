# Một giáo viên có thể dạy nhiều môn
# Một môn có thể do nhiều giáo viên đảm nhiệm

# app/models/teacher_subject_model.py
from sqlalchemy import Column, Table, String, ForeignKey, UniqueConstraint
from .model import Base

teacher_subject_association = Table(
    "teacher_subject",
    Base.metadata,
    Column("teacher_code", String, ForeignKey("teachers.code")),
    Column("subject_name", String, ForeignKey("subjects.name")),
)

