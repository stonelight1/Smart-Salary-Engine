"""工资解释接口"""

from fastapi import APIRouter, Depends

from app.core.exceptions import BizError
from app.core.security import get_current_user
from app.engines.explainer.explainer import get_employee_explain

router = APIRouter(prefix="/api/v1", tags=["explain"])


@router.get("/salary-runs/{run_id}/employees/{employee_ref_id}/explain")
def api_get_explain(
    run_id: str,
    employee_ref_id: str,
    calc_version: int | None = None,
    user: dict = Depends(get_current_user),
):
    """查询员工工资解释"""
    try:
        result = get_employee_explain(run_id, employee_ref_id, calc_version=calc_version)
        return {"success": True, "data": result, "request_id": ""}
    except BizError:
        raise
