# app/routers/timetables.py
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse, FileResponse
from app.models.model import SessionLocal
from app.models.classes_model import Class
from app.models.subjects_model import Subject
from app.models.teachers_model import Teacher
from app.models.timetable_model import Timetable
from app.models.timetable_slot_model import TimetableSlot
from app.api.build_timetable import gen_timetable
from loguru import logger

router = APIRouter(prefix="/api/timetables", tags=["timetables"])
DAY_CHOICES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SESSION_CHOICES = ["morning", "afternoon", "evening"]  # tuỳ trường có thể bỏ evening
# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== TIMETABLES API==========
@router.get("/classes", response_model=List[Dict])
def list_classes(db: Session = Depends(get_db)):
    logger.info("Fetching all classes")
    rows = db.query(Class).order_by(Class.name.asc()).all()
    return [
        {
            "name": c.name,
            "grade": c.grade,
            "student_count": c.student_count,
        }
        for c in rows
    ]

@router.get("/teachers", response_model=List[Dict])
def list_teachers(db: Session = Depends(get_db)):
    rows = db.query(Teacher).order_by(Teacher.code.asc()).all()
    return [
        {
            "code": t.code,
            "name": t.name,
            # có thể expose thêm nếu muốn:
            # "status": t.status,
            # "max_weekly_lessons": t.max_weekly_lessons,
        }
        for t in rows
    ]

DAY_ORDER = {"Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4, "Friday": 5}
SESSION_ORDER = {"morning": 0, "afternoon": 1}

@router.get("/view", response_model=List[Dict])
def view_timetables(
    class_name: Optional[str] = Query(None, description="Lọc theo tên lớp, ví dụ: 10A1"),
    teacher_code: Optional[str] = Query(None, description="Lọc theo mã GV, ví dụ: gv001"),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách các dòng TKB kèm thông tin slot.
    Cấu trúc mỗi item (phù hợp với frontend đã gửi trước đó):

    {
      "class_name": "...",
      "subject_code": "...",
      "teacher_code": "...",
      "subject_name": "...",   # bonus
      "teacher_name": "...",   # bonus
      "slot": { "day_of_week": "...", "session": "...", "period": 1 }
    }
    """
    q = (
        db.query(Timetable, TimetableSlot, Subject, Teacher)
        .join(TimetableSlot, Timetable.slot_id == TimetableSlot.id)
        .join(Subject, Timetable.subject_code == Subject.code)
        .join(Teacher, Timetable.teacher_code == Teacher.code)
    )

    if class_name:
        q = q.filter(Timetable.class_name == class_name)
    if teacher_code:
        q = q.filter(Timetable.teacher_code == teacher_code)

    # Sắp xếp thân thiện theo thời gian + lớp
    rows = q.all()
    rows.sort(key=lambda r: (
        r[0].class_name,
        DAY_ORDER.get(r[1].day_of_week, 99),
        SESSION_ORDER.get(r[1].session, 9),
        r[1].period,
    ))

    out = []
    for tt, sl, subj, tch in rows:
        out.append({
            "class_name": tt.class_name,
            "subject_code": tt.subject_code,
            "teacher_code": tt.teacher_code,
            "subject_name": subj.name,
            "teacher_name": tch.name,
            "slot": {
                "day_of_week": sl.day_of_week,
                "session": sl.session,
                "period": sl.period,
            },
        })
    return out

# --- Schema: đặt periods theo NGÀY & BUỔI ---
class SetDayPeriodsReq(BaseModel):
    day: str
    session: str
    periods: int = Field(..., ge=0, le=12)  # 0 = xoá tất cả period của (day, session)
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
    """
    Đặt số tiết cho 1 (day, session) duy nhất.
    - periods=0: xoá hết slot của (day, session).
    - periods>0: đảm bảo tồn tại các period 1..N; xoá period > N nếu có.
    """
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

    # Lấy các period hiện có
    existing = db.query(TimetableSlot).filter(
        TimetableSlot.day_of_week == body.day,
        TimetableSlot.session == body.session
    ).all()
    have = {row.period for row in existing}

    created, kept, removed = 0, 0, 0

    # Thêm thiếu 1..N
    for p in range(1, body.periods + 1):
        if p not in have:
            db.add(TimetableSlot(day_of_week=body.day, session=body.session, period=p))
            created += 1
        else:
            kept += 1

    # Xoá thừa > N
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
    """
    Generate a new timetable.
    """
    result = gen_timetable()
    if not result["success"]:
        # Trả về lỗi 400 kèm message
        raise HTTPException(status_code=400, detail=result)
    
    # return {"status": "success", "message": result["message"]}
    return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": result["message"]}
        )