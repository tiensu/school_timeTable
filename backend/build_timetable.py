# file: build_timetable.py
import os
from collections import defaultdict
from ortools.sat.python import cp_model
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ======= CONFIG =======
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/timetable")
MAX_SOLVE_SECONDS = int(os.getenv("MAX_SOLVE_SECONDS", "60"))
# ======================

# ==== Import models từ app của bạn ====
from app.models.model import Base
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.class_subject_model import ClassSubject
from app.models.timetable_model import Timetable  # __tablename__="timetables"
from app.models.timetable_slot_model import TimetableSlot

# Teacher cần có:
# - subjects: relationship đến Subject (N-N)
# - unavailable_slots: relationship đến TimetableSlot (N-N)
# - max_weekly_lessons, available_morning, available_afternoon

# ==== Kết nối DB ====
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5}
SESSION_ORDER = {"morning": 0, "afternoon": 1}

def load_data(db):
    """Load dữ liệu & chuẩn hóa theo class_name."""
    classes = db.query(Class).all()
    subjects = db.query(Subject).all()
    slots = db.query(TimetableSlot).all()
    teachers = db.query(Teacher).all()

    # R_name: (class_name, subject_code) -> lessons_per_week
    class_subject_reqs = db.query(ClassSubject).all()
    R_name = {}
    for r in class_subject_reqs:
        key = (r.class_name, r.subject_code)
        R_name[key] = R_name.get(key, 0) + int(r.lessons_per_week or 0)

    # Chỉ giữ subjects có yêu cầu thực tế
    subjects = [s for s in subjects if any((c.name, s.code) in R_name for c in classes)]

    # Sắp slot theo thời gian (để làm soft constraint)
    slots_sorted = sorted(
        slots,
        key=lambda k: (DAY_ORDER.get(k.day_of_week, 99),
                       SESSION_ORDER.get(k.session, 9),
                       k.period)
    )

    # TeachOK (teacher_id, subject_code) -> bool
    TeachOK = defaultdict(bool)
    for t in teachers:
        for s in t.subjects:
            TeachOK[(t.id, s.code)] = True

    # Avail (teacher_id, slot_id) -> bool
    unavailable_by_teacher = {t.id: {sl.id for sl in t.unavailable_slots} for t in teachers}
    Avail = defaultdict(bool)
    for t in teachers:
        for k in slots:
            if k.id in unavailable_by_teacher[t.id]:
                Avail[(t.id, k.id)] = False
                continue
            if k.session == "morning" and not (t.available_morning or False):
                Avail[(t.id, k.id)] = False
                continue
            if k.session == "afternoon" and not (t.available_afternoon or False):
                Avail[(t.id, k.id)] = False
                continue
            Avail[(t.id, k.id)] = True

    Cap = {t.id: int(t.max_weekly_lessons or 0) for t in teachers}

    return {
        "classes": classes,
        "subjects": subjects,
        "slots": slots,
        "slots_sorted": slots_sorted,
        "teachers": teachers,
        "R_name": R_name,
        "TeachOK": TeachOK,
        "Avail": Avail,
        "Cap": Cap,
    }

