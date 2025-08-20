import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.teachers_model import Teacher
from app.models.timetable_slot_model import TimetableSlot

# === Kết nối DB ===
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# === Đọc Excel ===
df = pd.read_excel("sample_data/timetable_slots_information.xlsx")

# === Import từng lớp ===
created = 0
skipped = 0
for _, row in df.iterrows():
    name = str(row["name"]).strip()

    # Bỏ qua nếu đã tồn tại
    if db.query(Class).filter_by(name=name).first():
        skipped += 1
        continue

    grade = int(row["grade"])
    student_count = int(row["student_count"])
    subject_codes = str(row["subject_codes"]).split(",") if pd.notna(row["subject_codes"]) else []
    subjects = db.query(Subject).filter(Subject.code.in_(subject_codes)).all()

    clazz = Class(
        name=name,
        grade=grade,
        student_count=student_count,
        subjects=subjects
    )

    db.add(clazz)
    created += 1

db.commit()
db.close()

print(f"✅ Import lớp học xong. Tạo mới: {created}, bỏ qua (đã tồn tại): {skipped}.")
