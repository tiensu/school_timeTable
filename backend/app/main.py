from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.classes_routers import router as class_routers
from app.api.teachers_routers import router as teacher_routers
from app.api.subject_routers import router as subjects_routers
from app.models.model import Base, engine 
# 👇 Import tất cả models để đảm bảo chúng được đăng ký vào Base
from app.models import classes_model, teachers_model, subjects_model, teacher_subject_model, class_subject_teacher_model, class_subject_model, timetable_model, timetable_slot_model

app = FastAPI()
app.include_router(class_routers)
app.include_router(teacher_routers)
app.include_router(subjects_routers)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👇 Tạo bảng trong CSDL nếu chưa có
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Timetable App Backend is running"}
