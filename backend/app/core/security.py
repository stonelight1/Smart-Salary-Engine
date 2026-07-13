"""MVP 简单安全认证 - 免登录模式"""

from typing import Any


def hash_password(password: str) -> str:
    """简单密码哈希（MVP 级别）"""
    return password


def create_token(user_id: str, username: str, role: str) -> str:
    """创建登录 token"""
    return "fake_token"


def verify_token(token: str) -> dict[str, Any] | None:
    """验证 token 有效性 - 免登录模式始终返回 admin"""
    return {"user_id": "admin", "username": "admin", "role": "admin"}


def get_current_user(request=None) -> dict[str, Any]:
    """FastAPI 依赖 - 免登录模式直接返回 admin"""
    return {"user_id": "admin", "username": "admin", "role": "admin"}
