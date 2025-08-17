# app/services/auto_patch_teachers.py
# -*- coding: utf-8 -*-
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.model import SessionLocal

from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.timetable_slot_model import TimetableSlot
from app.models.classes_model import Class

HEAVY_PREFIXES = ("MATH_", "LIT_")
HEAVY_TARGET_CAP = 22

def _subject_demand(db: Session):
    demand = defaultdict(int)
    classes = db.query(Class).all()
    for c in classes:
        for s in getattr(c, "subjects", []) or []:
            w = int(s.lesson_per_week or 0)
            if w > 0:
                demand[s.code] += w
    return demand

def _effective_avail_slots(db: Session):
    teachers = db.query(Teacher).all()
    slots = db.query(TimetableSlot).all()
    unavail = {t.id: {sl.id for sl in t.unavailable_slots} for t in teachers}
    cnt = {t.id: 0 for t in teachers}
    for t in teachers:
        for k in slots:
            if k.id in unavail[t.id]:
                continue
            if k.session == "morning" and not (t.available_morning or False):
                continue
            if k.session == "afternoon" and not (t.available_afternoon or False):
                continue
            cnt[t.id] += 1
    return cnt  # teacher_id -> số slot rảnh

def _conservative_supply(db: Session):
    """Upper-bound: chia đều min(cap, avail_slots) cho các môn GV đó dạy."""
    teachers = db.query(Teacher).all()
    caps = {t.id: int(t.max_weekly_lessons or 0) for t in teachers}
    avail = _effective_avail_slots(db)

    supply = defaultdict(float)  # s_code -> float
    for t in teachers:
        cap_eff = min(caps[t.id], avail[t.id])
        s_list = [s.code for s in t.subjects]
        if not s_list:
            continue
        share = cap_eff / len(s_list)
        for sc in s_list:
            supply[sc] += share
    return supply

def compute_conservative_deficits(db: Session):
    demand = _subject_demand(db)
    supply = _conservative_supply(db)
    deficit = {}
    for sc, dem in demand.items():
        sup = int(supply.get(sc, 0))
        if sup < dem:
            deficit[sc] = dem - sup
    return demand, supply, deficit

def _pick_candidates(db: Session, s_code: str):
    teachers = db.query(Teacher).all()
    pref = s_code.split("_")[0] + "_"

    def score(t: Teacher):
        points = 0
        # còn rảnh cả 2 buổi
        points += 2 if (t.available_morning and t.available_afternoon) else 0
        # quota tốt
        points += 1 if (t.max_weekly_lessons or 0) >= 18 else 0
        # ít unavailable slots
        points += 1 if len(getattr(t, "unavailable_slots", [])) <= 4 else 0
        # đang dạy cùng họ môn
        if any(s.code.startswith(pref) for s in t.subjects):
            points += 2
        return points

    # loại GV đã dạy s_code
    pool = [t for t in teachers if s_code not in {s.code for s in t.subjects}]
    pool.sort(key=lambda t: (-score(t), t.code))
    return pool

def auto_patch_teachers(db: Session, boost_heavy=True):
    """
    Bù giáo viên theo conservative upper-bound.
    Trả về summary dict, KHÔNG trùng lặp gán môn cho GV.
    """
    added = defaultdict(int)

    # boost quota nhẹ cho họ môn nặng
    if boost_heavy:
        for t in db.query(Teacher).all():
            if any(s.code.startswith(HEAVY_PREFIXES) for s in t.subjects):
                if (t.max_weekly_lessons or 0) < HEAVY_TARGET_CAP:
                    t.max_weekly_lessons = HEAVY_TARGET_CAP

    demand, supply, deficit = compute_conservative_deficits(db)
    if not deficit:
        return {"patched": False, "added": {}, "note": "Không có môn thiếu theo conservative upper-bound."}

    subs = {s.code: s for s in db.query(Subject).all()}

    # Ưu tiên môn thiếu nhiều nhất
    for s_code, miss in sorted(deficit.items(), key=lambda x: -x[1]):
        subj = subs.get(s_code)
        if not subj:
            continue

        need = int(miss)
        for t in _pick_candidates(db, s_code):
            # bỏ qua GV không rảnh buổi nào
            if not (t.available_morning or t.available_afternoon):
                continue
            # gán môn nếu chưa có
            if subj not in t.subjects:
                t.subjects.append(subj)
                added[s_code] += 1
                # dừng ở ngưỡng bảo thủ: mỗi 2 thiếu ~ thêm 1 GV (tùy ràng buộc thực tế)
                if added[s_code] >= max(2, need // 2):
                    break

    db.commit()
    return {"patched": True, "added": dict(added)}

if __name__ == "__main__":
    db: Session = SessionLocal()
    auto_patch_teachers(db)