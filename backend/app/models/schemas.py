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
    class Config:
        orm_mode = True

# ===== TEACHERS =====
class TeacherBase(BaseModel):
    name: str
    email: Optional[str] = None
    max_weekly_sessions: int

class TeacherCreate(TeacherBase):
    pass

class TeacherRead(TeacherBase):
    id: int
    class Config:
        orm_mode = True

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
