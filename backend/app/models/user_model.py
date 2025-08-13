# app/models/users_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from app.models.model import Base  # điều chỉnh nếu Base ở module khác

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="user")  # "admin" | "user"
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
