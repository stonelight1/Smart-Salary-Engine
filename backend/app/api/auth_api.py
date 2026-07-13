"""认证接口 - 免登录模式"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    """免登录模式：直接返回固定 token"""
    return {
        "success": True,
        "data": {
            "access_token": "fake_token",
            "user": {"id": "admin", "username": "admin", "role": "admin"},
        },
        "request_id": "",
    }
