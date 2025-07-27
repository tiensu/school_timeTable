from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

import os
import io
import pandas as pd
from app.models.teachers_model import SessionLocal
from app.models.teachers_model import Class, Teacher, Subject, Room, Assignment
from app.schema import teachers_schema

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