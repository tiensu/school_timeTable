# file: build_timetable.py
import os
from collections import defaultdict
from ortools.sat.python import cp_model
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

# ======= CONFIG =======
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/timetable")
MAX_SOLVE_SECONDS = int(os.getenv("MAX_SOLVE_SECONDS", "60"))
# ======================

# ==== Import models từ app của bạn ====
from app.models.model import Base
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.timetable_model import Timetable  # __tablename__="timetables"
from app.models.timetable_slot_model import TimetableSlot

# ==== Kết nối DB ====
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5}
SESSION_ORDER = {"morning": 0, "afternoon": 1}

# ---------------------------
# Load & chuẩn hóa dữ liệu
# ---------------------------
def load_data(db):
    """
    Dựng nhu cầu R_name theo Class ⇄ Subject (N–N).
    R_name[(class_name, subject_code)] = subject.lesson_per_week
    """
    classes = db.query(Class).all()
    subjects = db.query(Subject).all()
    slots = db.query(TimetableSlot).all()
    teachers = db.query(Teacher).all()

    # Nhu cầu tiết/tuần cho mỗi (class_name, subject_code)
    R_name = {}
    for c in classes:
        for s in getattr(c, "subjects", []) or []:
            weekly = int(s.lesson_per_week or 0)
            if weekly > 0:
                R_name[(c.name, s.code)] = weekly

    # Chỉ giữ subjects có xuất hiện ở ít nhất một lớp
    subjects = [s for s in subjects if any((c.name, s.code) in R_name for c in classes)]

    # Sắp slot theo thời gian
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

    # quota thực tế theo GV (giới hạn bởi số slot rảnh)
    Cap = {}
    for t in teachers:
        eff_slots = sum(1 for k in slots if Avail.get((t.id, k.id), False))
        Cap[t.id] = min(int(t.max_weekly_lessons or 0), eff_slots)

    return {
        "classes": classes,
        "subjects": subjects,
        "slots": slots,
        "slots_sorted": slots_sorted,
        "teachers": teachers,
        "R_name": R_name,     # (class_name, subject_code) -> lessons/week
        "TeachOK": TeachOK,
        "Avail": Avail,
        "Cap": Cap,
    }

# --------------------------------------
# Tiền kiểm: cân bằng theo từng môn
# --------------------------------------
def subject_demands(data):
    """ demand[s_code] = tổng số tiết/tuần cần cho môn s_code (tổng cộng mọi lớp). """
    demand = defaultdict(int)
    for (_, s_code), need in data["R_name"].items():
        demand[s_code] += need
    return dict(demand)

