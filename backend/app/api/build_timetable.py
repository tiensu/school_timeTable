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

# ==== Import models từ app của bạn === =
from app.models.model import Base
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.timetable_model import Timetable
from app.models.timetable_slot_model import TimetableSlot
from app.models.class_subject_teacher_model import ClassSubjectTeacher
from app.models.teacher_x_slot_model import Teacher_X_Slot

DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5, "Saturday": 6}

# ==== Kết nối DB === =
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------
# Load & chuẩn hóa dữ liệu
# ---------------------------
def load_data(db):
    """
    Chuẩn hóa dữ liệu đầu vào, áp dụng các quy tắc đặc biệt cho lớp 12.
    Trả về dict chứa các thông tin cần thiết cho lập thời khóa biểu.
    """
    # 1. Chỉ lấy lớp 12
    classes = db.query(Class).filter(Class.name.like("12%")).all()
    subjects = db.query(Subject).all()
    # 2. Chỉ lấy slot buổi sáng
    slots = db.query(TimetableSlot).filter(TimetableSlot.session == "morning").all()
    slots_sorted = sorted(
        slots,
        key=lambda k: (DAY_ORDER.get(k.day_of_week, 99), k.period)
    )
    teachers = db.query(Teacher).all()
    # 3. Lấy phân công giáo viên–môn–lớp
    cst_rows = db.query(ClassSubjectTeacher).all()
    allowed_cst = set((row.class_name, row.subject_code, row.teacher_code) for row in cst_rows)

    # 4. Tính số tiết/tuần cho từng lớp–môn, áp dụng quy tắc chuyên đề
    R_name = {}
    for c in classes:
        for s in getattr(c, "subjects", []) or []:
            weekly = int(s.lesson_per_week or 0)
            spec = (c.specialized_class or "").strip()
            # Quy tắc cộng thêm tiết cho lớp chuyên đề
            if spec == "T-L-H" and s.code in ["HOA", "LY"]:
                weekly += 1
            if spec == "T-V-Địa" and s.code in ["VAN", "DIA"]:
                weekly += 1
            if spec == "T-V-Sử" and s.code in ["VAN", "SUI"]:
                weekly += 1
            if spec == "T-H-Sinh" and s.code in ["HOA", "SINH"]:
                weekly += 1
            if weekly > 0:
                R_name[(c.name, s.code)] = weekly

    # 5. Quy tắc: Giáo viên chủ nhiệm phải dạy SHL tiết 1 thứ 2
    TeachOK = defaultdict(bool)
    for t in teachers:
        if t.class_advisor and t.class_advisor.startswith("12"):
            class_name = t.class_advisor
            # Chỉ bổ sung quyền dạy SHL cho giáo viên chủ nhiệm lớp đó, KHÔNG cộng thêm tiết
            if (class_name, "SHL12") in R_name:
                TeachOK[(t.id, "SHL12", class_name)] = True

    # 6. Chỉ giữ các môn có xuất hiện ở ít nhất một lớp
    subjects = [s for s in subjects if any((c.name, s.code) in R_name for c in classes)]

    # 7. TeachOK (teacher_id, subject_code, class_name) -> bool
    for t in teachers:
        for s in t.subjects:
            for c in classes:
                if (c.name, s.code, t.code) in allowed_cst:
                    TeachOK[(t.id, s.code, c.name)] = True

    # 8. Avail (teacher_id, slot_id) -> bool
    unavailable_by_teacher = {t.id: {sl.id for sl in t.unavailable_slots} for t in teachers}
    Avail = defaultdict(bool)
    for t in teachers:
        for k in slots:
            if k.id in unavailable_by_teacher[t.id]:
                Avail[(t.id, k.id)] = False
                continue
            Avail[(t.id, k.id)] = True

    # 9. quota thực tế theo GV (giới hạn bởi số slot rảnh, không dùng max_weekly_x cho lớp học)
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
        "R_name": R_name,
        "TeachOK": TeachOK,
        "Avail": Avail,
        "Cap": Cap,
        "allowed_cst": allowed_cst,
    }

# --------------------------------------
# Tiền kiểm: cân bằng theo từng môn
# --------------------------------------
def subject_demands(data):
    """Tổng số tiết/tuần cần cho mỗi môn (gộp các lớp)."""
    demand = defaultdict(int)
    for (_, s_code), need in data["R_name"].items():
        demand[s_code] += need
    return dict(demand)

