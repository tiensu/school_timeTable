from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/timetable")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ====== Models ======
class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    grade = Column(Integer)
    student_count = Column(Integer)

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    subject = Column(String)
    phone = Column(String)
    email = Column(String, nullable=True)
    dob = Column(String, nullable=True)
    address = Column(String, nullable=True)

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    grade = Column(Integer)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    room_type = Column(String)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))

# ====== Tạo bảng sau khi model đã được định nghĩa ======
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
