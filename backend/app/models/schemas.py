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

# ===== TEACHERS =====
class TeacherBase(BaseModel):
    name: str
    subject: str
    phone: str
    email: str
    dob: str
    address: str

class TeacherCreate(TeacherBase):
    pass

class TeacherRead(TeacherBase):
    id: int
    model_config = {
        "from_attributes": True
    }

# ===== SUBJECTS =====
class SubjectBase(BaseModel):
    name: str
    grade: int

class SubjectCreate(SubjectBase):
    pass

class SubjectRead(SubjectBase):
    id: int
    class Config:
        orm_mode = True

# ===== ROOMS =====
class RoomBase(BaseModel):
    name: str
    room_type: str

class RoomCreate(RoomBase):
    pass

class RoomRead(RoomBase):
    id: int
    class Config:
        orm_mode = True

# ===== ASSIGNMENTS =====
class AssignmentBase(BaseModel):
    class_id: int
    teacher_id: int
    subject_id: int

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentRead(AssignmentBase):
    id: int
    class Config:
        orm_mode = True
