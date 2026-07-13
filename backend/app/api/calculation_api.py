"""工资计算接口"""

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.engines.calculator.calculator import calculate_salary, get_calculation_results

router = APIRouter(prefix="/api/v1", tags=["calculation"])


@router.post("/salary-runs/{run_id}/calculate")
def api_calculate(
    run_id: str,
    body: dict = {},
    user: dict = Depends(get_current_user),
):
    """发起工资计算"""
    try:
        result = calculate_salary(
            run_id,
            formula_version=body.get("formula_version", "v1"),
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise


@router.get("/salary-runs/{run_id}/calculation-results")
def api_get_results(
    run_id: str,
    calc_version: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """查询计算结果"""
    try:
        result = get_calculation_results(
            run_id,
            calc_version=calc_version,
            page=page,
            page_size=page_size,
        )
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
