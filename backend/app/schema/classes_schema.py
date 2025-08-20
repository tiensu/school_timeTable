from pydantic import BaseModel, Field
from typing import List
from typing import Optional

# ===== CLASSES =====
class ClassBase(BaseModel):
    name: str
    specialized_class: str

class ClassCreate(BaseModel):
    name: str = Field(..., examples=["10A1"])
    grade: int = Field(..., ge=1)
    student_count: int = Field(..., ge=1)
    subjects: Optional[List[str]] = Field(
        default=None,
        description="Danh sách *tên môn* (VD: ['Toán','Vật Lý','Tiếng Anh']). Để None nếu chưa gán."
    )

class ClassRead(ClassBase):
    id: int
    model_config = {
        "from_attributes": True
    }