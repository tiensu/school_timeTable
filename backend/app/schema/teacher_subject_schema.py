# app/schema/teacher_subject_schema.py
from pydantic import BaseModel
from typing import List

class TeacherSubjectBase(BaseModel):
    teacher_id: int
    subject_id: int

class TeacherSubjectCreate(TeacherSubjectBase):
    pass

class TeacherSubjectRead(TeacherSubjectBase):
    id: int

    class Config:
        orm_mode = True
