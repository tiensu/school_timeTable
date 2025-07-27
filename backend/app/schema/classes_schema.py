from pydantic import BaseModel
from typing import Optional

# ===== CLASSES =====
class ClassBase(BaseModel):
    name: str
    grade: int
    student_count: int

class ClassCreate(ClassBase):
    pass

class ClassRead(ClassBase):
    id: int
    model_config = {
        "from_attributes": True
    }