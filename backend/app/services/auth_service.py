"""认证服务"""

from app.core.exceptions import BizError
from app.core.security import hash_password, create_token
from app.db.database import SessionLocal
from app.models import User


def authenticate(username: str, password: str) -> dict:
    """用户认证，成功返回 token 和用户信息"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.password_hash != hash_password(password):
            raise BizError(
                error_code="UNAUTHORIZED",
                message="用户名或密码错误",
            )
        token = create_token(user.id, user.username, user.role)
        return {
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
            },
        }
    finally:
        db.close()
