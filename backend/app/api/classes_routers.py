from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger

import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.classes_model import Class
from app.schema import classes_schema

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))

@router.get("/class")
def serve_class_page():
    return FileResponse(os.path.join(BASE_DIR, "class_manager.html"))

# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== CLASSES ==========
@router.post("/classes")
def create_class(cls: classes_schema.ClassCreate, db: Session = Depends(get_db)):
    existing = db.query(Class).filter(Class.name == cls.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên lớp đã tồn tại.")
    new_class = Class(**cls.dict())
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return {"message": "Thêm lớp thành công."}


@router.post("/classes/import")
async def import_classes(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    
    imported_count = 0
    duplicated = []

    for _, row in df.iterrows():
        try:
            name = str(row[0]).strip()           # Cột A
            grade = int(row[1])                  # Cột B
            student_count = int(row[2])          # Cột C
            # logger.info(f'Processing class: {name}, Grade: {grade}, Students: {student_count}')

            # Kiểm tra lớp đã tồn tại
            existing = db.query(Class).filter(Class.name == name).first()
            if existing:
                duplicated.append(name)
                continue

            # Thêm lớp mới
            class_obj = Class(name=name, grade=grade, student_count=student_count)
            db.add(class_obj)
            imported_count += 1
        except Exception as e:
            duplicated.append(f"{row[0]} (Lỗi: {str(e)})")

    db.commit()

    return {
        "message": f"Đã import thành công {imported_count} lớp học",
        "imported_count": imported_count,
        "duplicated": duplicated
    }

@router.get("/classes")
def get_classes(skip: int = 0, limit: int = 10, search: str = ""):
    logger.info(f'Fetch class ...')
    session = SessionLocal()
    query = session.query(Class)
    if search:
        query = query.filter(Class.name.ilike(f"%{search}%"))
    total = query.count()
    classes = query.offset(skip).limit(limit).all()
    session.close()
    return {
        "data": [
            {
                **classes_schema.ClassRead.from_orm(cls).dict(),
                "index": skip + i + 1  # STT thực tế
            }
            for i, cls in enumerate(classes)
        ],
        "total": total
    }


@router.get("/classes/count")
def get_class_count(db: Session = Depends(get_db)):
    return {"count": db.query(Class).count()}

@router.put("/classes/{class_id}")
def update_class(class_id: int, class_update: classes_schema.ClassCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating class with ID: {class_id} with data: {class_update}")
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    db_class.name = class_update.name
    db_class.grade = class_update.grade
    db_class.student_count = class_update.student_count
    db.commit()
    return {"message": f"Cập nhập thông tin lớp {class_update.name} thành công!"}

# DELETE /classes/{class_id}
@router.delete("/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    logger.info(f'Deleting class {class_id}')
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Class not found")

    db.delete(db_class)
    db.commit()
    return {"message": f"Xóa lớp {db_class.name} thành công!"}
# Schema input
class ClassDeleteRequest(BaseModel):
    class_ids: list[int]

@router.post("/classes/delete-multiple")
def delete_multiple_classes(req: ClassDeleteRequest, db: Session = Depends(get_db)):
    deleted_count = db.query(Class).filter(Class.id.in_(req.class_ids)).delete(synchronize_session=False)
    db.commit()
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching classes found to delete.")
    
    return {"deleted": deleted_count, "message": f"Đã xóa {deleted_count} lớp thành công!"}