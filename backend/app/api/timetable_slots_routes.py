# app/routers/timetable_slots_routes.py
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.model import SessionLocal
from app.models.timetable_slot_model import TimetableSlot
from app.models.timetable_model import Timetable
from app.models.teacher_unavailable_slot_model import teacher_unavailable_slot_association
from loguru import logger
from sqlalchemy import delete
import pandas as pd
import io
# from app.api.user_routes import require_admin

# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/api/timetable-slots", tags=["timetable-slots"])

# Cấu hình hợp lệ
DAY_CHOICES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SESSION_CHOICES = ["morning", "afternoon", "evening"]  # tuỳ trường có thể bỏ evening

# ----------------- Helpers -----------------
def _current_config(db: Session) -> Dict:
    # distinct days
    days = [d for (d,) in db.query(TimetableSlot.day_of_week)
                          .distinct()
                          .order_by(TimetableSlot.day_of_week).all()]
    # distinct sessions
    sessions = [s for (s,) in db.query(TimetableSlot.session)
                              .distinct()
                              .order_by(TimetableSlot.session).all()]
    # periods per session theo từng ngày (đếm distinct period)
    per_day_periods = {}
    for ses in sessions:
        by_day: Dict[str, int] = {}
        for d in days:
            cnt = db.query(func.count(func.distinct(TimetableSlot.period)))\
                    .filter(TimetableSlot.session == ses,
                            TimetableSlot.day_of_week == d).scalar() or 0
            if cnt > 0:
                by_day[d] = int(cnt)
        per_day_periods[ses] = by_day  # ví dụ: {"Monday":5,"Tuesday":5,...}

    # tổng hợp max period theo session (nếu có lệch giữa các ngày)
    periods_per_session = {
        ses: (max(by_day.values()) if by_day else 0)
        for ses, by_day in per_day_periods.items()
    }

    total_slots = db.query(func.count(TimetableSlot.id)).scalar() or 0

    return {
        "days": days,                                 # ["Monday",...]
        "sessions": sessions,                         # ["morning","afternoon",...]
        "per_day_periods": per_day_periods,           # {"morning":{"Monday":5,...}, ...}
        "periods_per_session": periods_per_session,   # {"morning":5, ...}
        "total_slots": int(total_slots),
    }

# ----------------- Schemas -----------------
class AddDayReq(BaseModel):
    day: str
    @validator("day")
    def v_day(cls, v):
        if v not in DAY_CHOICES:
            raise ValueError(f"day phải thuộc {DAY_CHOICES}")
        return v

class AddSessionReq(BaseModel):
    session: str
    periods: int = Field(..., ge=1, le=12)
    @validator("session")
    def v_ses(cls, v):
        if v not in SESSION_CHOICES:
            raise ValueError(f"session phải thuộc {SESSION_CHOICES}")
        return v

class SetPeriodsReq(BaseModel):
    session: str
    periods: int = Field(..., ge=0, le=12)  # 0 = xoá tất cả slots của buổi
    @validator("session")
    def v_ses(cls, v):
        if v not in SESSION_CHOICES:
            raise ValueError(f"session phải thuộc {SESSION_CHOICES}")
        return v

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
# ----------------- APIs cấu hình -----------------

@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    """Trả về cấu hình hiện tại: ngày, buổi, số tiết/buổi (max theo ngày), chi tiết per-day."""
    return _current_config(db)

@router.post("/config/add-day")
def config_add_day(body: AddDayReq, db: Session = Depends(get_db)):
    """Thêm một ngày mới: sinh slot cho tất cả session hiện có, theo periods_per_session hiện tại."""
    cfg = _current_config(db)
    if body.day in cfg["days"]:
        return {"created": 0, "skipped": "day_exists"}

    created = 0
    for ses in cfg["sessions"]:
        pps = cfg["periods_per_session"].get(ses, 0)
        for p in range(1, pps + 1):
            db.add(TimetableSlot(day_of_week=body.day, session=ses, period=p))
            created += 1
    db.commit()
    return {"created": created}

