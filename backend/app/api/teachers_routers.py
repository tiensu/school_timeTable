from email.mime import text
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import and_
import re

import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.class_subject_teacher_model import ClassSubjectTeacher
from app.models.timetable_slot_model import TimetableSlot
from app.schema import teachers_schema

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))

# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== TEACHERS ==========
@router.post("/teachers")
def create_teacher(item: teachers_schema.TeacherCreate, db: Session = Depends(get_db)):
    logger.info(f'Thêm mới giáo viên: {item}')
    existing = db.query(Teacher).filter(Teacher.code == item.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Giáo viên đã tồn tại.")
    
    subjects = db.query(Subject).filter(Subject.name.in_(item.subject)).all()
    new_teacher = Teacher(
        code=item.code,
        name=item.name,
        status=item.status,
        max_weekly_lessons=item.max_weekly_lessons,
        available_morning=item.available_morning,
        available_afternoon=item.available_afternoon,
        unavailable_slots=item.unavailable_slots,
        subjects=subjects,
    )
    
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return {"message": "Thêm giáo viên thành công."}

PAIR_RE = re.compile(r"\s*([^-,\s]+)-([^-,\s]+)\s*")
def parse_pairs(raw: str | List[str]) -> List[Tuple[str, str]]:
    """Parse 'LS10-10A11,HO12-10A10' -> [('LS10','10A11'),('HO12','10A10')]"""
    if not raw:
        return []
    if isinstance(raw, list):
        tokens = []
        for item in raw:
            tokens += [t.strip() for t in re.split(r"[,\n;]+", str(item)) if t.strip()]
    else:
        tokens = [t.strip() for t in re.split(r"[,\n;]+", str(raw)) if t.strip()]
    pairs = []
    for tok in tokens:
        m = PAIR_RE.fullmatch(tok)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs

def get_slot_by_label(label: str, db: Session = Depends(get_db)):
    try:
        d, sess, per = label.split("-")
        return db.query(TimetableSlot).filter_by(
            day_of_week=d, session=sess, period=int(per)
        ).first()
    except:
        return None

@router.post("/teachers/import")
async def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Đọc Excel
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))

    # Prefetch
    subj_map = {s.code: s for s in db.query(Subject).all()}
    class_map = {c.name: c for c in db.query(Class).all()}

    imported_count = 0
    created_cst = 0
    duplicated_lst: List[str] = []
    error_lst: List[str] = []

    for index, row in df.iterrows():
        try:
            code = str(row[0]).strip() if pd.notna(row[0]) else ""
            name = str(row[1]).strip() if pd.notna(row[1]) else ""
            if not code or not name:
                logger.warning(f"Dòng {index+1} không có mã hoặc tên giáo viên.")
                raise ValueError("Thiếu mã hoặc tên giáo viên")

            max_weekly_lessons = int(row[2]) if pd.notna(row[2]) else 17
            # logger.info(f"Max weekly lessons for {name} (code={code}): {max_weekly_lessons}")
            max_weekly_x = int(row[3]) if pd.notna(row[3]) else None
            # logger.info(f"Max weekly x for {name}: {max_weekly_x}")
            slot_labels = str(row[4]).split(",") if pd.notna(row[4]) else []
            # logger.info(f"Slot labels for {name} (code={code}): {slot_labels}")
            assignments_raw = str(row[5]).strip() if pd.notna(row[5]) else ""
            # logger.info(f"Assignments for {name} (code={code}): {assignments_raw}")
            class_advisor = str(row[6]).strip() if pd.notna(row[6]) else ""
            # logger.info(f"Class advisor for {name} (code={code}): {class_advisor}")

            # Trùng code -> skip
            existing = db.query(Teacher).filter(Teacher.code == code).first()
            if existing:
                duplicated_lst.append(f"Dòng {index+1}: Giáo viên {name} đã tồn tại (code={code})")
                logger.warning(f"Teacher {name} (code={code}) already exists, skipping.")
                continue
            
            # Gán unavailable_slots
            unavailable_slots = []  
            for label in slot_labels:
                slot = get_slot_by_label(label.strip(), db)
                # logger.debug(f'UNAVAILABLE SLOT: {slot}')
                if slot:
                    unavailable_slots.append(slot)
                    # logger.debug(f'UNAVAILABLE SLOT: {slot}')

            # Tạo teacher
            teacher = Teacher(
                name=name,
                code=code,
                max_weekly_lessons=max_weekly_lessons,
                max_weekly_x=max_weekly_x,
                class_advisor=class_advisor,
                unavailable_slots=unavailable_slots
            )
            db.add(teacher)
            db.flush()  # cần teacher.id

            # Parse assignments 'môn-lớp' và ghi ClassSubjectTeacher
            # logger.info(f"Processing assignments for {name} (code={code}): {assignments_raw}")
            pairs = parse_pairs(assignments_raw)
            # logger.info(f"Parsed pairs: {pairs}")

            unknown_subjects, unknown_classes = [], []
            for subj_code, class_code in pairs:
                if subj_code not in subj_map:
                    unknown_subjects.append(subj_code)
                if class_code not in class_map:
                    unknown_classes.append(class_code)

            for subj_code, class_code in pairs:
                subj = subj_map.get(subj_code)
                clazz = class_map.get(class_code)
                if not subj:
                    logger.warning(f"Không tìm thấy môn {subj_code} tại dòng: {index+1} - {code} - {name}")
                    continue
                if not clazz:
                    logger.warning(f"Không tìm thấy lớp {class_code} tại dòng: {index+1} - {code} - {name}")
                    continue
                existed = db.query(ClassSubjectTeacher).filter(
                    and_(
                        ClassSubjectTeacher.teacher_code == teacher.code,
                        ClassSubjectTeacher.subject_code == subj.code,
                        ClassSubjectTeacher.class_name == clazz.name,
                    )
                ).first()
                if existed:
                    logger.warning(f"ClassSubjectTeacher already exists for {teacher.name} - {subj_code} - {class_code}")
                    continue
                db.add(ClassSubjectTeacher(
                    teacher_code=teacher.code,
                    subject_code=subj.code,
                    class_name=clazz.name,
                ))
                created_cst += 1

                # (tuỳ chọn) đồng bộ quan hệ phụ để query nhanh
                # if subj not in teacher.subjects:
                #     teacher.subjects.append(subj)
                # if clazz not in teacher.classes:
                #     teacher.classes.append(clazz)

            imported_count += 1

            # Cảnh báo mềm theo dòng
            warn = []
            if unknown_subjects:
                warn.append(f"Môn không tồn tại: {', '.join(sorted(set(unknown_subjects)))}")
                # logger.warning(f"Môn không tồn tại: {', '.join(sorted(set(unknown_subjects)))}")
            if unknown_classes:
                warn.append(f"Lớp không tồn tại: {', '.join(sorted(set(unknown_classes)))}")
                # logger.warning(f"Lớp không tồn tại: {', '.join(sorted(set(unknown_classes)))}")
            if warn:
                error_lst.append(f"Dòng {index+1} (code={code}): " + " | ".join(warn))

        except Exception as e:
            logger.error(f"Lỗi import tại dòng {index+1}")
            error_lst.append(f"Dòng {index+1} ({code if 'code' in locals() else 'N/A'}) - Lỗi: {e}")

    db.commit()
    return {
        "message": f"Đã import {imported_count} giáo viên, tạo {created_cst} dòng class_subject_teacher",
        "imported_count": imported_count,
        "created_class_subject_teacher": created_cst,
        "duplicated": duplicated_lst,
        "errors": error_lst,
    }

