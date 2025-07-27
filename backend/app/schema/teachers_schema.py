from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ===== TEACHERS =====
class TeacherBase(BaseModel):
    name: str = Field(..., min_length=2)
    subject: str
    phone: Optional[str]
    email: Optional[EmailStr]
    dob: Optional[str]
    address: Optional[str]
    status: Optional[str] = "active"

    # Ràng buộc thời gian & số tiết
    max_weekly_lessons: Optional[int] = 18
    available_morning: Optional[bool] = True
    available_afternoon: Optional[bool] = True
    unavailable_days: Optional[list[str]] = []

class TeacherCreate(TeacherBase):
    pass

class TeacherRead(TeacherBase):
    id: int
    model_config = {
        "from_attributes": True
    }