@router.delete("/config/day/{day}")
def config_delete_day(day: str, db: Session = Depends(get_db)):
    """Xoá toàn bộ slots thuộc ngày nếu tồn tại, xử lý liên kết."""
    
    logger.info(f"Xoá toàn bộ slots của ngày: {day}")
    if day not in DAY_CHOICES:
        raise HTTPException(status_code=400, detail="Ngày không hợp lệ.")

    # Lấy danh sách các slot thuộc ngày đó
    slots = db.query(TimetableSlot).filter(TimetableSlot.day_of_week == day).all()
    if not slots:
        raise HTTPException(status_code=404, detail="Ngày không tồn tại trong cấu hình hiện tại.")

    slot_ids = [slot.id for slot in slots]

    # Kiểm tra xem có slot nào đã được dùng trong bảng Timetable chưa
    timetable_count = db.query(Timetable).filter(Timetable.slot_id.in_(slot_ids)).count()
    if timetable_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Các tiết học của ngày này đã được sắp xếp trong thời khóa biểu. "
                   "Hãy xóa thời khóa biểu trước rồi cấu hình lại."
        )

    # Xóa liên kết teacher_unavailable_slot_association
    db.execute(
        delete(teacher_unavailable_slot_association).where(
            teacher_unavailable_slot_association.c.slot_id.in_(slot_ids)
        )
    )

    # Xoá toàn bộ slot
    deleted = db.query(TimetableSlot).filter(TimetableSlot.id.in_(slot_ids)).delete(synchronize_session=False)
    db.commit()

    return {"deleted": int(deleted)}


@router.post("/config/add-session")
def config_add_session(body: AddSessionReq, db: Session = Depends(get_db)):
    """Thêm một buổi mới: tạo slot cho tất cả ngày hiện có, với periods mặc định."""
    # logger.debug(f'Thêm một buổi mới: tạo slot cho tất cả ngày hiện có, với periods mặc định.')
    cfg = _current_config(db)
    if body.session in cfg["sessions"]:
        raise HTTPException(status_code=400, detail="Buổi đã tồn tại.")
    created = 0
    for d in cfg["days"]:
        for p in range(1, body.periods + 1):
            db.add(TimetableSlot(day_of_week=d, session=body.session, period=p))
            created += 1
    db.commit()
    return {"created": created}

@router.delete("/config/session/{session}")
def config_delete_session(session: str, db: Session = Depends(get_db)):
    """Xoá toàn bộ slots của một buổi."""
    if session not in SESSION_CHOICES:
        raise HTTPException(status_code=400, detail="Buổi không hợp lệ.")
    deleted = db.query(TimetableSlot).filter(TimetableSlot.session == session).delete()
    db.commit()
    return {"deleted": int(deleted)}

@router.put("/config/periods")
def config_set_periods(body: SetPeriodsReq, db: Session = Depends(get_db)):
    """
    Đặt số tiết cho một buổi và đồng bộ cho TẤT CẢ các ngày:
    - Nếu periods = 0: xoá toàn bộ slot của buổi đó (tương đương remove session).
    - Nếu >0: thêm các period còn thiếu, xoá các period thừa.
    """
    if body.periods == 0:
        deleted = db.query(TimetableSlot).filter(TimetableSlot.session == body.session).delete()
        db.commit()
        return {"session": body.session, "periods": 0, "deleted": int(deleted)}

    cfg = _current_config(db)
    days = cfg["days"]
    created, kept, removed = 0, 0, 0

    for d in days:
        # hiện có những period nào cho (day, session)
        existing = db.query(TimetableSlot).filter(
            TimetableSlot.day_of_week == d,
            TimetableSlot.session == body.session
        ).all()
        have = {row.period for row in existing}

        # thêm thiếu
        for p in range(1, body.periods + 1):
            if p not in have:
                db.add(TimetableSlot(day_of_week=d, session=body.session, period=p))
                created += 1
            else:
                kept += 1

        # xoá thừa
        for p in sorted(have):
            if p > body.periods:
                db.query(TimetableSlot).filter(
                    TimetableSlot.day_of_week == d,
                    TimetableSlot.session == body.session,
                    TimetableSlot.period == p
                ).delete()
                removed += 1

    db.commit()
    return {"session": body.session, "periods": body.periods, "created": created, "kept": kept, "removed": removed}
    
