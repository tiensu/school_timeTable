# app/routers/reports_routes.py
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.timetable_model import Timetable
from app.models.timetable_slot_model import TimetableSlot

router = APIRouter(prefix="/api/reports", tags=["reports"])
# ========== API UTILS ==========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== REPORTS ==========
def _ensure_models(db: Session):
    if db.query(Teacher).count() == 0:
        raise HTTPException(status_code=400, detail="Chưa có giáo viên trong hệ thống.")
    if db.query(Timetable).count() == 0:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu thời khóa biểu trong bảng timetables.")

def _query_teacher_load(
    db: Session,
    subject: Optional[str],
    class_name: Optional[str],
    day_of_week: Optional[str],
    session_filter: Optional[str],
    teacher_q: Optional[str],
) -> List[Dict]:
    _ensure_models(db)

    # JOIN tường minh
    q = db.query(Timetable, TimetableSlot, Subject) \
        .join(TimetableSlot, Timetable.slot_id == TimetableSlot.id) \
        .join(Subject, Timetable.subject_code == Subject.code)

    # filter dữ liệu TKB
    if subject:
        q = q.filter(Timetable.subject_code == subject)
    if class_name:
        q = q.filter(Timetable.class_name == class_name)
    if day_of_week:
        q = q.filter(TimetableSlot.day_of_week == day_of_week)
    if session_filter:
        q = q.filter(TimetableSlot.session == session_filter)

    # lấy toàn bộ giáo viên & filter theo teacher_q ở tầng giáo viên
    teachers_q = db.query(Teacher)
    if teacher_q:
        s = f"%{teacher_q.strip().lower()}%"
        teachers_q = teachers_q.filter(
            or_(func.lower(Teacher.code).like(s), func.lower(Teacher.name).like(s))
        )
    teachers_list = teachers_q.all()
    teachers = {t.code: t for t in teachers_list}
    allowed_codes = set(teachers.keys()) if teacher_q else None

    stats: Dict[str, Dict] = {}
    for tt, slot, sub in q.all():
        # nếu có teacher_q → chỉ gom cho GV phù hợp
        if allowed_codes is not None and tt.teacher_code not in allowed_codes:
            continue

        gv_code = tt.teacher_code
        if gv_code not in stats:
            teacher = teachers.get(gv_code) or db.query(Teacher).filter(Teacher.code == gv_code).first()
            cap = int((teacher.max_weekly_lessons if teacher else 0) or 0)
            stats[gv_code] = {
                "teacher_code": gv_code,
                "teacher_name": (teacher.name if teacher else gv_code),
                "capacity": cap,
                "total_periods": 0,
                "by_subject": {},
                "by_class": {},
                "by_day": {},
                "by_session": {},
            }
        s = stats[gv_code]
        s["total_periods"] += 1
        s["by_subject"][tt.subject_code] = s["by_subject"].get(tt.subject_code, 0) + 1
        s["by_class"][tt.class_name] = s["by_class"].get(tt.class_name, 0) + 1
        s["by_day"][slot.day_of_week] = s["by_day"].get(slot.day_of_week, 0) + 1
        s["by_session"][slot.session] = s["by_session"].get(slot.session, 0) + 1

    for s in stats.values():
        cap = s["capacity"] or 0
        total = s["total_periods"]
        s["utilization"] = round((total / cap) * 100, 1) if cap > 0 else None
        s["overload"] = max(0, total - cap) if cap > 0 else 0

    out = sorted(stats.values(), key=lambda x: (x["overload"], x["total_periods"]), reverse=True)
    return out

@router.get("/teacher-load")
def teacher_load(
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    day_of_week: Optional[str] = Query(None),
    session: Optional[str] = Query(None, description="morning/afternoon/evening"),
    teacher_q: Optional[str] = Query(None, description="Lọc theo mã hoặc tên giáo viên"),
) -> List[Dict]:
    """
    Tổng hợp số tiết / giáo viên, hỗ trợ filter theo teacher_q (mã/tên).
    """
    return _query_teacher_load(db, subject, class_name, day_of_week, session, teacher_q)

@router.get("/teacher-load/detail")
def teacher_load_detail(
    teacher_code: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Chi tiết TKB cho một giáo viên.
    """
    _ensure_models(db)

    teacher = db.query(Teacher).filter(Teacher.code == teacher_code).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Không tìm thấy giáo viên.")

    q = db.query(Timetable, TimetableSlot, Subject).join(
        TimetableSlot, Timetable.slot_id == TimetableSlot.id
    ).join(
        Subject, Timetable.subject_code == Subject.code
    ).filter(
        Timetable.teacher_code == teacher_code
    ).order_by(
        TimetableSlot.day_of_week, TimetableSlot.session, TimetableSlot.period
    )

    details = []
    for tt, slot, sub in q.all():
        details.append({
            "class_name": tt.class_name,
            "subject_code": tt.subject_code,
            "subject_name": sub.name,
            "day_of_week": slot.day_of_week,
            "session": slot.session,
            "period": slot.period,
            "slot_id": slot.id,
        })

    return {
        "teacher_code": teacher.code,
        "teacher_name": teacher.name,
        "capacity": int(teacher.max_weekly_lessons or 0),
        "total_periods": len(details),
        "details": details
    }

# ---------------- PDF Export ----------------
from sqlalchemy import func, or_
from io import BytesIO
from fastapi.responses import StreamingResponse
@router.get("/teacher_load_pdf")
@router.get("/teacher-load/pdf")
def teacher_load_pdf(
    db: Session = Depends(get_db),
    subject: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    day_of_week: Optional[str] = Query(None),
    session: Optional[str] = Query(None),
    searchValue: Optional[str] = Query(None, description="Lọc theo tên hoặc mã GV (tương đương Tìm nhanh)"),
):
    # Gọi lại logic join từ _query_teacher_load, với searchValue = teacher_q
    teacher_data = _query_teacher_load(
        db=db,
        subject=subject,
        class_name=class_name,
        day_of_week=day_of_week,
        session_filter=session,
        teacher_q=searchValue
    )

    # Tạo bảng dữ liệu
    data = [["Mã GV", "Tên GV", "Tổng số tiết", "Quota", "% sử dụng", "Overload", "Theo môn", "Theo lớp", "Theo ngày", "Theo buổi"]]

    for t in teacher_data:
        row = [
            t["teacher_code"],
            t["teacher_name"],
            t["total_periods"],
            t["capacity"],
            f'{t["utilization"]}%' if t["utilization"] is not None else "",
            t["overload"],
            "\n".join(f"{k}: {v}" for k, v in t["by_subject"].items()),
            "\n".join(f"{k}: {v}" for k, v in t["by_class"].items()),
            "\n".join(f"{k}: {v}" for k, v in t["by_day"].items()),
            "\n".join(f"{k}: {v}" for k, v in t["by_session"].items()),
        ]
        data.append(row)

    # Xuất PDF
    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from fastapi.responses import StreamingResponse

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    doc.build([table])
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=teacher_load.pdf"
    })
