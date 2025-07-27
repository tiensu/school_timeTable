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
from app.schema import subjects_schema

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))

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

    for _, row in df.iterrows():
        try:
            name = str(row[0]).strip()           # Cột A
            code = str(row[1]).strip()           # Cột B
            number_of_periods_per_week = int(row[2])           # Cột C
            subject_group = row[3]          # Cột D
            required = True if row[4] == "Có" else False
            exam_required = True if row[5] == "Có" else False  # Cột F
            description = str(row[6]).strip() if len(row) > 6 else None  # Cột G
            status = str(row[7]).strip() if len(row) > 7 else "Đang dạy"  # Cột H, mặc định là "active"
            logger.info(f"Importing subject: {name}, Code: {code}, Required: {required}, Periods/Week: {number_of_periods_per_week}, Group: {subject_group}, Exam Required: {exam_required}, Description: {description}, Status: {status}")
            # Kiểm tra môn học đã tồn tại
            existing = db.query(Subject).filter(Subject.code == code).first()
            if existing:
                duplicated.append(name)
                continue

            # Thêm môn học mới
            subject_obj = Subject(name=name, code=code, required=required, num_periods_per_week=number_of_periods_per_week, subject_group=subject_group, exam_required=exam_required, description=description, status=status)
            db.add(subject_obj)
            imported_count += 1
        except Exception as e:
            logger.error(f"Error importing row {row[0]}: {e}")
            duplicated.append(f"{row[0]} (Lỗi: {str(e)})")

    db.commit()

    return {
        "message": f"Đã import thành công {imported_count} môn học",
        "imported_count": imported_count,
        "duplicated": duplicated
    }

@router.get("/subjects")
def get_subjects(skip: int = 0, limit: int = 10, search: str = ""):
    logger.info(f'Fetch subjects ...')
    session = SessionLocal()
    query = session.query(Subject)
    if search:
        query = query.filter(Subject.name.ilike(f"%{search}%"))
    total = query.count()
    subjects = query.offset(skip).limit(limit).all()
    session.close()
    return {
        "data": [
            {
                **subjects_schema.SubjectRead.from_orm(sub).dict(),
                "index": skip + i + 1  # STT thực tế
            }
            for i, sub in enumerate(subjects)
        ],
        "total": total
    }


@router.get("/subjects/count")
def get_subject_count(db: Session = Depends(get_db)):
    return {"count": db.query(Subject).count()}

@router.put("/subjects/{subject_id}")
def update_subject(subject_id: int, subject_update: subjects_schema.SubjectCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating subject with ID: {subject_id} with data: {subject_update}")
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
    deleted_count = db.query(Subject).filter(Subject.id.in_(req.subject_ids)).delete(synchronize_session=False)
    db.commit()
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching subjects found to delete.")

    return {"deleted": deleted_count, "message": f"Đã xóa {deleted_count} môn học thành công!"}