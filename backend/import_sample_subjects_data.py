from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.timetable_slot_model import TimetableSlot
from app.models.teachers_model import Teacher
from app.models.classes_model import Class
from app.models.subjects_model import Subject

from sqlalchemy import create_engine

from app.models.model import SessionLocal
# === Kết nối DB ===
DATABASE_URL = "postgresql://postgres:postgres@db:5432/timetable"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db: Session = SessionLocal()

# --- 1) MÔN HỌC ---
# (code, name, group, periods/week, exam_required)
SUBJECT_DEFS = [
    # Khối 10
    ("MATH_10",  "Toán 10",                  "KHTN", 4, True),
    ("PHYS_10",  "Vật Lý 10",                "KHTN", 3, True),
    ("CHEM_10",  "Hóa 10",                   "KHTN", 3, True),
    ("LIT_10",   "Ngữ Văn 10",               "KHXH", 4, True),
    ("HIST_10",  "Lịch Sử 10",               "KHXH", 2, True),
    ("GEO_10",   "Địa Lí 10",                "KHXH", 2, True),
    ("BIO_10",   "Sinh Học 10",              "KHTN", 2, True),
    ("ENG_10",   "Tiếng Anh 10",             "NN",   3, True),
    ("CIV_10",   "Giáo Dục Công Dân 10",     "GD",   2, False),
    ("TECH_10",  "Công Nghệ 10",             "GD",   2, False),
    ("DEF_10",   "Giáo Dục Quốc Phòng 10",   "GD",   2, False),
    ("PE_10",    "Giáo Dục Thể Chất 10",     "GD",   2, False),
    ("IT_10",    "Tin Học 10",               "KHTN", 2, False),
    # Khối 11
    ("MATH_11",  "Toán 11",                  "KHTN", 4, True),
    ("PHYS_11",  "Vật Lý 11",                "KHTN", 3, True),
    ("CHEM_11",  "Hóa 11",                   "KHTN", 3, True),
    ("LIT_11",   "Ngữ Văn 11",               "KHXH", 4, True),
    ("HIST_11",  "Lịch Sử 11",               "KHXH", 2, True),
    ("GEO_11",   "Địa Lí 11",                "KHXH", 2, True),
    ("BIO_11",   "Sinh Học 11",              "KHTN", 2, True),
    ("ENG_11",   "Tiếng Anh 11",             "NN",   3, True),
    ("CIV_11",   "Giáo Dục Công Dân 11",     "GDCD",   2, False),
    ("TECH_11",  "Công Nghệ 11",             "CN",   2, False),
    ("DEF_11",   "Giáo Dục Quốc Phòng 11",   "GDQP",   2, False),
    ("PE_11",    "Giáo Dục Thể Chất 11",     "GDTC",   2, False),
    ("IT_11",    "Tin Học 11",               "KHTN", 2, False),
    ("ELECT", "Môn tự chọn (khối 11)",       "TC", 2, False),
    # Khối 12
    ("MATH_12",  "Toán 12",                  "KHTN", 4, True),
    ("PHYS_12",  "Vật Lý 12",                "KHTN", 3, True),
    ("CHEM_12",  "Hóa 12",                   "KHTN", 3, True),
    ("LIT_12",   "Ngữ Văn 12",               "KHXH", 4, True),
    ("HIST_12",  "Lịch Sử 12",               "KHXH", 2, True),
    ("GEO_12",   "Địa Lí 12",                "KHXH", 2, True),
    ("BIO_12",   "Sinh Học 12",              "KHTN", 2, True),
    ("ENG_12",   "Tiếng Anh 12",             "NN",   3, True),
    ("CIV_12",   "Giáo Dục Công Dân 12",     "GDCD",   2, False),
    ("TECH_12",  "Công Nghệ 12",             "CN",   2, False),
    ("DEF_12",   "Giáo Dục Quốc Phòng 12",   "GDQP",   2, False),
    ("PE_12",    "Giáo Dục Thể Chất 12",     "GDTC",   2, False),
    ("IT_12",    "Tin Học 12",               "KHTN", 2, False),
]
for s in SUBJECT_DEFS:
    if not db.query(Subject).filter_by(code=s[0]).first():
        db.add(Subject(
            code=s[0],
            name=s[1],
            required=True,
            subject_group=s[2],
            lesson_per_week=s[3],
            exam_required=s[4]
        ))
db.commit()
db.close()

print("✅ Dữ liệu mẫu đã được import thành công.")