def compute_subject_coverage_lp(data, time_limit=10.0):
    """
    Kiểm tra khả năng bao phủ tiết theo từng môn.
    """
    teachers = data["teachers"]
    TeachOK  = data["TeachOK"]
    Cap      = data["Cap"]
    demand   = subject_demands(data)
    model = cp_model.CpModel()
    Y = {}
    for t in teachers:
        for s_code in demand.keys():
            # Chỉ xét các lớp mà giáo viên được phép dạy
            if any(TeachOK.get((t.id, s_code, c.name), False) for c in data["classes"]):
                ub = min(Cap[t.id], demand[s_code])
                Y[(t.id, s_code)] = model.NewIntVar(0, ub, f"y_t{t.id}_{s_code}")
    for t in teachers:
        terms = [Y[(t.id, sc)] for sc in demand.keys() if (t.id, sc) in Y]
        if terms:
            model.Add(sum(terms) <= Cap[t.id])
    for sc, dem in demand.items():
        terms = [Y[(t.id, sc)] for t in teachers if (t.id, sc) in Y]
        if terms:
            model.Add(sum(terms) <= dem)
    if Y:
        model.Maximize(sum(Y.values()))
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
        return covered, 0, status

def subject_balance_report(data):
    """In báo cáo thừa/thiếu từng môn, trả về dict thiếu/thừa."""
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
            print(f"{sc:10s} demand={d:3d} covered={c:3d}  OK")
            surpluses[sc] = 0
    total_demand = sum(demand.values())
    print(f"TOTAL  demand={total_demand}  covered={obj}  status={status}")
    return deficits, surpluses

