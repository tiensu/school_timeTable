# app/api/teacher_subject_routers.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.teacher_subject_model import TeacherSubject
from app.schema.teacher_subject_schema import TeacherSubjectCreate, TeacherSubjectRead

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/teacher-subjects", response_model=TeacherSubjectRead)
def create_teacher_subject(item: TeacherSubjectCreate, db: Session = Depends(get_db)):
    existing = db.query(TeacherSubject).filter_by(
        teacher_id=item.teacher_id,
        subject_id=item.subject_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Teacher already assigned to this subject.")
    ts = TeacherSubject(**item.dict())
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts

@router.delete("/teacher-subjects")
def delete_teacher_subject(item: TeacherSubjectCreate, db: Session = Depends(get_db)):
    ts = db.query(TeacherSubject).filter_by(
        teacher_id=item.teacher_id,
        subject_id=item.subject_id
    ).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    db.delete(ts)
    db.commit()
    return {"message": "Teacher-subject link deleted."}

@router.get("/teacher-subjects", response_model=List[TeacherSubjectRead])
def get_all_teacher_subjects(db: Session = Depends(get_db)):
    return db.query(TeacherSubject).all()
