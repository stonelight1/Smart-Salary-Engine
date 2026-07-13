"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import config_loader
from app.core.exceptions import BizError, biz_error_handler, global_exception_handler
from app.core.logging import generate_request_id
from app.db.database import init_db
from app.db.seed import seed_default_user
from app.api import auth_api, salary_run_api, import_api, employee_api, check_api, calculation_api, explain_api, export_api, adjustment_api, v2_api, reference_api, employee_v4_api, snapshot_api, attendance_compare_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_loader.load_all()
    init_db()
    seed_default_user()
    yield


app = FastAPI(title="Smart Salary Engine API", version="0.1.0", lifespan=lifespan)

# CORS - MVP 允许本地前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
app.exception_handler(BizError)(biz_error_handler)
app.exception_handler(Exception)(global_exception_handler)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = generate_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# 注册路由
app.include_router(auth_api.router)
app.include_router(salary_run_api.router)
app.include_router(import_api.router)
app.include_router(employee_api.router)
app.include_router(check_api.router)
app.include_router(calculation_api.router)
app.include_router(explain_api.router)
app.include_router(export_api.router)
app.include_router(adjustment_api.router)
app.include_router(v2_api.router)
app.include_router(reference_api.router)
app.include_router(employee_v4_api.router)
app.include_router(snapshot_api.router)
app.include_router(attendance_compare_api.router)


@app.get("/api/v1/health")
def health_check():
    return {"success": True, "data": {"status": "ok"}, "request_id": ""}
