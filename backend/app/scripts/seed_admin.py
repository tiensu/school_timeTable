# app/scripts/seed_admin.py
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.user_model import User
from loguru import logger

# cấu hình bcrypt giống user_routes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # ⚠️ đổi ngay sau khi khởi tạo

def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)

def seed_admin(db: Session):
    admin = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
    if admin:
        logger.info("Admin user đã tồn tại: {}", DEFAULT_ADMIN_USERNAME)
        return

    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.success("Tạo admin mặc định: {} / {}", DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()
