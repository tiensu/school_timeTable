from pydantic import BaseModel, Field
from typing import List
from typing import Optional

# ===== TEACHERS =====
class TeacherBase(BaseModel):
    name: str = Field(..., min_length=2)
    code: str = Field(..., min_length=2, max_length=10, description="Unique code for the teacher")
    subjects: List[str]  # List of subject names this teacher teaches
    status: Optional[str] = "active"

    # Ràng buộc thời gian & số tiết
    max_weekly_lessons: Optional[int] = 18
    available_morning: Optional[bool] = True
    available_afternoon: Optional[bool] = True
    unavailable_slots: Optional[List[int]] = [] 

class TeacherCreate(BaseModel):
    name: str = Field(..., min_length=2)
    code: str = Field(..., min_length=2, max_length=10, description="Unique code for the teacher")
    subjects: List[str]  # List of subject names this teacher teaches
    status: Optional[str] = "active"

    # Ràng buộc thời gian & số tiết
    max_weekly_lessons: Optional[int] = 18
    available_morning: Optional[bool] = True
    available_afternoon: Optional[bool] = True
    unavailable_slots: Optional[List[int]] = []

class TeacherUpdate(BaseModel):
    name: str = Field(..., min_length=2)
    code: str = Field(..., min_length=2, max_length=10, description="Unique code for the teacher")
    subjects: List[str]  # List of subject names this teacher teaches
    index: Optional[int] = 0
    status: Optional[str] = "active"

    # Ràng buộc thời gian & số tiết
    max_weekly_lessons: Optional[int] = 18
    available_morning: Optional[bool] = True
    available_afternoon: Optional[bool] = True
    unavailable_slots: Optional[List[int]] = []

class TeacherRead(TeacherBase):
    id: int
    model_config = {
        "from_attributes": True
    }

class TeacherOut(BaseModel):
    id: int
    name: str
    code: str
    subjects: List[str]  # tên các môn học
    status: Optional[str] = "active"
    max_weekly_lessons: Optional[int] = 18
    available_morning: Optional[bool] = True
    available_afternoon: Optional[bool] = True
    unavailable_slots: Optional[List[str]] = []
    index: Optional[int] = None