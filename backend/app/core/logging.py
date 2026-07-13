"""日志、request_id 等中间件"""

import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"
