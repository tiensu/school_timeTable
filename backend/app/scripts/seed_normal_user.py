# app/scripts/seed_normal_user.py
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.model import SessionLocal
from app.models.user_model import User
from loguru import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_USERNAME = "user1"
DEFAULT_PASSWORD = "user123"  # ⚠️ đổi sau khi tạo

def get_password_hash(plain: str) -> str:
    return pwd_context.hash(plain)

def seed_user(db: Session):
    user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
    if user:
        logger.info("Normal user đã tồn tại: {}", DEFAULT_USERNAME)
        return

    user = User(
        username=DEFAULT_USERNAME,
        password_hash=get_password_hash(DEFAULT_PASSWORD),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    logger.success("✅ Tạo normal user mặc định: {} / {}", DEFAULT_USERNAME, DEFAULT_PASSWORD)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_user(db)
    finally:
        db.close()