def build_and_solve(data):
    """Build CP-SAT model theo class_name, solve, trả về (class_name, subject_code, teacher_code, slot_id)."""
    classes = data["classes"]
    subjects = data["subjects"]
    slots = data["slots"]
    slots_sorted = data["slots_sorted"]
    teachers = data["teachers"]
    R_name = data["R_name"]
    TeachOK = data["TeachOK"]
    Avail = data["Avail"]
    Cap = data["Cap"]

    teachers_by_id = {t.id: t for t in teachers}

    model = cp_model.CpModel()

    # Biến x[l_name, s_code, t_id, k_id] ∈ {0,1}
    X = {}
    for l in classes:
        for s in subjects:
            need = R_name.get((l.name, s.code), 0)
            if need <= 0:
                continue
            for t in teachers:
                if not TeachOK.get((t.id, s.code), False):
                    continue
                for k in slots:
                    if not Avail.get((t.id, k.id), False):
                        continue
                    X[(l.name, s.code, t.id, k.id)] = model.NewBoolVar(
                        f"x_l{l.name}_s{s.code}_t{t.id}_k{k.id}"
                    )

    # (1) Đủ số tiết cho mỗi (class_name, subject)
    for l in classes:
        for s in subjects:
            need = R_name.get((l.name, s.code), 0)
            if need > 0:
                model.Add(
                    sum(X[(l.name, s.code, t.id, k.id)]
                        for t in teachers for k in slots
                        if (l.name, s.code, t.id, k.id) in X) == need
                )

    # (2) Lớp không trùng slot
    for l in classes:
        for k in slots:
            model.Add(
                sum(X[(l.name, s.code, t.id, k.id)]
                    for s in subjects for t in teachers
                    if (l.name, s.code, t.id, k.id) in X) <= 1
            )

    # (3) GV không trùng slot
    for t in teachers:
        for k in slots:
            model.Add(
                sum(X[(l.name, s.code, t.id, k.id)]
                    for l in classes for s in subjects
                    if (l.name, s.code, t.id, k.id) in X) <= 1
            )

    # (5) Giới hạn tổng số tiết/tuần của GV
    for t in teachers:
        model.Add(
            sum(X[(l.name, s.code, t.id, k.id)]
                for l in classes for s in subjects for k in slots
                if (l.name, s.code, t.id, k.id) in X) <= Cap[t.id]
        )

    # Soft: tránh 2 tiết liền nhau cùng môn cho mỗi lớp
    penalties = []
    for l in classes:
        for s in subjects:
            for i in range(len(slots_sorted) - 1):
                k1 = slots_sorted[i]
                k2 = slots_sorted[i + 1]
                y = model.NewBoolVar(f"consec_{l.name}_{s.code}_{k1.id}_{k2.id}")
                sum_k1 = sum(X.get((l.name, s.code, t.id, k1.id), 0) for t in teachers)
                sum_k2 = sum(X.get((l.name, s.code, t.id, k2.id), 0) for t in teachers)
                model.Add(y <= sum_k1)
                model.Add(y <= sum_k2)
                model.Add(y >= sum_k1 + sum_k2 - 1)
                penalties.append((y, 1))

    if penalties:
        model.Minimize(sum(w * var for var, w in penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_SOLVE_SECONDS
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Không tìm được thời khóa biểu khả thi. status={status}")

    # Xuất kết quả (class_name, subject_code, teacher_code, slot_id)
    result = []
    for (l_name, s_code, t_id, k_id), var in X.items():
        if solver.Value(var) == 1:
            result.append((l_name, s_code, teachers_by_id[t_id].code, k_id))
    return result

def write_timetable(db, assignments, wipe_existing=True):
    """Ghi vào bảng timetables theo class_name."""
    if wipe_existing:
        db.query(Timetable).delete()
        db.commit()
    rows = [
        Timetable(class_name=l_name, subject_code=s_code, teacher_code=t_code, slot_id=k_id)
        for (l_name, s_code, t_code, k_id) in assignments
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)

def sanity_report(data):
    classes = data["classes"]
    subjects = data["subjects"]
    teachers = data["teachers"]
    slots = data["slots"]
    R_name = data["R_name"]
    TeachOK = data["TeachOK"]
    Avail = data["Avail"]
    Cap = data["Cap"]

    print("---- SANITY REPORT ----")
    # A. nhu cầu / số slot
    total_slots = len(slots)
    for c in classes:
        need_total = sum(R_name.get((c.name, s.code), 0) for s in subjects)
        print(f"[Class {c.name}] need={need_total}, slots={total_slots}")
        if need_total > total_slots:
            print(f"  !! Không đủ slot cho lớp {c.name}")

    # B. mỗi (class,subject): số biến ứng viên (t,k)
    for c in classes:
        for s in subjects:
            need = R_name.get((c.name, s.code), 0)
            if need <= 0: 
                continue
            candidates = 0
            teachers_ok = [t for t in teachers if TeachOK.get((t.id, s.code), False)]
            for t in teachers_ok:
                for k in slots:
                    if Avail.get((t.id, k.id), False):
                        candidates += 1
            print(f"[{c.name}-{s.code}] need={need}, candidates={candidates}, teachers_ok={len(teachers_ok)}")
            if candidates < need:
                print(f"  !! Ứng viên < nhu cầu → INFEASIBLE")

    # C. quota GV
    for t in teachers:
        cap = Cap[t.id]
        # số slot GV thật sự có thể dạy
        avail_slots = sum(1 for k in slots if Avail.get((t.id, k.id), False))
        print(f"[Teacher {t.code}] cap={cap}, avail_slots={avail_slots}")


def main():
    db = SessionLocal()
    try:
        # Đảm bảo bảng tồn tại (nếu bạn dùng Alembic có thể bỏ dòng này)
        Base.metadata.create_all(bind=engine)

        data = load_data(db)
        sanity_report(data)
        if not data["R_name"]:
            raise RuntimeError("Thiếu yêu cầu class_subjects (R_name). Hãy seed bảng class_subjects trước.")
        if not data["slots"]:
            raise RuntimeError("Thiếu timetable_slots.")
        if not data["teachers"]:
            raise RuntimeError("Thiếu teachers.")
        if not data["subjects"]:
            raise RuntimeError("Thiếu subjects được yêu cầu.")

        assignments = build_and_solve(data)
        n = write_timetable(db, assignments, wipe_existing=True)
        print(f"✅ Đã ghi {n} dòng vào bảng timetables.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
