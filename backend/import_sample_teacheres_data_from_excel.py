import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.timetable_slot_model import TimetableSlot
from app.models.model import SessionLocal
from loguru import logger

# Kết nối DB
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Đọc file Excel
df = pd.read_excel("sample_data/teachers_template.xlsx")

# Tạo mapping để tra nhanh
# subject_map = {s.code: s for s in db.query(Subject).all()}
def get_slot_by_label(label: str):
    try:
        d, sess, per = label.split("-")
        return db.query(TimetableSlot).filter_by(
            day_of_week=d, session=sess, period=int(per)
        ).first()
    except:
        return None

# Lặp từng dòng để tạo Teacher
for _, row in df.iterrows():
    if db.query(Teacher).filter_by(code=row["code"]).first():
        continue  # bỏ qua nếu đã tồn tại

    # Gán môn học
    subject_codes = str(row["subject_codes"]).split(",")
    subjects = db.query(Subject).filter(Subject.code.in_(subject_codes)).all()

    # Gán slot bận
    unavailable_slots = []
    slot_labels = str(row["unavailable_slots"]).split(",") if pd.notna(row["unavailable_slots"]) else []
    for label in slot_labels:
        slot = get_slot_by_label(label.strip())
        if slot:
            unavailable_slots.append(slot)
            # logger.debug(f'Added unavailable slot: {slot}')

    t = Teacher(
        code=row["code"],
        name=row["name"],
        max_weekly_lessons=int(row["max_weekly_lessons"]),
        available_morning=bool(row["available_morning"]),
        available_afternoon=bool(row["available_afternoon"]),
        status="active",
        subjects=subjects,
        unavailable_slots=unavailable_slots
    )
    db.add(t)

# Commit
db.commit()
db.close()

print("✅ Import thành công giáo viên từ file Excel.")