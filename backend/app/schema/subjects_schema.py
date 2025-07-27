from pydantic import BaseModel
from typing import Optional

# ===== CLASSES =====
class SubjectBase(BaseModel):
    name: str
    code: str
    required: bool = False  # Có bắt buộc không
    num_periods_per_week: Optional[int] = None
    subject_group: Optional[str] = None  # Nhóm môn học
    exam_required: Optional[bool] = False  # Có cần thi cuối kỳ không
    description: Optional[str] = None
    status: Optional[str] = "active"  # active, retired, inactive

class SubjectCreate(SubjectBase):
    pass

class SubjectRead(SubjectBase):
    id: int
    model_config = {
        "from_attributes": True
    }