@router.get("/teachers")
def get_teachers(skip: int = 0, limit: int = 10, search: str = ""):
    session = SessionLocal()
    try:
        # query = session.query(Teacher)
        query = session.query(Teacher).options(selectinload(Teacher.unavailable_slots))
        if search:
            query = query.filter(Teacher.name.ilike(f"%{search}%"))

        total = query.count()
        teachers = query.offset(skip).limit(limit).all()
        # logger.info(f'teachers: {teachers}, total: {total}')

        result = []
        for i, teacher in enumerate(teachers):
            # Lấy danh sách môn-lớp mà giáo viên này giảng dạy
            cst_list = session.query(ClassSubjectTeacher).filter(
                ClassSubjectTeacher.teacher_code == teacher.code
            ).all()
            subjects_with_classes = [
                f"{cst.subject_code}-{cst.class_name}" for cst in cst_list
            ]
            teacher_data = teachers_schema.TeacherOut(
                id=teacher.id,
                name=teacher.name,
                code=teacher.code,
                class_advisor=teacher.class_advisor,
                subj_class=subjects_with_classes,
                max_weekly_lessons=teacher.max_weekly_lessons,
                max_weekly_x=teacher.max_weekly_x,
                unavailable_slots=[
                    f"{slot.day_of_week}-{slot.session}-{slot.period}"
                    for slot in teacher.unavailable_slots
                ],
                index=skip + i + 1
            )
            result.append(teacher_data.dict())

        return {
            "data": result,
            "total": total
        }
    finally:
        session.close()

