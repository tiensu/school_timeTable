import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.timetable_slot_model import TimetableSlot

# Kết nối DB
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Đọc Excel file
df = pd.read_excel("sample_data/timetable_slots_template.xlsx")  # Đảm bảo file cùng thư mục hoặc nhập path đầy đủ

# Lặp và ghi vào DB
for _, row in df.iterrows():
    slot = TimetableSlot(
        day_of_week=row["day_of_week"],
        session=row["session"],
        period=int(row["period"])
    )
    db.add(slot)

db.commit()
db.close()

print("✅ Import timetable slots từ file Excel thành công.")
