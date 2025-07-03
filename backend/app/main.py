from fastapi import FastAPI
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import Base, engine 

app = FastAPI()
app.include_router(router)

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