from fastapi import HTTPException

def remove_slot_and_refs(db: Session, slot: TimetableSlot):
    # ⚠️ Kiểm tra xem slot này có đang được dùng trong bảng timetables không
    timetable_exists = db.query(Timetable).filter(Timetable.slot_id == slot.id).first()
    if timetable_exists:
        raise HTTPException(
            status_code=400,
            detail="Các tiết học của ngày này đã được sắp xếp trong thời khóa biểu. Hãy xóa thời khóa biểu trước rồi cấu hình lại."
        )

    # Xóa trong bảng liên kết
    db.execute(
        delete(teacher_unavailable_slot_association).where(
            teacher_unavailable_slot_association.c.slot_id == slot.id
        )
    )

    # Cuối cùng mới xóa slot
    db.delete(slot)

@router.put("/config/periods/day")
def config_set_day_periods(body: SetDayPeriodsReq, db: Session = Depends(get_db)):
    """
    Đặt số tiết cho 1 (day, session) duy nhất.
    - periods=0: xoá hết slot của (day, session).
    - periods>0: đảm bảo tồn tại các period 1..N; xoá period > N nếu có.
    """
    logger.info(f"Đặt số tiết cho {body.day} {body.session} với periods={body.periods}")

    existing = db.query(TimetableSlot).filter(
        TimetableSlot.day_of_week == body.day,
        TimetableSlot.session == body.session
    ).all()

    existing_by_period = {slot.period: slot for slot in existing}

    created, kept, removed = 0, 0, 0

    if body.periods == 0:
        for slot in existing:
            remove_slot_and_refs(db, slot)
            removed += 1
        db.commit()
        return {
            "day": body.day, "session": body.session,
            "periods": 0, "created": 0, "kept": 0, "removed": removed
        }

    # Thêm thiếu từ 1 đến N
    for p in range(1, body.periods + 1):
        if p in existing_by_period:
            kept += 1
        else:
            db.add(TimetableSlot(day_of_week=body.day, session=body.session, period=p))
            created += 1

    # Xoá các period > N
    for p in sorted(existing_by_period):
        if p > body.periods:
            slot = existing_by_period[p]
            remove_slot_and_refs(db, slot)
            removed += 1

    db.commit()
    return {
        "day": body.day,
        "session": body.session,
        "periods": body.periods,
        "created": created,
        "kept": kept,
        "removed": removed
    }

@router.post("/import")
async def import_subjects(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))

    imported_count = 0
    duplicated = []
    errors = []

    for idx, row in df.iterrows():
        try:
            day_of_week=row[0] if pd.notna(row[0]) else None,
            session=row[1] if pd.notna(row[1]) else None,
            period=int(row[2]) if pd.notna(row[2]) else None

            if not day_of_week or not session:
                raise ValueError("Thiếu ngày hoặc buổi học")

            existing = db.query(TimetableSlot).filter(
                TimetableSlot.day_of_week == day_of_week,
                TimetableSlot.session == session,
                TimetableSlot.period == period
            ).first()
            if existing:
                duplicated.append(existing.name)
                continue

            slot = TimetableSlot(
                day_of_week=day_of_week,
                session=session,
                period=period
            )
            db.add(slot)
            imported_count += 1

        except Exception as e:
            errors.append(f"Dòng {idx} ({row[0]}): {str(e)}")
            logger.error(f"Error processing row {idx}: {e}")

    db.commit()
    return {
        "imported": imported_count,
        "duplicated": duplicated,
        "errors": errors
    }