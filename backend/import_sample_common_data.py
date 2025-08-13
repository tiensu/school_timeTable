from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.timetable_slot_model import TimetableSlot

import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.models.model import SessionLocal
# === Kết nối DB ===
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"


# Retry kết nối nếu DB chưa sẵn sàng
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db: Session = SessionLocal()

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

db.close()

print("✅ Import thành công common data.")
