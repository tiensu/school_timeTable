# app/models/model.py

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/timetable")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ====== Tạo bảng sau khi model đã được định nghĩa ======
# Base.metadata.drop_all(bind=engine)
# Base.metadata.create_all(bind=engine)