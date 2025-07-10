from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
import pandas as pd
from app.models.database import SessionLocal
from app.models.database import Class, Teacher, Subject, Room, Assignment
from app.models import schemas
from pydantic import BaseModel
import os
import io
from loguru import logger

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))

@router.get("/dashboard")
def serve_class_page():
    return FileResponse(os.path.join(BASE_DIR, "dashboard.html"))

@router.get("/class")
def serve_class_page():
    return FileResponse(os.path.join(BASE_DIR, "class_manager.html"))

@router.get("/teacher")
def serve_teacher_page():
    return FileResponse(os.path.join(BASE_DIR, "teacher_manager.html"))

@router.get("/subject")
def serve_subject_page():
    return FileResponse(os.path.join(BASE_DIR, "subject_manager.html"))

@router.get("/room")
def serve_room_page():
    return FileResponse(os.path.join(BASE_DIR, "room_manager.html"))

@router.get("/assignment")
def serve_room_page():
    return FileResponse(os.path.join(BASE_DIR, "assignment_manager.html"))

# ========== API UTILS ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== CLASSES ==========
@router.post("/classes")
def create_class(cls: schemas.ClassCreate, db: Session = Depends(get_db)):
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
                **schemas.ClassRead.from_orm(cls).dict(),
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
def update_class(class_id: int, class_update: schemas.ClassCreate, db: Session = Depends(get_db)):
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

# ========== TEACHERS ==========
@router.post("/teachers")
def create_teacher(item: schemas.TeacherCreate, db: Session = Depends(get_db)):
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
async def import_classes(file: UploadFile = File(...), db: Session = Depends(get_db)):
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

            # Kiểm tra gv đã tồn tại
            existing = db.query(Teacher).filter(Teacher.name == name).first()
            if existing:
                duplicated.append(name)
                continue

            # Thêm lớp mới
            teacher_obj = Teacher(name=name, subject=subject, phone=phone, email=email, dob=dob, address=address)
            db.add(teacher_obj)
            imported_count += 1
        except Exception as e:
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
    logger.info(f'teachers: {teachers}')
    return {
        "data": [
            {
                **schemas.TeacherRead.from_orm(cls).dict(),
                "index": skip + i + 1  # STT thực tế
            }
            for i, cls in enumerate(teachers)
        ],
        "total": total
    }

# ========== SUBJECTS ==========
@router.post("/subjects", response_model=schemas.SubjectRead)
def create_subject(item: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_item = Subject(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/subjects", response_model=list[schemas.SubjectRead])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).all()

# ========== ROOMS ==========
@router.post("/rooms", response_model=schemas.RoomRead)
def create_room(item: schemas.RoomCreate, db: Session = Depends(get_db)):
    db_item = Room(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/rooms", response_model=list[schemas.RoomRead])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()

# ========== ASSIGNMENTS ==========
@router.post("/assignments", response_model=schemas.AssignmentRead)
def create_assignment(item: schemas.AssignmentCreate, db: Session = Depends(get_db)):
    db_item = Assignment(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/assignments", response_model=list[schemas.AssignmentRead])
def list_assignments(db: Session = Depends(get_db)):
    return db.query(Assignment).all()