def compute_subject_coverage_lp(data, time_limit=10.0):
    """
    Tính khả năng bao phủ tối đa theo từng môn (không sửa dữ liệu).
    Biến y[t,s] ∈ Z≥0: số tiết GV t dạy môn s (tổng mọi lớp).
      - ∑_s y[t,s] ≤ Cap[t]
      - ∑_t y[t,s] ≤ demand[s]
      - y[t,s]=0 nếu TeachOK(t,s)=False
    Maximize ∑_t,s y[t,s]
    Trả về: covered_per_subject (s_code->int), objective_value
    """
    teachers = data["teachers"]
    TeachOK  = data["TeachOK"]
    Cap      = data["Cap"]
    demand   = subject_demands(data)

    model = cp_model.CpModel()
    # Biến
    Y = {}  # (tid, s_code) -> IntVar
    for t in teachers:
        for s_code in demand.keys():
            if TeachOK.get((t.id, s_code), False):
                # upper bound: không cần vượt quá cả cap GV lẫn demand môn
                ub = min(Cap[t.id], demand[s_code])
                Y[(t.id, s_code)] = model.NewIntVar(0, ub, f"y_t{t.id}_{s_code}")

    # ∑_s y[t,s] ≤ Cap[t]
    for t in teachers:
        terms = [Y[(t.id, sc)] for sc in demand.keys() if (t.id, sc) in Y]
        if terms:
            model.Add(sum(terms) <= Cap[t.id])

    # ∑_t y[t,s] ≤ demand[s]
    for sc, dem in demand.items():
        terms = [Y[(t.id, sc)] for t in teachers if (t.id, sc) in Y]
        if terms:
            model.Add(sum(terms) <= dem)

    # Maximize tổng bao phủ
    all_vars = list(Y.values())
    if all_vars:
        model.Maximize(sum(all_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    covered = {sc: 0 for sc in demand.keys()}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (tid, sc), var in Y.items():
            covered[sc] += solver.Value(var)
        return covered, int(solver.ObjectiveValue()), status
    else:
        # Không giải được (hiếm): coi như không bao phủ gì
        return covered, 0, status

def subject_balance_report(data):
    """In báo cáo thừa/thiếu từng môn, và trả về dict thiếu/thừa."""
    demand = subject_demands(data)
    covered, obj, status = compute_subject_coverage_lp(data, time_limit=10.0)

    print("---- SUBJECT BALANCE (exact aggregate LP) ----")
    deficits = {}
    surpluses = {}
    for sc in sorted(demand.keys()):
        d = demand[sc]
        c = covered.get(sc, 0)
        if c < d:
            print(f"\033[91m{sc:10s} demand={d:3d} covered={c:3d}  DEFICIT={d-c}\033[0m")
            deficits[sc] = d - c
        else:
            # c <= d do ràng buộc, nên surplus ở đây là 0; ta log thêm potential_naive cho tham khảo
            print(f"{sc:10s} demand={d:3d} covered={c:3d}  OK")
            surpluses[sc] = 0

    total_demand = sum(demand.values())
    print(f"TOTAL  demand={total_demand}  covered={obj}  status={status}")
    return deficits, surpluses

# ---------------------------
# Dựng & giải TKB chi tiết
# ---------------------------
def build_and_solve(data):
    """Trả về (class_name, subject_code, teacher_code, slot_id)."""
    classes = data["classes"]
    subjects = data["subjects"]
    slots = data["slots"]
    slots_sorted = data["slots_sorted"]
    teachers = data["teachers"]
    R_name = data["R_name"]
    TeachOK = data["TeachOK"]
    Avail = data["Avail"]
    Cap = data["Cap"]

    DISABLE_CAP = os.getenv("DISABLE_CAP", "0") == "1"
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

    # (1) Đủ số tiết cho mỗi (class_name, subject_code)
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

    # (5) Giới hạn tổng số tiết/tuần của GV (có công tắc bỏ để test)
    if not DISABLE_CAP:
        for t in teachers:
            model.Add(
                sum(X[(l.name, s.code, t.id, k.id)]
                    for l in classes for s in subjects for k in slots
                    if (l.name, s.code, t.id, k.id) in X) <= Cap[t.id]
            )
    else:
        print("⚠️ DISABLE_CAP=1 → tạm bỏ quota GV để test tính khả thi.")

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

# =========================
#  Báo cáo & chẩn đoán
# =========================
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
    total_slots = len(slots)
    for c in classes:
        need_total = sum(R_name.get((c.name, s.code), 0) for s in subjects)
        print(f"[Class {c.name}] need={need_total}, slots={total_slots}")
        if need_total > total_slots:
            print(f"  !! Không đủ slot cho lớp {c.name}")

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

    for t in teachers:
        cap = Cap[t.id]
        avail_slots = sum(1 for k in slots if Avail.get((t.id, k.id), False))
        print(f"[Teacher {t.code}] cap={cap}, avail_slots={avail_slots}")

def class_subject_balance_report(data, time_limit=15.0):
    """
    Kiểm tra bao phủ ở cấp (class_name, subject_code).
    Biến y[t,c,s] ∈ Z≥0: số tiết GV t dạy cho lớp c, môn s (tổng theo tuần).
      - ∑_{c,s} y[t,c,s] ≤ Cap[t]
      - ∑_{t}   y[t,c,s] ≤ need[c,s] (= R_name[(c,s)])
      - y[t,c,s] = 0 nếu TeachOK(t,s)=False
    Maximize ∑ y[t,c,s]
    In ra thiếu/thừa theo từng lớp–môn. Mặc định chỉ in thiếu; đặt VERBOSE_CLASS_SUBJECT=1 để in tất cả.
    """
    classes  = data["classes"]
    teachers = data["teachers"]
    Cap      = data["Cap"]
    TeachOK  = data["TeachOK"]
    R_name   = data["R_name"]

    # Tập (c,s) có nhu cầu
    pairs = [(c.name, s_code) for (c, s_code) in
             [(c, sc) for c in classes for sc in set(sc for (_, sc) in R_name.keys())]
             if R_name.get((c.name, s_code), 0) > 0]

    model = cp_model.CpModel()
    Y = {}  # (tid, class_name, s_code) -> IntVar

    # Tạo biến với upper bound hợp lý
    for t in teachers:
        cap_t = Cap[t.id]
        if cap_t <= 0:
            continue
        for (cname, scode) in pairs:
            need_cs = R_name[(cname, scode)]
            if need_cs <= 0:
                continue
            if not TeachOK.get((t.id, scode), False):
                continue
            ub = min(cap_t, need_cs)
            Y[(t.id, cname, scode)] = model.NewIntVar(0, ub, f"y_t{t.id}_{cname}_{scode}")

    # Quota theo giáo viên
    for t in teachers:
        vars_t = [var for (tid, _, _), var in Y.items() if tid == t.id]
        if vars_t:
            model.Add(sum(vars_t) <= Cap[t.id])

    # Nhu cầu theo từng (class, subject)
    for (cname, scode) in pairs:
        vars_cs = [var for (tid, cn, sc), var in Y.items() if cn == cname and sc == scode]
        if vars_cs:
            model.Add(sum(vars_cs) <= R_name[(cname, scode)])

    # Mục tiêu
    if Y:
        model.Maximize(sum(Y.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    # Tổng hợp kết quả
    covered_cs = defaultdict(int)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for key, var in Y.items():
            covered_cs[(key[1], key[2])] += solver.Value(var)

    # Log
    verbose = os.getenv("VERBOSE_CLASS_SUBJECT", "0") == "1"
    print("---- CLASS–SUBJECT BALANCE (exact LP by class) ----")
    deficits_cs = {}
    for (cname, scode) in sorted(pairs):
        need = R_name[(cname, scode)]
        cov  = covered_cs.get((cname, scode), 0)
        if cov < need:
            print(f"\033[91m[{cname}-{scode}] need={need:2d}  covered={cov:2d}  DEFICIT={need-cov}\033[0m")
            deficits_cs[(cname, scode)] = need - cov
        elif verbose:
            print(f"[{cname}-{scode}] need={need:2d}  covered={cov:2d}  OK")

    total_need = sum(R_name.values())
    total_cov  = sum(covered_cs.values())
    print(f"TOTAL  need={total_need}  covered={total_cov}  status={status}")

    # Tính thiếu theo từng môn (gộp các lớp) để bạn dễ nhìn
    per_subject_missing = defaultdict(int)
    per_class_missing   = defaultdict(int)
    for (cname, scode), miss in deficits_cs.items():
        per_subject_missing[scode] += miss
        per_class_missing[cname]   += miss

    if deficits_cs:
        print("---- MISSING by subject (sum over classes) ----")
        for sc in sorted(per_subject_missing.keys()):
            print(f"\033[91m{sc:10s}  MISSING={per_subject_missing[sc]}\033[0m")

        print("---- MISSING by class (sum over subjects) ----")
        for cn in sorted(per_class_missing.keys()):
            print(f"\033[91m{cn:8s}  MISSING={per_class_missing[cn]}\033[0m")

    return deficits_cs  # dict[(class_name, subject_code)] = missing


def gen_timetable():
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        data = load_data(db)
        sanity_report(data)

        # Tiền kiểm
        deficits_by_subject, _ = subject_balance_report(data)
        deficits_by_class_subject = class_subject_balance_report(data)

        if deficits_by_subject or deficits_by_class_subject:
            logger.info("❌ Thiếu giáo viên. Không tạo thời khóa biểu.")

            return {
                "success": False,
                "subject_missing": deficits_by_subject,  # Dict[str, int]
                "class_subject_missing": {f"{cls} – {subj}": miss for (cls, subj), miss in deficits_by_class_subject.items()}
            }


        # Nếu đủ thì tạo TKB
        assignments = build_and_solve(data)
        n = write_timetable(db, assignments, wipe_existing=True)
        logger.info(f"✅ Đã ghi {n} dòng vào bảng timetables.")
        return {
            "success": True,
            "message": f"Đã tạo {n} dòng thời khóa biểu thành công."
        }

    finally:
        db.close()

if __name__ == "__main__":
    gen_timetable()
