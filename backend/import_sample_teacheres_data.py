# import_sample_classes_data.py
import random
random.seed(42)
from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.timetable_slot_model import TimetableSlot
# from app.models.class_subject_model import class_subject_association

db: Session = SessionLocal()

# --- 3) GIÁO VIÊN (81 người) ---

# Lấy sẵn subject objects & utility
all_subjects = db.query(Subject).order_by(Subject.code.asc()).all()
subject_by_code = {s.code: s for s in all_subjects}

# Danh sách ngày/buổi/tiết để gán unavailable_slots (khớp seed slot: 5 tiết/buổi)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SESSIONS = ["morning", "afternoon"]
PERIODS = [1, 2, 3, 4, 5]

def get_slot_by_label(db_sess, label: str):
    # "Monday-morning-1" -> TimetableSlot
    d, sess, per = label.split("-")
    return db_sess.query(TimetableSlot).filter_by(
        day_of_week=d, session=sess, period=int(per)
    ).first()

# Tạo 81 giáo viên: gv001..gv081
def seed_teachers():
    created = 0
    subject_codes_cycle = [s.code for s in all_subjects]  # vòng tròn gán môn
    idx = 0

    for n in range(1, 82):
        code = f"gv{n:03d}"
        if db.query(Teacher).filter_by(code=code).first():
            continue

        # Tạo tên đơn giản cho nhanh (có thể thay bằng danh sách tên thật)
        name = f"Giáo viên {n:03d}"

        # quota 16–22 tiết/tuần
        cap = random.choice([16, 18, 20, 22])

        # availability: phần lớn dạy cả sáng/chiều; đôi khi chỉ 1 buổi
        am = True
        pm = True
        if random.random() < 0.15:
            am, pm = True, False
        elif random.random() < 0.15:
            am, pm = False, True

        t = Teacher(
            code=code,
            name=name,
            max_weekly_lessons=cap,
            available_morning=am,
            available_afternoon=pm,
            status="active",
        )

        # Gán 2–3 môn/giáo viên (round-robin + một ít ngẫu nhiên)
        k = random.choice([2, 3])
        assigned_codes = []
        for _ in range(k):
            # Bỏ môn ELECT nếu muốn giới hạn (nhưng vẫn cho 1 phần GV dạy ELECT cho khối 11)
            pick = subject_codes_cycle[idx % len(subject_codes_cycle)]
            idx += 1
            if pick == "ELECT" and random.random() < 0.5:
                # 50% GV không dạy ELECT
                pick = subject_codes_cycle[idx % len(subject_codes_cycle)]
                idx += 1
            if pick not in assigned_codes:
                assigned_codes.append(pick)

        for sc in assigned_codes:
            subj = subject_by_code.get(sc)
            if subj:
                t.subjects.append(subj)

        # Gán 0–3 slot bận
        busy_count = random.choice([0, 1, 2, 3])
        # Lấy các slot label ngẫu nhiên, nhưng chỉ append nếu slot tồn tại
        labels = set()
        while len(labels) < busy_count:
            label = f"{random.choice(DAYS)}-{random.choice(SESSIONS)}-{random.choice(PERIODS)}"
            labels.add(label)
        for label in labels:
            slot = get_slot_by_label(db, label)
            if slot:
                t.unavailable_slots.append(slot)

        db.add(t)
        created += 1

    if created:
        db.commit()

seed_teachers()

print("✅ Dữ liệu mẫu giáo viên đã được import thành công.")