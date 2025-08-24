from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.teachers_model import Teacher
from app.models.timetable_model import Timetable
from app.models.teacher_x_slot_model import Teacher_X_Slot
from app.models.timetable_slot_model import TimetableSlot
from app.api.build_timetable import gen_timetable
from loguru import logger

router = APIRouter(prefix="/api/timetables/teachers", tags=["timetables-teacher"])
DAY_CHOICES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SESSION_CHOICES = ["morning", "afternoon", "evening"]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/classes", response_model=List[Dict])
def list_classes(db: Session = Depends(get_db)):
    logger.info("Fetching all classes")
    rows = db.query(Class).order_by(Class.name.asc()).all()
    return [{"name": c.name} for c in rows]

@router.get("/teachers", response_model=List[Dict])
def list_teachers(db: Session = Depends(get_db)):
    rows = db.query(Teacher).order_by(Teacher.code.asc()).all()
    return [{"code": t.code, "name": t.name} for t in rows]

DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5}
SESSION_ORDER = {"morning": 0, "afternoon": 1}

@router.get("/view", response_model=List[Dict])
def view_teacher_timetables(
    teacher_code: Optional[str] = Query(None, description="Lọc theo mã GV, ví dụ: gv001"),
    class_name: Optional[str] = Query(None, description="Lọc theo tên lớp, ví dụ: 10A1"),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách các dòng TKB của giáo viên, kèm thông tin slot và lớp.
    Bao gồm cả các slot từ bảng teacher_x_slots (x_slot coi như là 1 tiết dạy của giáo viên, không gắn lớp/môn).
    Cấu trúc mỗi item:
    {
      "teacher_code": "...",
      "teacher_name": "...",
      "class_name": "...",
      "subject_code": "...",
      "subject_name": "...",
      "slot": { "day_of_week": "...", "session": "...", "period": 1 },
      "from_x_slot": true/false
    }
    """
    # Lấy các tiết dạy thực tế (có lớp, môn)
    q = (
        db.query(Timetable, TimetableSlot, Subject, Teacher)
        .join(TimetableSlot, Timetable.slot_id == TimetableSlot.id)
        .join(Subject, Timetable.subject_code == Subject.code)
        .join(Teacher, Timetable.teacher_code == Teacher.code)
    )

    if teacher_code:
        q = q.filter(Timetable.teacher_code == teacher_code)
    if class_name:
        q = q.filter(Timetable.class_name == class_name)

    rows = q.all()
    rows.sort(key=lambda r: (
        r[3].code,  # teacher_code
        DAY_ORDER.get(r[1].day_of_week, 99),
        SESSION_ORDER.get(r[1].session, 9),
        r[1].period,
        r[0].class_name,
    ))

    out = []
    for tt, sl, subj, tch in rows:
        out.append({
            "teacher_code": tt.teacher_code,
            "teacher_name": tch.name,
            "class_name": tt.class_name,
            "subject_code": tt.subject_code,
            "subject_name": subj.name,
            "slot": {
                "day_of_week": sl.day_of_week,
                "session": sl.session,
                "period": sl.period,
            },
            "from_x_slot": False
        })

    # Lấy các slot từ bảng teacher_x_slots (x_slot coi như tiết dạy của giáo viên, không gắn lớp/môn)
    x_slot_query = db.query(Teacher_X_Slot, TimetableSlot, Teacher).join(
        TimetableSlot, Teacher_X_Slot.slot_id == TimetableSlot.id
    ).join(
        Teacher, Teacher_X_Slot.teacher_code == Teacher.code
    )
    if teacher_code:
        x_slot_query = x_slot_query.filter(Teacher_X_Slot.teacher_code == teacher_code)

    x_slots = x_slot_query.all()
    for x_slot, slot, teacher in x_slots:
        # Nếu slot này đã có trong out (trùng giáo viên, slot), thì bỏ qua
        exists = any(
            o["teacher_code"] == x_slot.teacher_code and
            o["slot"]["day_of_week"] == slot.day_of_week and
            o["slot"]["session"] == slot.session and
            o["slot"]["period"] == slot.period
            for o in out
        )
        # if not exists:
        out.append({
            "teacher_code": x_slot.teacher_code,
            "teacher_name": teacher.name,
            "class_name": None,
            "subject_code": None,
            "subject_name": None,
            "slot": {
                "day_of_week": slot.day_of_week,
                "session": slot.session,
                "period": slot.period,
            },
            "from_x_slot": True
        })

    # Sắp xếp lại toàn bộ kết quả
    out.sort(key=lambda r: (
        r["teacher_code"],
        DAY_ORDER.get(r["slot"]["day_of_week"], 99),
        SESSION_ORDER.get(r["slot"]["session"], 9),
        r["slot"]["period"],
        r.get("class_name") or "",
    ))
    # logger.info(f'OUT: {out}')
    return out

class SetDayPeriodsReq(BaseModel):
    day: str
    session: str
    periods: int = Field(..., ge=0, le=12)
    @validator("day")
    def v_day(cls, v):
        if v not in DAY_CHOICES:
            raise ValueError(f"day phải thuộc {DAY_CHOICES}")
        return v
    @validator("session")
    def v_ses(cls, v):
        if v not in SESSION_CHOICES:
            raise ValueError(f"session phải thuộc {SESSION_CHOICES}")
        return v

@router.put("/config/periods/day")
def config_set_day_periods(body: SetDayPeriodsReq, db: Session = Depends(get_db)):
    if body.periods == 0:
        deleted = db.query(TimetableSlot).filter(
            TimetableSlot.day_of_week == body.day,
            TimetableSlot.session == body.session
        ).delete()
        db.commit()
        return {
            "day": body.day, "session": body.session,
            "periods": 0, "created": 0, "kept": 0, "removed": int(deleted)
        }

    existing = db.query(TimetableSlot).filter(
        TimetableSlot.day_of_week == body.day,
        TimetableSlot.session == body.session
    ).all()
    have = {row.period for row in existing}

    created, kept, removed = 0, 0, 0

    for p in range(1, body.periods + 1):
        if p not in have:
            db.add(TimetableSlot(day_of_week=body.day, session=body.session, period=p))
            created += 1
        else:
            kept += 1

    for p in sorted(have):
        if p > body.periods:
            db.query(TimetableSlot).filter(
                TimetableSlot.day_of_week == body.day,
                TimetableSlot.session == body.session,
                TimetableSlot.period == p
            ).delete()
            removed += 1

    db.commit()
    return {
        "day": body.day, "session": body.session,
        "periods": body.periods,
        "created": created, "kept": kept, "removed": removed
    }

@router.post("/gen_timetable")
def generate_timetable(db: Session = Depends(get_db)):
    result = gen_timetable()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"detail": result["message"]}
    )