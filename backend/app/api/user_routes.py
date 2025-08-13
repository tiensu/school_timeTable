# app/routers/user_routes.py
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.models.model import SessionLocal
from app.models.user_model import User  # Giả định có model này
from loguru import logger

router = APIRouter(prefix="/api/users", tags=["users"])

# ================== CONFIG / UTILS ==================
SECRET_KEY = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET"  # => thay bằng biến môi trường
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 giờ

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")  # để FastAPI UI biết luồng

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

# ================== SCHEMAS ==================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class MeResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

class MenuItem(BaseModel):
    label: str
    path: str
    icon: str

# ================== AUTH HELPERS ==================
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực. Vui lòng đăng nhập lại.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user: Optional[User] = db.query(User).filter(User.username == sub).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập tài nguyên này.")
    return current_user

# ================== ROUTES ==================
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for user: {payload.username}")
    user: Optional[User] = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Sai tên đăng nhập hoặc mật khẩu.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Sai tên đăng nhập hoặc mật khẩu.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đang bị khóa.")

    access_token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=access_token, username=user.username, role=user.role)

@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )

@router.get("/menu", response_model=List[MenuItem])
def get_menu(current_user: User = Depends(get_current_user)):
    """
    Trả về danh sách menu theo role.
    - admin: thấy tất cả
    - user: ẩn 'Cấu hình'
    """
    base_menu: List[MenuItem] = [
        MenuItem(label="Môn học", path="/subjects", icon="bi-journal-bookmark"),
        MenuItem(label="Lớp học", path="/classes", icon="bi-building"),
        MenuItem(label="Giáo viên", path="/teachers", icon="bi-person-badge"),
        MenuItem(label="Phòng học", path="/rooms", icon="bi-door-open"),
        MenuItem(label="Thời khóa biểu", path="/schedule", icon="bi-calendar-week"),
        MenuItem(label="Báo cáo & Thống kê", path="/reports", icon="bi-bar-chart-line"),
    ]
    settings_item = MenuItem(label="Cấu hình", path="/settings", icon="bi-sliders2-vertical")

    if current_user.role == "admin":
        return base_menu[:3] + [settings_item] + base_menu[3:]  # chèn Settings sau 3 mục đầu
    else:
        return base_menu  # không có Settings cho normal user

@router.get("/check")
def check_token(_: User = Depends(get_current_user)):
    """ Endpoint đơn giản để FE kiểm tra token còn hợp lệ. """
    return {"ok": True}
