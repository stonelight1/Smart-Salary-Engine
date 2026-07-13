"""数据库初始数据"""

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models import User


def seed_default_user():
    """创建默认管理员用户（仅首次运行时）"""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            return
        user = User(
            id="user_admin",
            username="admin",
            password_hash=hash_password("admin123"),
            role="HR",
        )
        db.add(user)
        db.commit()
        print("[seed] 默认用户已创建: admin / admin123")
    finally:
        db.close()
