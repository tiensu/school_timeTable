from sqlalchemy import create_engine, Column, Integer, String, Boolean, Table, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from fastapi import APIRouter, Depends
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.class_subject_model import ClassSubject
from app.models.timetable_model import Timetable
from app.models.timetable_slot_model import TimetableSlot

import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.models.model import SessionLocal
# === Kết nối DB ===
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"


# Retry kết nối nếu DB chưa sẵn sàng
for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db: Session = SessionLocal()
        print("✅ PostgreSQL đã sẵn sàng.")
        break
    except OperationalError as e:
        print(f"⏳ Chờ PostgreSQL... ({i+1}/10)")
        time.sleep(3)
else:
    raise RuntimeError("❌ Không thể kết nối đến PostgreSQL sau 10 lần thử.")

# Môn học
subjects = [
    Subject(code="MATH10", name="Toán 10", required="Có", num_periods_per_week=4, subject_group="KHTN", exam_required=True),
    Subject(code="PHYS10", name="Lý 10", required="Có", num_periods_per_week=3, subject_group="KHTN", exam_required=True),
    Subject(code="CHEM10", name="Hóa 10", required="Có", num_periods_per_week=3, subject_group="KHTN", exam_required=True),
]
for s in subjects:
    if not db.query(Subject).filter_by(code=s.code).first():
        db.add(s)
db.commit()

# -------------------------
# Slot học: Monday–Friday, mỗi buổi 5 tiết → 5 ngày * 2 buổi * 5 tiết = 50 slots
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
for day in days:
    for session in ["morning", "afternoon"]:
        for period in range(1, 6):  # 1 đến 5
            db.add(TimetableSlot(day_of_week=day, session=session, period=period))
db.commit()

# -------------------
# Lấy subject và slot từ DB
def get_subject_by_code(db, code: str):
    return db.query(Subject).filter_by(code=code).first()

def get_slot_by_label(db, label: str):
    """Ví dụ label = 'Monday-morning-1' → lấy slot tương ứng"""
    parts = label.split("-")
    return db.query(TimetableSlot).filter_by(
        day_of_week=parts[0],
        session=parts[1],
        period=int(parts[2])
    ).first()


# Khởi tạo giáo viên
teacher_data = [
    {
        "code": "gv001",
        "name": "Nguyễn Văn A",
        "max_weekly_lessons": 16,
        "subjects": ["MATH10", "PHYS10"],  # 🧠 dạy Toán, Lý
        "available_morning": True,
        "available_afternoon": True,
        "unavailable_slots": [
            "Monday-morning-1", "Wednesday-afternoon-2"
        ]
    },
    {
        "code": "gv002",
        "name": "Trần Thị B",
        "max_weekly_lessons": 18,
        "subjects": ["CHEM10"],  # 🧠 dạy Hóa
        "available_morning": True,
        "available_afternoon": False,
        "unavailable_slots": [
            "Thursday-morning-1"
        ]
    }
]
# Thêm vào DB
for t in teacher_data:
    if db.query(Teacher).filter_by(code=t["code"]).first():
        continue

    teacher = Teacher(
        code=t["code"],
        name=t["name"],
        max_weekly_lessons=t["max_weekly_lessons"],
        available_morning=t["available_morning"],
        available_afternoon=t["available_afternoon"],
    )

    # Gán môn học có thể dạy
    for subj_code in t["subjects"]:
        subj = get_subject_by_code(db, subj_code)
        if subj:
            teacher.subjects.append(subj)

    # Gán unavailable_slots
    for label in t["unavailable_slots"]:
        slot = get_slot_by_label(db, label)
        if slot:
            teacher.unavailable_slots.append(slot)

    db.add(teacher)
db.commit()

# Lớp học
classes = [
    Class(name="10A1", grade=10, student_count=45),
    Class(name="10A2", grade=10, student_count=42),
    Class(name="10A3", grade=10, student_count=42),
]
for c in classes:
    if not db.query(Class).filter_by(name=c.name).first():
        db.add(c)

db.commit()

# Lớp học cần học môn nào, bao nhiêu tiết/tuần
class_10a1 = db.query(Class).filter_by(name="10A1").first()
class_10a2 = db.query(Class).filter_by(name="10A2").first()
class_10a3 = db.query(Class).filter_by(name="10A3").first()

class_subjects = [
    ClassSubject(class_name=class_10a1.name, subject_code="MATH10", lessons_per_week=4),
    ClassSubject(class_name=class_10a1.name, subject_code="PHYS10", lessons_per_week=3),
    ClassSubject(class_name=class_10a2.name, subject_code="CHEM10", lessons_per_week=3),
    ClassSubject(class_name=class_10a2.name, subject_code="PHYS10", lessons_per_week=3),
    ClassSubject(class_name=class_10a2.name, subject_code="MATH10", lessons_per_week=4),
    ClassSubject(class_name=class_10a2.name, subject_code="CHEM10", lessons_per_week=3),
]
db.add_all(class_subjects)
db.commit()

# # Thời khóa biểu mẫu (gán lớp, môn, giáo viên, slot)
# slots = db.query(TimetableSlot).all()
# db.add_all([
#     Timetable(class_name=class_10a1.name, subject_code="MATH10", teacher_code="gv001", slot_id=slots[0].id),
#     Timetable(class_name=class_10a1.name, subject_code="PHYS10", teacher_code="gv001", slot_id=slots[1].id),
#     Timetable(class_name=class_10a2.name, subject_code="CHEM10", teacher_code="gv002", slot_id=slots[2].id),
# ])
# db.commit()

db.close()

print("✅ Dữ liệu mẫu đã được import thành công.")
