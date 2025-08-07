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
