from email.mime import text
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
from app.models.subjects_model import Subject
from app.schema import subjects_schema
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
        unavailable_days=item.unavailable_days,
        subjects=subjects,
    )
    
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return {"message": "Thêm giáo viên thành công."}

@router.post("/teachers/import")
async def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    
    imported_count = 0
    duplicated_lst = []
    error_lst = []

    for index, row in df.iterrows():
        try:
            code = str(row[0]).strip()           # Cột A
            name = str(row[1]).strip()           # Cột B
            subject_names = [s.strip() for s in str(row[2]).strip().split(",")]  # Cột C

            # Kiểm tra môn học có tồn tại
            subject_objs = []
            subject_missing = []
            for sbn in subject_names:
                subject = db.query(Subject).filter(Subject.name == sbn).first()
                if not subject:
                    subject_missing.append(sbn)
                else:
                    subject_objs.append(subject)

            if subject_missing:
                error_lst.append(f"{name} (Môn học không tồn tại: {', '.join(subject_missing)})")
                continue

            # Các cột còn lại
            status = str(row[3]).strip() if len(row) > 3 and pd.notna(row[3]) else "active"
            max_weekly_lessons = int(row[4]) if len(row) > 4 and pd.notna(row[4]) else 18
            available_morning = True if len(row) > 5 and str(row[5]).strip() == "Có" else False
            available_afternoon = True if len(row) > 6 and str(row[6]).strip() == "Có" else False
            text = str(row[7]).strip() if len(row) > 7 and pd.notna(row[7]) else ""
            unavailable_days = [d.strip() for d in text.split(",")] if text else []

            # Kiểm tra giáo viên đã tồn tại
            existing = db.query(Teacher).filter(Teacher.code == code).first()
            if existing:
                duplicated_lst.append(f"Giáo viên {name} đã tồn tại với mã {code}")
                continue

            # Tạo giáo viên mới
            teacher_obj = Teacher(
                name=name, 
                code=code, 
                subjects=subject_objs,
                status=status,
                max_weekly_lessons=max_weekly_lessons,
                available_morning=available_morning,
                available_afternoon=available_afternoon,
                unavailable_days=unavailable_days
            )

            db.add(teacher_obj)
            imported_count += 1

        except Exception as e:
            logger.error(f"Lỗi khi import giáo viên tại dòng {index+2} ({row[0]}): {str(e)}")
            error_lst.append(f"Dòng {index+2} ({row[0]}) - Lỗi: {str(e)}")

    db.commit()

    return {
        "message": f"Đã import thành công {imported_count} giáo viên",
        "imported_count": imported_count,
        "duplicated": duplicated_lst,
        "errors": error_lst
    }


@router.get("/teachers")
def get_teachers(skip: int = 0, limit: int = 10, search: str = ""):
    session = SessionLocal()
    try:
        query = session.query(Teacher)
        if search:
            query = query.filter(Teacher.name.ilike(f"%{search}%"))

        total = query.count()
        teachers = query.offset(skip).limit(limit).all()

        result = []
        for i, teacher in enumerate(teachers):
            subject_names = [sub.name for sub in teacher.subjects]
            teacher_data = teachers_schema.TeacherOut(
                id=teacher.id,
                name=teacher.name,
                code=teacher.code,
                subjects=subject_names,
                status=teacher.status,
                max_weekly_lessons=teacher.max_weekly_lessons,
                available_morning=teacher.available_morning,
                available_afternoon=teacher.available_afternoon,
                unavailable_days=teacher.unavailable_days,
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
    db_teacher.unavailable_days = teacher_update.unavailable_days

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