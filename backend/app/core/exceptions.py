"""统一错误处理"""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR


ERROR_HTTP_STATUS: dict[str, int] = {
    "UNAUTHORIZED": HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": HTTP_403_FORBIDDEN,
    "INVALID_ARGUMENT": HTTP_400_BAD_REQUEST,
    "RESOURCE_NOT_FOUND": HTTP_404_NOT_FOUND,
    "FILE_TYPE_NOT_SUPPORTED": HTTP_400_BAD_REQUEST,
    "FILE_TOO_LARGE": HTTP_400_BAD_REQUEST,
    "EXCEL_PARSE_FAILED": HTTP_400_BAD_REQUEST,
    # 扩展 Excel 错误码
    "EXCEL_EMPTY_FILE": HTTP_400_BAD_REQUEST,
    "EXCEL_TOO_LARGE": HTTP_400_BAD_REQUEST,
    "EXCEL_INVALID_EXTENSION": HTTP_400_BAD_REQUEST,
    "EXCEL_INVALID_FORMAT": HTTP_400_BAD_REQUEST,
    "EXCEL_CORRUPTED_ZIP": HTTP_400_BAD_REQUEST,
    "EXCEL_INVALID_STRUCTURE": HTTP_400_BAD_REQUEST,
    "EXCEL_REPAIR_TIMEOUT": HTTP_400_BAD_REQUEST,
    "EXCEL_REPAIR_FAILED": HTTP_400_BAD_REQUEST,
    "EXCEL_UNSUPPORTED_FEATURE": HTTP_400_BAD_REQUEST,
    "EXCEL_VALUE_ONLY_WARNING": HTTP_400_BAD_REQUEST,
    "RUN_STATUS_NOT_ALLOWED": HTTP_409_CONFLICT,
    "RUN_BUSY": HTTP_409_CONFLICT,
    "BLOCK_ISSUE_EXISTS": HTTP_409_CONFLICT,
    "FORMULA_CONFIG_INVALID": HTTP_500_INTERNAL_SERVER_ERROR,
    "INTERNAL_ERROR": HTTP_500_INTERNAL_SERVER_ERROR,
}


class BizError(Exception):
    """业务异常"""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def http_status(self) -> int:
        return ERROR_HTTP_STATUS.get(self.error_code, HTTP_500_INTERNAL_SERVER_ERROR)


def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status(),
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "request_id": getattr(request.state, "request_id", ""),
            "details": exc.details,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "系统内部错误",
            "request_id": getattr(request.state, "request_id", ""),
            "details": {},
        },
    )
