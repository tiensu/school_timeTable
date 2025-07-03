from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from app.models.database import SessionLocal
from app.models.database import Class, Teacher, Subject, Room, Assignment
from app.models import schemas
from pydantic import BaseModel
import os

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
@router.post("/classes", response_model=schemas.ClassRead)
def create_class(item: schemas.ClassCreate, db: Session = Depends(get_db)):
    db_item = Class(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/classes", response_model=list[schemas.ClassRead])
def list_classes(db: Session = Depends(get_db)):
    return db.query(Class).all()

# DELETE /classes/{class_id}
@router.delete("/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    db.delete(cls)
    db.commit()
    return {"message": f"Class with id {class_id} deleted successfully"}
# Schema input
class ClassDeleteRequest(BaseModel):
    class_ids: list[int]

@router.post("/classes/delete-multiple")
def delete_multiple_classes(req: ClassDeleteRequest, db: Session = Depends(get_db)):
    deleted_count = db.query(Class).filter(Class.id.in_(req.class_ids)).delete(synchronize_session=False)
    db.commit()
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No matching classes found to delete.")
    
    return {"deleted": deleted_count, "message": f"{deleted_count} classes deleted successfully."}

# ========== TEACHERS ==========
@router.post("/teachers", response_model=schemas.TeacherRead)
def create_teacher(item: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_item = Teacher(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/teachers", response_model=list[schemas.TeacherRead])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).all()

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
