# app/models/class_subject_link.py
from sqlalchemy import Column, Table, String, ForeignKey, UniqueConstraint, Index
from .model import Base

class_subject_association = Table(
    "class_subject",
    Base.metadata,
    Column("class_name", String,
           ForeignKey("classes.name", ondelete="CASCADE", onupdate="CASCADE"),
           nullable=False),
    Column("subject_name", String,
           ForeignKey("subjects.name", ondelete="CASCADE", onupdate="CASCADE"),
           nullable=False),
    # UniqueConstraint("class_name", "subject_code", name="uq_class_subject"),
    # Index("ix_cs_class", "class_name"),
    # Index("ix_cs_subject", "subject_code"),
)