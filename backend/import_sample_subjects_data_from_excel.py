import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.model import SessionLocal
from app.models.subjects_model import Subject
from app.models.teachers_model import Teacher
from app.models.classes_model import Class
from app.models.timetable_slot_model import TimetableSlot
from app.schema import subjects_schema
from loguru import logger

# Thiết lập kết nối đến PostgreSQL
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Đọc dữ liệu từ file Excel
df = pd.read_excel("sample_data/subjects_template.xlsx")

# Ghi từng dòng vào DB (nếu chưa tồn tại)
for idx, row in df.iterrows():
    try:
        name = str(row[0]).strip() if pd.notna(row[0]) else None
        code = str(row[1]).strip() if pd.notna(row[1]) else None
        lesson_per_week = int(row[2]) if pd.notna(row[2]) else None
        subject_group = str(row[3]).strip() if pd.notna(row[3]) else None
        required = str(row[4]).strip() == "Có" if pd.notna(
            row[4]) else False
        exam_required = str(row[5]).strip(
        ) == "Có" if pd.notna(row[5]) else False
        description = str(row[6]).strip() if len(
            row) > 6 and pd.notna(row[6]) else None
        status = str(row[7]).strip() if len(
            row) > 7 and pd.notna(row[7]) else "active"

        if not name or not code:
            raise ValueError("Thiếu tên hoặc mã môn học")

        existing = db.query(Subject).filter(Subject.code == code).first()
        if existing:
            duplicated.append(name)
            continue

        subject_obj = Subject(
            name=name,
            code=code,
            required=required,
            lesson_per_week=lesson_per_week,
            subject_group=subject_group,
            exam_required=exam_required,
            description=description,
            status=status
        )
        db.add(subject_obj)

    except Exception as e:
        logger.error(f"Dòng {idx+2} ({row[0]}): {str(e)}")
    
    db.commit()
    db.close()

print("✅ Import thành công dữ liệu môn học từ file Excel.")