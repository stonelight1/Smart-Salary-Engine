"""工资解释引擎"""

import json

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import (
    SalaryRun, EmployeeRecord, EmployeeFieldValue,
    CalculationResult, CalculationTrace, CheckIssue,
)


def get_employee_explain(
    salary_run_id: str,
    employee_ref_id: str,
    calc_version: int | None = None,
) -> dict:
    """查询员工工资解释"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        version = calc_version or run.current_calc_version
        if version == 0:
            raise BizError(error_code="INVALID_ARGUMENT", message="尚未计算工资")

        emp = db.query(EmployeeRecord).filter(EmployeeRecord.id == employee_ref_id).first()
        if not emp:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="员工不存在")

        # 获取最终工资
        net_results = db.query(CalculationResult).filter(
            CalculationResult.salary_run_id == salary_run_id,
            CalculationResult.employee_record_id == employee_ref_id,
            CalculationResult.calc_version == version,
            CalculationResult.item_code == "net_salary",
        ).all()

        net_salary = net_results[0].amount if net_results else "0.00"

        # 获取所有工资项结果
        all_results = db.query(CalculationResult).filter(
            CalculationResult.salary_run_id == salary_run_id,
            CalculationResult.employee_record_id == employee_ref_id,
            CalculationResult.calc_version == version,
        ).order_by(CalculationResult.id).all()

        items = []
        for r in all_results:
            # 获取 trace
            traces = db.query(CalculationTrace).filter(
                CalculationTrace.calculation_result_id == r.id,
            ).all()

            inputs = []
            for t in traces:
                input_vals = json.loads(t.input_values_json) if t.input_values_json else {}
                sources = json.loads(t.source_json) if t.source_json else {}
                for field_code, val in input_vals.items():
                    if field_code != r.item_code:
                        inputs.append({
                            "field_code": field_code,
                            "field_name": field_code,
                            "value": str(val),
                            "source_text": sources.get(field_code, "系统计算"),
                        })

            items.append({
                "item_code": r.item_code,
                "item_name": r.item_name,
                "amount": str(r.amount),
                "formula": r.formula,
                "inputs": inputs,
            })

        # 获取字段来源
        field_values = db.query(EmployeeFieldValue).filter(
            EmployeeFieldValue.employee_record_id == employee_ref_id,
        ).all()

        field_sources = {}
        for fv in field_values:
            if fv.source_file_id == "manual":
                field_sources[fv.field_code] = f"人工补录（{fv.manual_reason or ''}）"
            else:
                field_sources[fv.field_code] = f"{fv.source_file_id}/{fv.source_sheet}/{fv.source_row}行/{fv.source_column}"

        # WARN 检查
        warnings_list = db.query(CheckIssue).filter(
            CheckIssue.salary_run_id == salary_run_id,
            CheckIssue.employee_record_id == employee_ref_id,
            CheckIssue.level == "WARN",
            CheckIssue.status == "OPEN",
        ).all()

        # 生成摘要
        summary = f"{emp.employee_name} 本次实发工资为 {net_salary} 元。\n\n"
        for item in items:
            if item["inputs"]:
                inputs_str = " + ".join(
                    f"{i.get('field_name','')} {i['value']}"
                    for i in item["inputs"]
                    if i["value"] and i["value"] != "0"
                )
                if inputs_str:
                    summary += f"{item['item_name']} = {inputs_str} = {item['amount']} 元。\n"
            elif item["item_code"] == "net_salary":
                summary += f"{item['item_name']} = {item['amount']} 元。\n"

        return {
            "employee_name": emp.employee_name,
            "calc_version": version,
            "net_salary": str(net_salary),
            "summary": summary,
            "items": items,
            "warnings": [w.message for w in warnings_list],
        }
    finally:
        db.close()