@router.get("/teachers/count")
def get_teachers_count(db: Session = Depends(get_db)):
    return {"count": db.query(Teacher).count()}

@router.put("/teachers/{teacher_code}")
def update_teachers(teacher_code: str, teacher_update: teachers_schema.TeacherUpdate, db: Session = Depends(get_db)):
    logger.info(f"Updating teacher with code: {teacher_code} with data: {teacher_update}")
    
    db_teacher = db.query(Teacher).filter(Teacher.code == teacher_code).first()
    if not db_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # ✅ Tra danh sách môn học theo tên
    subject_objs = []
    missing_subjects = []
    for subject_name in teacher_update.subjects:
        subject = db.query(Subject).filter(Subject.name == subject_name).first()
        if not subject:
            missing_subjects.append(subject_name)
        else:
            subject_objs.append(subject)

    if missing_subjects:
        raise HTTPException(status_code=404, detail=f"Các môn học không tồn tại: {', '.join(missing_subjects)}")

    # ✅ Cập nhật thông tin giáo viên
    db_teacher.code = teacher_update.code
    db_teacher.name = teacher_update.name
    db_teacher.subjects = subject_objs  # ⚠️ phải là List[Subject]
    db_teacher.status = teacher_update.status
    db_teacher.max_weekly_lessons = teacher_update.max_weekly_lessons
    db_teacher.available_morning = teacher_update.available_morning
    db_teacher.available_afternoon = teacher_update.available_afternoon
    db_teacher.unavailable_slots = teacher_update.unavailable_slots

    db.commit()
    return {"message": f"Cập nhật thông tin giáo viên {teacher_update.name} thành công!"}


# DELETE /teachers/{teacher_id}
@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    logger.info(f'Deleting teacher {teacher_id}')
    db_teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not db_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    db.delete(db_teacher)
    db.commit()
    return {"message": f"Xóa giáo viên {db_teacher.name} thành công!"}

class TeacherDeleteRequest(BaseModel):
    teacher_ids: list[int]

@router.post("/teachers/delete-multiple")
def delete_multiple_teachers(req: TeacherDeleteRequest, db: Session = Depends(get_db)):
    deleted_count = db.query(Teacher).filter(Teacher.id.in_(req.teacher_ids)).delete(synchronize_session=False)
    db.commit()
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching teacher found to delete.")
    
    return {"deleted": deleted_count, "message": f"Đã xóa {deleted_count} giáo viên thành công!"}