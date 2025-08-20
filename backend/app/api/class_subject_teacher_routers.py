from fastapi import APIRouter

import os
from app.models.model import SessionLocal

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
