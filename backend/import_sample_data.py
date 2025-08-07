from sqlalchemy import create_engine, Column, Integer, String, Boolean, Table, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.class_subject_model import ClassSubject
from app.models.timetable_model import Timetable
from app.models.timetable_slot_model import TimetableSlot

from app.models.model import SessionLocal
# === Kết nối DB ===
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Môn học
subjects = [
    Subject(code="MATH10", name="Toán 10", required="Có", num_periods_per_week=4, subject_group="KHTN", exam_required=True),
    Subject(code="PHYS10", name="Lý 10", required="Có", num_periods_per_week=3, subject_group="KHTN", exam_required=True),
    Subject(code="CHEM10", name="Hóa 10", required="Có", num_periods_per_week=3, subject_group="KHTN", exam_required=True),
]
for s in subjects:
    if not db.query(Subject).filter_by(code=s.code).first():
        db.add(s)

# Giáo viên
teachers = [
    Teacher(code="gv001", name="Nguyễn Văn A", max_weekly_lessons=16, unavailable_days="Thứ 2"),
    Teacher(code="gv002", name="Trần Thị B", max_weekly_lessons=18, available_afternoon=False, unavailable_days="Thứ 4"),
]
for t in teachers:
    if not db.query(Teacher).filter_by(code=t.code).first():
        db.add(t)

# Lớp học
classes = [
    Class(name="10A1", grade=10, student_count=45),
    Class(name="10A2", grade=10, student_count=42),
]
for c in classes:
    if not db.query(Class).filter_by(name=c.name).first():
        db.add(c)

db.commit()

# Gán môn dạy cho giáo viên
gv001 = db.query(Teacher).filter_by(code="gv001").first()
gv002 = db.query(Teacher).filter_by(code="gv002").first()
toan = db.query(Subject).filter_by(code="MATH10").first()
ly = db.query(Subject).filter_by(code="PHYS10").first()
hoa = db.query(Subject).filter_by(code="CHEM10").first()

gv001.subjects = [toan, ly]
gv002.subjects = [hoa]
db.commit()

# Lớp học cần học môn nào, bao nhiêu tiết/tuần
class_10a1 = db.query(Class).filter_by(name="10A1").first()
class_10a2 = db.query(Class).filter_by(name="10A2").first()

class_subjects = [
    ClassSubject(class_name=class_10a1.name, subject_code="MATH10", lessons_per_week=4),
    ClassSubject(class_name=class_10a1.name, subject_code="PHYS10", lessons_per_week=3),
    ClassSubject(class_name=class_10a2.name, subject_code="CHEM10", lessons_per_week=3),
]
db.add_all(class_subjects)

# Slot học: Monday–Friday, mỗi buổi 5 tiết → 5 ngày * 2 buổi * 5 tiết = 50 slots
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
for day in days:
    for session in ["morning", "afternoon"]:
        for period in range(1, 6):  # 1 đến 5
            db.add(TimetableSlot(day_of_week=day, session=session, period=period))
db.commit()

# Thời khóa biểu mẫu (gán lớp, môn, giáo viên, slot)
slots = db.query(TimetableSlot).all()
db.add_all([
    Timetable(class_name=class_10a1.name, subject_code="MATH10", teacher_code="gv001", slot_id=slots[0].id),
    Timetable(class_name=class_10a1.name, subject_code="PHYS10", teacher_code="gv001", slot_id=slots[1].id),
    Timetable(class_name=class_10a2.name, subject_code="CHEM10", teacher_code="gv002", slot_id=slots[2].id),
])
db.commit()
db.close()

print("✅ Dữ liệu mẫu đã được import thành công.")
