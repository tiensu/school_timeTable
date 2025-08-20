from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.classes_routers import router as class_routers
from app.api.teachers_routers import router as teacher_routers
from app.api.subject_routers import router as subjects_routers
from app.api.timetable_slots_routes import router as timetable_slots_routers
from app.api.timetables_routes import router as timetables_routers
from app.api.reports_routes import router as reports_routers
from app.api.user_routes import router as user_routers
from app.api.home_routes import router as home_routes
from app.models.model import Base, engine 
# 👇 Import tất cả models để đảm bảo chúng được đăng ký vào Base
from app.models import (
    user_model,
    classes_model, 
    teachers_model, 
    subjects_model, 
    class_subject_teacher_model, 
    class_subject_model, 
    timetable_model, 
    timetable_slot_model
)

app = FastAPI()
app.include_router(class_routers)
app.include_router(teacher_routers)
app.include_router(subjects_routers)
app.include_router(timetables_routers)
app.include_router(timetable_slots_routers)
app.include_router(reports_routers)
app.include_router(user_routers)
app.include_router(home_routes)

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
