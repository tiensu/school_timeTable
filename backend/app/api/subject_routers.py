from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.subjects_model import Subject
from app.models.classes_model import Class
from app.models.teachers_model import Teacher
from app.models.class_subject_teacher_model import ClassSubjectTeacher
from app.schema import subjects_schema

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "../../../frontend"))


@router.get("/subject")
def serve_subject_page():
    return FileResponse(os.path.join(BASE_DIR, "subject_management.html"))

# ========== API UTILS ==========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== SUBJECTS ==========


@router.post("/subjects")
def create_subject(cls: subjects_schema.SubjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Subject).filter(Subject.name == cls.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên môn học đã tồn tại.")
    new_subject = Subject(**cls.dict())
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return {"message": "Thêm môn học thành công."}


@router.post("/subjects/import")
async def import_subjects(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))

    imported_count = 0
    duplicated = []
    errors = []

    for idx, row in df.iterrows():
        try:
            name = str(row[0]).strip() if pd.notna(row[0]) else None
            code = str(row[1]).strip() if pd.notna(row[1]) else None
            lesson_per_week = int(row[2]) if pd.notna(row[2]) else None

            if not name or not code:
                raise ValueError("Thiếu tên hoặc mã môn học")

            existing = db.query(Subject).filter(Subject.code == code).first()
            if existing:
                duplicated.append(name)
                continue

            subject_obj = Subject(
                name=name,
                code=code,
                lesson_per_week=lesson_per_week,
            )
            db.add(subject_obj)
            imported_count += 1

        except Exception as e:
            errors.append(f"Dòng {idx+1} ({row[0]}): {str(e)}")
            logger.error(f"Error processing row {idx+1}: {e}")

    db.commit()
    return {
        "imported": imported_count,
        "duplicated": duplicated,
        "errors": errors
    }


@router.get("/subjects/names")
def get_subject_name():
    logger.info(f'Fetch subjects name ...')
    session = SessionLocal()
    try:
        subjects = session.query(Subject.name).all()
        subject_names = [s[0] for s in subjects]
        # logger.info(f'Subjects fetched: {subject_names}')
        return {"subject_names": subject_names}
    except Exception as e:
        logger.error(f"Error fetching subjects: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        session.close()


@router.get("/subjects")
def get_subjects(skip: int = 0, limit: int = 10, search: str = ""):
    logger.info(f'Fetch subjects ...')
    session = SessionLocal()
    query = session.query(Subject)
    if search:
        query = query.filter(Subject.name.ilike(f"%{search}%"))
    total = query.count()
    subjects = query.offset(skip).limit(limit).all()
    result = []
    for i, sub in enumerate(subjects):
        # Lấy danh sách giáo viên dạy môn này (theo từng lớp)
        subject_teachers = session.query(ClassSubjectTeacher).filter(
            ClassSubjectTeacher.subject_code == sub.code
        ).all()
        teachers_name = []
        for st in subject_teachers:
            # subjects = session.query(Subject).filter(Subject.code == st.subject_code).first()
            teachers = session.query(Teacher).filter(Teacher.code == st.teacher_code).first()
            teachers_name.append(teachers.name)
        teachers_name = list(set(teachers_name))  # loại bỏ trùng lặp
        result.append({
            **subjects_schema.SubjectRead.from_orm(sub).dict(),
            "index": skip + i + 1,
            "teachers_name": teachers_name  # danh sách mã giáo viên dạy môn này
        })
    session.close()
    return {
        "data": result,
        "total": total
    }


@router.get("/subjects/count")
def get_subject_count(db: Session = Depends(get_db)):
    return {"count": db.query(Subject).count()}


@router.put("/subjects/{subject_id}")
def update_subject(subject_id: int, subject_update: subjects_schema.SubjectCreate, db: Session = Depends(get_db)):
    logger.info(
        f"Updating subject with ID: {subject_id} with data: {subject_update}")
    db_subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not db_subject:
        logger.error(f"Subject with ID {subject_id} not found.")
        raise HTTPException(status_code=404, detail="Subject not found")

    db_subject.name = subject_update.name
    db_subject.code = subject_update.code
    db_subject.required = subject_update.required
    db_subject.num_periods_per_week = subject_update.num_periods_per_week
    db_subject.subject_group = subject_update.subject_group
    db_subject.exam_required = subject_update.exam_required
    db_subject.description = subject_update.description
    db_subject.status = subject_update.status
    db.commit()
    return {"message": f"Cập nhập thông tin môn học {subject_update.name} thành công!"}

# DELETE /subjects/{subject_id}


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    logger.info(f'Deleting subject {subject_id}')
    db_subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    db.delete(db_subject)
    db.commit()
    return {"message": f"Xóa môn học {db_subject.name} thành công!"}
# Schema input


class SubjectDeleteRequest(BaseModel):
    subject_ids: list[int]


@router.post("/subjects/delete-multiple")
def delete_multiple_subjects(req: SubjectDeleteRequest, db: Session = Depends(get_db)):
    deleted_count = db.query(Subject).filter(Subject.id.in_(
        req.subject_ids)).delete(synchronize_session=False)
    db.commit()

    if deleted_count == 0:
        raise HTTPException(
            status_code=404, detail="No matching subjects found to delete.")

    return {"deleted": deleted_count, "message": f"Đã xóa {deleted_count} môn học thành công!"}
