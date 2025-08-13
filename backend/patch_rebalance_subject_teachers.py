# -*- coding: utf-8 -*-
"""
Tự động bù giáo viên cho các subject_code thiếu (theo conservative upper-bound).
Chạy:  python patch_rebalance_subject_teachers.py
Sau đó: unset DISABLE_CAP và chạy lại build_timetable.py
"""

from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.timetable_slot_model import TimetableSlot

DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
SESS = ["morning","afternoon"]

# Các họ môn “nặng” ưu tiên tăng quota nếu cần
HEAVY_PREFIXES = ("MATH_", "LIT_")

# Giới hạn quota sau khi boost
HEAVY_TARGET_CAP = 22

def compute_conservative_deficits(db: Session):
    """Trả về (demand, supply_upper, deficit) theo conservative method trong build_timetable."""
    # R_name: (class_name, subject_code) -> lessons/week
    demand = defaultdict(int)
    # dựng R_name từ quan hệ Class ↔ Subject và lesson_per_week
    from app.models.classes_model import Class
    classes = db.query(Class).all()
    for c in classes:
        for s in getattr(c, "subjects", []) or []:
            w = int(s.lesson_per_week or 0)
            if w > 0:
                demand[s.code] += w

    # TeachOK, Cap, Avail
    teachers = db.query(Teacher).all()
    caps = {t.id: int(t.max_weekly_lessons or 0) for t in teachers}

    # Avail slots per teacher
    slots = db.query(TimetableSlot).all()
    avail = set()
    unavail = {t.id: {sl.id for sl in t.unavailable_slots} for t in teachers}
    for t in teachers:
        for k in slots:
            if k.id in unavail[t.id]: 
                continue
            if k.session == "morning" and not (t.available_morning or False): 
                continue
            if k.session == "afternoon" and not (t.available_afternoon or False): 
                continue
            avail.add((t.id, k.id))
    t_avail_count = {t.id: 0 for t in teachers}
    for tid, _ in avail:
        t_avail_count[tid] += 1

    # TeachOK
    teach_ok = defaultdict(list)  # s_code -> list teacher_id
    subj_by_code = {s.code: s for s in db.query(Subject).all()}
    for t in teachers:
        for s in t.subjects:
            teach_ok[s.code].append(t.id)

    # Conservative upper bound: chia đều min(cap, avail_slots) cho các môn mà GV đó dạy
    supply = defaultdict(float)
    for t in teachers:
        t_cap_eff = min(caps[t.id], t_avail_count[t.id])
        s_list = [s.code for s in t.subjects]
        if not s_list:
            continue
        share = t_cap_eff / len(s_list)
        for sc in s_list:
            supply[sc] += share

    # deficits
    deficit = {}
    for sc, dem in demand.items():
        sup = int(supply.get(sc, 0))
        if sup < dem:
            deficit[sc] = dem - sup

    return demand, supply, deficit

def pick_candidates(db: Session, s_code: str):
    """Chọn danh sách ứng viên GV để gán thêm môn s_code (ưu tiên đã dạy cùng 'họ' môn)."""
    teachers = db.query(Teacher).all()
    # Ưu tiên GV đã dạy cùng họ môn (MATH_* / LIT_* …)
    prefix = s_code.split("_")[0] + "_"
    preferred = []
    others = []
    for t in teachers:
        codes = {s.code for s in t.subjects}
        if s_code in codes:
            continue  # đã dạy rồi
        if any(c.startswith(prefix) for c in codes):
            preferred.append(t)
        else:
            others.append(t)

    # Ưu tiên người còn rảnh 2 buổi và quota >= 16
    def score(t: Teacher):
        score = 0
        score += 2 if (t.available_morning and t.available_afternoon) else 0
        score += 1 if (t.max_weekly_lessons or 0) >= 18 else 0
        return score

    preferred.sort(key=lambda t: (-score(t), t.code))
    others.sort(key=lambda t: (-score(t), t.code))
    return preferred + others

def run():
    db: Session = SessionLocal()
    try:
        demand, supply, deficit = compute_conservative_deficits(db)

        if not deficit:
            print("✅ Không có môn nào thiếu theo conservative upper-bound.")
            return

        subs = {s.code: s for s in db.query(Subject).all()}
        added = defaultdict(int)

        # Boost quota nhẹ cho GV dạy họ môn nặng
        for t in db.query(Teacher).all():
            if any(s.code.startswith(HEAVY_PREFIXES) for s in t.subjects):
                if (t.max_weekly_lessons or 0) < HEAVY_TARGET_CAP:
                    t.max_weekly_lessons = HEAVY_TARGET_CAP

        # Gán thêm GV cho các subject thiếu
        for s_code, miss in sorted(deficit.items(), key=lambda x: -x[1]):
            subj = subs.get(s_code)
            if not subj:
                print(f"⚠️ Subject {s_code} không tồn tại, bỏ qua.")
                continue

            need = int(miss)
            print(f"➕ Bù giáo viên cho {s_code}: thiếu≈{need}")

            for t in pick_candidates(db, s_code):
                # Bỏ qua GV không rảnh buổi nào
                if not (t.available_morning or t.available_afternoon):
                    continue
                # Gán môn
                if subj not in t.subjects:
                    t.subjects.append(subj)
                    added[s_code] += 1
                    # Dừng khi đã thêm đủ số người “ước lượng”
                    # (mỗi GV thêm ~1–2 tiết thực khi giải, tùy vào ràng buộc; bổ sung biên độ)
                    if added[s_code] >= max(2, need // 2):
                        break

        db.commit()
        print("✅ Đã gán thêm giáo viên. Tóm tắt:")
        for k in sorted(added):
            print(f"  {k}: +{added[k]} GV")

    finally:
        db.close()

if __name__ == "__main__":
    run()