# ---------------------------
# Dựng & giải TKB chi tiết
# ---------------------------
def build_and_solve(data):
    """
    Dựng mô hình tối ưu hóa thời khóa biểu, áp dụng các quy tắc đặc biệt.
    Trả về danh sách (class_name, subject_code, teacher_code, slot_id).
    """
    classes = data["classes"]
    subjects = data["subjects"]
    slots = data["slots"]
    slots_sorted = data["slots_sorted"]
    teachers = data["teachers"]
    R_name = data["R_name"]
    TeachOK = data["TeachOK"]
    Avail = data["Avail"]
    Cap = data["Cap"]
    allowed_cst = data["allowed_cst"]

    DISABLE_CAP = os.getenv("DISABLE_CAP", "0") == "1"
    teachers_by_id = {t.id: t for t in teachers}
    model = cp_model.CpModel()

    # Biến x[l_name, s_code, t_id, k_id] ∈ {0,1}
    X = {}
    # 1. Xử lý đặc biệt: Giáo viên chủ nhiệm phải dạy SHL tiết 1 thứ 2
    for t in teachers:
        if t.class_advisor and t.class_advisor.startswith("12"):
            class_name = t.class_advisor
            slot_shl = next((k for k in slots if k.day_of_week == "Monday" and k.period == 1), None)
            if slot_shl:
                # Chỉ tạo biến nếu lớp có môn SHL
                if R_name.get((class_name, "SHL12"), 0) > 0 and Avail.get((t.id, slot_shl.id), False):
                    X[(class_name, "SHL12", t.id, slot_shl.id)] = model.NewBoolVar(
                        f"x_l{class_name}_sSHL_t{t.id}_k{slot_shl.id}"
                    )
    # 2. Các trường hợp còn lại
    for l in classes:
        for s in subjects:
            need = R_name.get((l.name, s.code), 0)
            if need <= 0:
                continue
            for t in teachers:
                # Chỉ phân công giáo viên theo bảng class_subject_teacher
                if not TeachOK.get((t.id, s.code, l.name), False):
                    continue
                for k in slots:
                    if not Avail.get((t.id, k.id), False):
                        continue
                    # Tránh tạo lại biến SHL tiết 1 thứ 2 cho giáo viên chủ nhiệm
                    if (l.name == t.class_advisor and s.code == "SHL12" and k.day_of_week == "Monday" and k.period == 1):
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

    # (3) GV không trùng slot: mỗi giáo viên chỉ được dạy tối đa 1 lớp/môn trong cùng một slot
    for t in teachers:
        for k in slots:
            expr = [X[(l.name, s.code, t.id, k.id)]
                    for l in classes for s in subjects
                    if (l.name, s.code, t.id, k.id) in X]
            if expr:
                model.Add(sum(expr) <= 1)

    # (5) Giới hạn tổng số tiết/tuần của GV (không dùng max_weekly_x)
    if not DISABLE_CAP:
        for t in teachers:
            model.Add(
                sum(X[(l.name, s.code, t.id, k.id)]
                    for l in classes for s in subjects for k in slots
                    if (l.name, s.code, t.id, k.id) in X) <= Cap[t.id]
            )
    else:
        print("⚠️ DISABLE_CAP=1 → tạm bỏ quota GV để test tính khả thi.")

    # Quy tắc: Giáo viên chủ nhiệm phải dạy SHL vào tiết 1 thứ 2
    for t in teachers:
        if t.class_advisor and t.class_advisor.startswith("12"):
            class_name = t.class_advisor
            slot_shl = next((k for k in slots if k.day_of_week == "Monday" and k.period == 1), None)
            if slot_shl:
                key = (class_name, "SHL12", t.id, slot_shl.id)
                var = X.get(key)
                if var is not None:
                    model.Add(var == 1)

    # Soft: tránh 2 tiết liền nhau cùng môn cho mỗi lớp, trừ các môn >=4 tiết
    penalties = []
    for l in classes:
        for s in subjects:
            need = R_name.get((l.name, s.code), 0)
            allow_consec = need >= 4
            for i in range(len(slots_sorted) - 1):
                k1 = slots_sorted[i]
                k2 = slots_sorted[i + 1]
                if k1.day_of_week != k2.day_of_week:
                    continue
                y = model.NewBoolVar(f"consec_{l.name}_{s.code}_{k1.id}_{k2.id}")
                sum_k1 = sum(X.get((l.name, s.code, t.id, k1.id), 0) for t in teachers)
                sum_k2 = sum(X.get((l.name, s.code, t.id, k2.id), 0) for t in teachers)
                model.Add(y <= sum_k1)
                model.Add(y <= sum_k2)
                model.Add(y >= sum_k1 + sum_k2 - 1)
                if not allow_consec:
                    penalties.append((y, 1))
    if penalties:
        model.Minimize(sum(w * var for var, w in penalties))

    # (6) Không có tiết trống giữa các tiết trong 1 buổi
    for l in classes:
        for day in DAY_ORDER.keys():
            # Lấy các slot của buổi đó, sắp xếp theo period
            day_slots = sorted([k for k in slots if k.day_of_week == day], key=lambda k: k.period)
            n_periods = len(day_slots)
            if n_periods < 2:
                continue
            # Tạo biến phụ: có tiết học ở period i
            has_period = []
            for k in day_slots:
                var = model.NewBoolVar(f"has_{l.name}_{day}_{k.period}")
                model.Add(var == sum(X.get((l.name, s.code, t.id, k.id), 0) for s in subjects for t in teachers))
                has_period.append(var)
            # Nếu có tiết ở đầu và cuối buổi thì các tiết giữa phải có tiết
            for i in range(n_periods):
                for j in range(i + 2, n_periods):
                    # Nếu có tiết ở period i và period j thì các period giữa phải có tiết
                    for mid in range(i + 1, j):
                        model.Add(has_period[mid] >= has_period[i] + has_period[j] - 1)

    # (7) Số tiết trong 1 buổi phải từ 4 đến 5 tiết (nếu có tiết thì phải >=4)
    for l in classes:
        for day in DAY_ORDER.keys():
            day_slots = [k for k in slots if k.day_of_week == day]
            slot_ids = [k.id for k in day_slots]
            # Tổng số tiết của lớp l trong buổi day
            sum_period = sum(
                sum(X.get((l.name, s.code, t.id, k_id), 0) for s in subjects for t in teachers)
                for k_id in slot_ids
            )
            # Tạo biến phụ: lớp có học trong buổi này không
            has_any = model.NewBoolVar(f"has_any_{l.name}_{day}")
            # Nếu có tiết thì has_any = 1, ngược lại = 0
            model.Add(sum_period >= 1).OnlyEnforceIf(has_any)
            model.Add(sum_period == 0).OnlyEnforceIf(has_any.Not())
            # Nếu có học thì số tiết phải >=4 và <=5
            model.Add(sum_period >= 4).OnlyEnforceIf(has_any)
            model.Add(sum_period <= 5).OnlyEnforceIf(has_any)

    # (8) Mỗi tiết phải có 1 giáo viên Trực X (trừ tiết 1 sáng thứ 2)
    direct_teachers = [t for t in teachers if getattr(t, "max_weekly_x", 0) > 0]
    DirectX = {}  # DirectX[(t.id, k.id)] = BoolVar: giáo viên t trực X tại slot k
    for k in slots:
        if k.day_of_week == "Monday" and k.period == 1:
            continue  # Bỏ qua tiết 1 sáng thứ 2
        # Tạo biến trực X cho từng giáo viên có max_weekly_x > 0
        for t in direct_teachers:
            DirectX[(t.id, k.id)] = model.NewBoolVar(f"directX_t{t.id}_k{k.id}")
        # Mỗi slot phải có đúng 1 giáo viên trực X
        model.Add(
            sum(DirectX[(t.id, k.id)] for t in direct_teachers) == 1
        )
        # Giáo viên trực X không được dạy tiết đó
        for t in direct_teachers:
            for l in classes:
                for s in subjects:
                    if (l.name, s.code, t.id, k.id) in X:
                        model.Add(X[(l.name, s.code, t.id, k.id)] + DirectX[(t.id, k.id)] <= 1)

    # Tổng số tiết trực X của mỗi giáo viên không vượt quá max_weekly_x
    for t in direct_teachers:
        model.Add(
            sum(DirectX[(t.id, k.id)] for k in slots
                if (k.day_of_week != "Monday" or k.period != 1)) <= t.max_weekly_x
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = MAX_SOLVE_SECONDS
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 42  # Đặt seed cố định để kết quả lặp lại

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Không tìm được thời khóa biểu khả thi. status={status}")

    # Xuất kết quả (class_name, subject_code, teacher_code, slot_id)
    result = []
    direct_x_assignments = []
    for (l_name, s_code, t_id, k_id), var in X.items():
        if solver.Value(var) == 1:
            result.append((l_name, s_code, teachers_by_id[t_id].code, k_id))

    # Log giáo viên trực X cho từng tiết
    print("\n---- Giáo viên trực X từng tiết ----")
    for k in slots:
        if k.day_of_week == "Monday" and k.period == 1:
            continue
        for t in direct_teachers:
            key = (t.id, k.id)
            if key in DirectX and solver.Value(DirectX[key]) == 1:
                print(f"Slot {k.day_of_week} - Tiết {k.period}: {t.name} (Trực X)")
                direct_x_assignments.append((t.code, k.id))
                break

    # Kiểm tra giáo viên bị trùng slot (dạy nhiều lớp trong cùng một tiết)
    from collections import defaultdict
    slot_teacher_map = defaultdict(list)
    for (l_name, s_code, t_id, k_id), var in X.items():
        if solver.Value(var) == 1:
            slot_teacher_map[(t_id, k_id)].append((l_name, s_code))
    print("\n---- Kiểm tra giáo viên bị trùng slot ----")
    for (t_id, k_id), assigns in slot_teacher_map.items():
        if len(assigns) > 1:
            teacher = teachers_by_id[t_id]
            print(f"\033[91mGiáo viên {teacher.code} ({teacher.name}) dạy nhiều lớp/môn tại slot id={k_id}: {assigns}\033[0m")

    return result, direct_x_assignments

def write_timetable(db, assignments, direct_x_assignments, wipe_existing=True):
    """Ghi vào bảng timetables và teacher_x_slots."""
    if wipe_existing:
        db.query(Timetable).delete()
        db.query(Teacher_X_Slot).delete()
        db.commit()
    rows = [
        Timetable(class_name=l_name, subject_code=s_code, teacher_code=t_code, slot_id=k_id)
        for (l_name, s_code, t_code, k_id) in assignments
    ]
    db.add_all(rows)
    # Lưu giáo viên trực X
    direct_x_rows = [
        Teacher_X_Slot(teacher_code=t_code, slot_id=k_id)
        for (t_code, k_id) in direct_x_assignments
    ]
    db.add_all(direct_x_rows)
    db.commit()
    return len(rows), len(direct_x_rows)

# =========================
#  Báo cáo & chẩn đoán
# =========================
def sanity_report(data):
    """
    Kiểm tra nhanh dữ liệu đầu vào: số slot, số tiết, số ứng viên cho từng lớp–môn.
    """
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
            teachers_ok = [t for t in teachers if TeachOK.get((t.id, s.code, c.name), False)]
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
    
    print("\n---- KIỂM TRA CHI TIẾT DỮ LIỆU ĐẦU VÀO ----")
    # 1. Lớp-môn không có giáo viên nào đủ điều kiện dạy
    for c in classes:
        for s in subjects:
            need = R_name.get((c.name, s.code), 0)
            if need <= 0:
                continue
            teachers_ok = [t for t in teachers if TeachOK.get((t.id, s.code, c.name), False)]
            if not teachers_ok:
                print(f"\033[91mLớp {c.name} - Môn {s.code} không có giáo viên nào đủ điều kiện dạy!\033[0m")

    # 2. Giáo viên có số slot rảnh quá ít so với quota
    for t in teachers:
        cap = Cap[t.id]
        avail_slots = sum(1 for k in slots if Avail.get((t.id, k.id), False))
        if avail_slots < cap:
            print(f"\033[93mGiáo viên {t.code} ({t.name}) quota={cap}, slot rảnh={avail_slots} < quota!\033[0m")

    # 3. Lớp-môn có số tiết cần dạy vượt quá số slot
    for c in classes:
        for s in subjects:
            need = R_name.get((c.name, s.code), 0)
            if need <= 0:
                continue
            total_slots = len(slots)
            if need > total_slots:
                print(f"\033[91mLớp {c.name} - Môn {s.code} cần {need} tiết, nhưng chỉ có {total_slots} slot!\033[0m")

def class_subject_balance_report(data, time_limit=15.0):
    """
    Kiểm tra bao phủ ở cấp (class_name, subject_code).
    Biến y[t,c,s] ∈ Z≥0: số tiết GV t dạy cho lớp c, môn s (tổng theo tuần).
    """
    classes  = data["classes"]
    teachers = data["teachers"]
    Cap      = data["Cap"]
    TeachOK  = data["TeachOK"]
    R_name   = data["R_name"]

    pairs = [(c.name, s_code) for (c, s_code) in
             [(c, sc) for c in classes for sc in set(sc for (_, sc) in R_name.keys())]
             if R_name.get((c.name, s_code), 0) > 0]

    model = cp_model.CpModel()
    Y = {}
    for t in teachers:
        cap_t = Cap[t.id]
        if cap_t <= 0:
            continue
        for (cname, scode) in pairs:
            need_cs = R_name[(cname, scode)]
            if need_cs <= 0:
                continue
            if not TeachOK.get((t.id, scode, cname), False):
                continue
            ub = min(cap_t, need_cs)
            Y[(t.id, cname, scode)] = model.NewIntVar(0, ub, f"y_t{t.id}_{cname}_{scode}")

    for t in teachers:
        vars_t = [var for (tid, _, _), var in Y.items() if tid == t.id]
        if vars_t:
            model.Add(sum(vars_t) <= Cap[t.id])

    for (cname, scode) in pairs:
        vars_cs = [var for (tid, cn, sc), var in Y.items() if cn == cname and sc == scode]
        if vars_cs:
            model.Add(sum(vars_cs) <= R_name[(cname, scode)])

    if Y:
        model.Maximize(sum(Y.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    covered_cs = defaultdict(int)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for key, var in Y.items():
            covered_cs[(key[1], key[2])] += solver.Value(var)

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
        # Tiền kiểm tổng theo môn
        deficits_by_subject, _ = subject_balance_report(data)
        # Tiền kiểm chi tiết theo lớp–môn
        deficits_by_class_subject = class_subject_balance_report(data)
        if deficits_by_subject or deficits_by_class_subject:
            msg = "❌ Thiếu giáo viên. Không tạo thời khóa biểu."
            print("\n" + msg)
            return {
                "success": False,
                "message": msg,
                "subject_missing": deficits_by_subject,
                "class_subject_missing": {f"{cls}-{subj}": miss for (cls, subj), miss in deficits_by_class_subject.items()}
            }
        assignments, direct_x_assignments = build_and_solve(data)
        n, n_x = write_timetable(db, assignments, direct_x_assignments, wipe_existing=True)
        msg = f"✅ Đã ghi {n} dòng vào bảng timetables. Đã ghi {n_x} dòng vào bảng teacher_x_slots."
        return {
            "success": True,
            "message": msg
        }
    finally:
        db.close()

if __name__ == "__main__":
    gen_timetable()
