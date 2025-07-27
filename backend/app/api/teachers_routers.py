from email.mime import text
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

import os
import io
import pandas as pd
from app.models.model import SessionLocal
from app.models.teachers_model import Teacher
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
    existing = db.query(Teacher).filter(Teacher.name == item.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Giáo viên đã tồn tại.")
    new_teacher = Teacher(**item.dict())
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return {"message": "Thêm giáo viên thành công."}

@router.post("/teachers/import")
async def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents))
    
    imported_count = 0
    duplicated = []

    for _, row in df.iterrows():
        try:
            name = str(row[0]).strip()           # Cột A
            subject = str(row[1]).strip()                    # Cột B
            phone = str(row[2]).strip()            # Cột C
            email = str(row[3]).strip()    
            dob = str(row[4]).strip()    
            address = str(row[5]).strip()
            status = str(row[6]).strip() if len(row) > 6 else "Đang làm việc"  # Cột G, mặc định là "active"
            max_weekly_lessons = row[7] if len(row) > 7 else 18  # Cột H, mặc định là 18
            available_morning = True if row[8] == "Có" else False  # Cột I, mặc định là True
            available_afternoon = True if row[9] == "Có" else False  # Cột J, mặc định là True
            text = row[10] if len(row) > 10 and pd.notna(row[10]) else "" 
            unavailable_days = [d.strip() for d in text.split(",")] if text else [] # Cột K, mặc định là []

            # Kiểm tra giáo viên đã tồn tại
            existing = db.query(Teacher).filter(Teacher.name == name).first()
            if existing:
                duplicated.append(name)
                continue

            # Thêm giáo viên mới
            teacher_obj = Teacher(name=name, 
                                  subject=subject, 
                                  phone=phone, 
                                  email=email, 
                                  dob=dob, 
                                  address=address, 
                                  status=status,
                                  max_weekly_lessons=max_weekly_lessons,
                                  available_morning=available_morning,
                                  available_afternoon=available_afternoon,
                                  unavailable_days=unavailable_days)
            db.add(teacher_obj)
            imported_count += 1
        except Exception as e:
            logger.error(f"Lỗi khi import giáo viên {row[0]}: {str(e)}")
            duplicated.append(f"{row[0]} (Lỗi: {str(e)})")

    db.commit()

    return {
        "message": f"Đã import thành công {imported_count} lớp học",
        "imported_count": imported_count,
        "duplicated": duplicated
    }

@router.get("/teachers")
def get_teachers(skip: int = 0, limit: int = 10, search: str = ""):
    session = SessionLocal()
    query = session.query(Teacher)
    if search:
        query = query.filter(Teacher.name.ilike(f"%{search}%"))
    total = query.count()
    teachers = query.offset(skip).limit(limit).all()
    session.close()
    # logger.info(f'teachers: {teachers}')
    return {
        "data": [
            {
                **teachers_schema.TeacherRead.from_orm(cls).dict(),
                "index": skip + i + 1  # STT thực tế
            }
            for i, cls in enumerate(teachers)
        ],
        "total": total
    }

@router.get("/teachers/count")
def get_teachers_count(db: Session = Depends(get_db)):
    return {"count": db.query(Teacher).count()}

@router.put("/teachers/{teacher_id}")
def update_teachers(teacher_id: int, teacher_update: teachers_schema.TeacherCreate, db: Session = Depends(get_db)):
    logger.info(f"Updating teacher with ID: {teacher_id} with data: {teacher_update}")
    db_teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not db_teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    db_teacher.name = teacher_update.name
    db_teacher.subject = teacher_update.subject
    db_teacher.phone = teacher_update.phone
    db_teacher.email = teacher_update.email
    db_teacher.dob = teacher_update.dob
    db_teacher.address = teacher_update.address
    db.commit()
    return {"message": f"Cập nhập thông tin giáo viên {teacher_update.name} thành công!"}

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