from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from app.models.database import SessionLocal
from app.models import Class, Teacher, Subject, Room, Assignment
from app.models import schemas
import os

router = APIRouter()

# ========== HTML ROUTES ==========
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))

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
