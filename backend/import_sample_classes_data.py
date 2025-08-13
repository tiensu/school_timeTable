# import_sample_classes_data.py

from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.timetable_slot_model import TimetableSlot
# from app.models.class_subject_model import class_subject_association

db: Session = SessionLocal()

# --- 2) LỚP HỌC ---
# Khối 10..12, mỗi khối 12 lớp (A1..A12)

SUBJECTS_BY_GRADE = {
    10: ["MATH_10","LIT_10","ENG_10","PHYS_10","CHEM_10","BIO_10","HIST_10","GEO_10","CIV_10","PE_10","IT_10","TECH_10","DEF_10"],
    11: ["MATH_11","LIT_11","ENG_11","PHYS_11","CHEM_11","BIO_11","HIST_11","GEO_11","CIV_11","PE_11","IT_11","TECH_11","DEF_11","ELECT"],
    12: ["MATH_12","LIT_12","ENG_12","PHYS_12","CHEM_12","BIO_12","HIST_12","GEO_12","CIV_12","PE_12","IT_12","TECH_12","DEF_12"],
}

# ===== 2. Hàm thêm lớp và gán môn =====
def add_class_with_subjects(class_name: str, grade: int, student_count: int, subject_code: list[str]):
    # Kiểm tra tồn tại
    existing = db.query(Class).filter_by(name=class_name).first()
    if existing:
        print(f"❌ Lớp {class_name} đã tồn tại, bỏ qua.")
        return
    subjects = db.query(Subject).filter(Subject.code.in_(subject_code)).all()
    clazz = Class(name=class_name, grade=grade, student_count=student_count, subjects=subjects)
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    # print(f"✅ Đã thêm lớp {class_name} với {len(subjects)} môn.")

# ===== 3. Sinh dữ liệu mẫu =====
# Khối 10
for i in range(1, 13):
    add_class_with_subjects(f"10A{i}", 10, 45, SUBJECTS_BY_GRADE[10])

# Khối 11
for i in range(1, 13):
    add_class_with_subjects(f"11A{i}", 11, 43, SUBJECTS_BY_GRADE[11])

# Khối 12
for i in range(1, 13):
    add_class_with_subjects(f"12A{i}", 12, 42, SUBJECTS_BY_GRADE[12])

db.close()

print("✅ Dữ liệu mẫu lớp học đã được import thành công.")



