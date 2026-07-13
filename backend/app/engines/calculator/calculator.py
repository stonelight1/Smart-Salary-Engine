"""工资计算引擎

负责任务的工资公式运算、trace 保存、版本管理
"""

import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.core.config import config_loader
from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.engines.calculator.safe_expr import SafeExpr, SafeExprError
from app.models import (
    SalaryRun, EmployeeRecord, EmployeeFieldValue,
    CalculationResult, CalculationTrace, CheckIssue, AdjustmentItem,
)


def calculate_salary(salary_run_id: str, formula_version: str = "v1") -> dict:
    """执行工资计算"""
    db = SessionLocal()
    try:
        # 1. 前置检查
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        if run.status not in ("CHECK_PASSED", "CALCULATED", "CONFIRMED", "LOCKED"):
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"当前状态不允许计算: {run.status}，请先执行数据检查",
            )

        # 2. 检查是否有未处理的 BLOCK 异常
        open_blocks = db.query(CheckIssue).filter(
            CheckIssue.salary_run_id == salary_run_id,
            CheckIssue.level == "BLOCK",
            CheckIssue.status == "OPEN",
        ).count()
        if open_blocks > 0:
            raise BizError(
                error_code="BLOCK_ISSUE_EXISTS",
                message="存在未处理的严重异常，禁止工资计算",
                details={"block_count": open_blocks},
            )

        # 3. 加载公式配置
        formulas_config = config_loader.get("formula_rules") or {}
        items = formulas_config.get("items", [])
        if not items:
            raise BizError(
                error_code="FORMULA_CONFIG_INVALID",
                message="公式配置无效或为空",
            )

        # 4. 加载舍入配置
        rounding = formulas_config.get("rounding", {})
        intermediate_scale = rounding.get("intermediate_scale", 6)
        final_scale = rounding.get("default_scale", 2)

        # 5. 校验公式配置
        _validate_formulas(items)

        # 6. 递增计算版本
        run.status = "CALCULATING"
        run.current_calc_version += 1
        calc_version = run.current_calc_version
        db.commit()

        # 7. 获取所有员工
        employees = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == salary_run_id,
            EmployeeRecord.status == "NORMAL",
        ).all()

        success_count = 0
        failed_count = 0

        for emp in employees:
            try:
                _calculate_employee(
                    db, emp, salary_run_id, calc_version,
                    items, intermediate_scale, final_scale,
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                # 记录失败
                import traceback
                traceback.print_exc()

        # 8. 更新任务状态
        run.status = "CALCULATED"
        db.commit()

        return {
            "status": "CALCULATED",
            "calc_version": calc_version,
            "employee_count": len(employees),
            "success_count": success_count,
            "failed_count": failed_count,
        }
    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise BizError(
            error_code="INTERNAL_ERROR",
            message=f"工资计算失败: {str(e)}",
        )
    finally:
        db.close()


def _validate_formulas(items: list[dict]):
    """校验公式配置"""
    codes = set()
    for item in items:
        code = item.get("item_code", "")
        if code in codes:
            raise BizError(
                error_code="FORMULA_CONFIG_INVALID",
                message=f"公式项重复: {code}",
            )
        codes.add(code)

    # 检查循环依赖
    deps = {item["item_code"]: set(item.get("dependencies", [])) for item in items}
    # 只检查计算公式项之间的循环，忽略自引用（同名字段引用）
    for item in items:
        code = item["item_code"]
        visited = set()
        stack = [code]
        while stack:
            current = stack.pop()
            if current in visited:
                if current == code:
                    continue  # 自引用（依赖自己的来源字段）不视为循环
                raise BizError(
                    error_code="FORMULA_CONFIG_INVALID",
                    message=f"检测到循环依赖，涉及公式项: {current}",
                )
            visited.add(current)
            for dep in deps.get(current, set()):
                if dep != current and dep in codes:  # 跳过自引用，只查其他公式项
                    stack.append(dep)


def _calculate_employee(
    db: SessionLocal,
    emp: EmployeeRecord,
    salary_run_id: str,
    calc_version: int,
    items: list[dict],
    intermediate_scale: int,
    final_scale: int,
):
    """计算单名员工的工资"""
    # 获取员工字段值
    field_values = db.query(EmployeeFieldValue).filter(
        EmployeeFieldValue.employee_record_id == emp.id,
    ).all()

    # 转换 {field_code: Decimal/value}
    variables: dict[str, Any] = {}
    field_sources: dict[str, dict] = {}
    for fv in field_values:
        val = fv.value_decimal if fv.value_decimal is not None else fv.value_text
        if val is not None:
            variables[fv.field_code] = val
        field_sources[fv.field_code] = {
            "source_text": f"{fv.source_file_id}/{fv.source_sheet}/{fv.source_row}行/{fv.source_column}",
        }

    # 合并人工调整项
    adjustments = db.query(AdjustmentItem).filter(
        AdjustmentItem.employee_record_id == emp.id,
        AdjustmentItem.status == "ACTIVE",
    ).all()
    for adj in adjustments:
        field = adj.field_code
        existing = variables.get(field)
        if existing is None:
            existing = Decimal("0")
        if not isinstance(existing, Decimal):
            try:
                existing = Decimal(str(existing))
            except Exception:
                existing = Decimal("0")
        variables[field] = existing + adj.amount
        field_sources[field] = {
            "source_text": f"人工调整（{adj.adjustment_type}: {adj.reason}）",
        }

    safe_expr = SafeExpr(variables)

    # 按 order 排序
    sorted_items = sorted(items, key=lambda x: x.get("order", 0))

    for item in sorted_items:
        item_code = item["item_code"]
        item_type = item.get("item_type", "")
        expression = item.get("expression", "")
        required = item.get("required", False)
        source_field = item.get("source_field")

        # 输入项直接取变量值
        if item_type == "input" and source_field:
            value = variables.get(source_field)
            if value is None and required:
                # 尝试找字段
                raise BizError(
                    error_code="FORMULA_CONFIG_INVALID",
                    message=f"{emp.employee_name} 的 {item['item_name']} 缺少来源字段 {source_field}",
                )
            if value is not None:
                variables[item_code] = value
                safe_expr._vars[item_code] = value  # 更新表达式变量的计算上下文
            continue

        # 计算项
        if not expression:
            continue

        try:
            result = safe_expr.evaluate(expression)
        except SafeExprError as e:
            if required:
                raise BizError(
                    error_code="FORMULA_CONFIG_INVALID",
                    message=f"{emp.employee_name} 的 {item['item_name']} 公式求值失败: {str(e)}",
                )
            result = Decimal("0")

        if result is None:
            if required:
                raise BizError(
                    error_code="FORMULA_CONFIG_INVALID",
                    message=f"{emp.employee_name} 的 {item['item_name']} 计算为空",
                )
            result = Decimal("0")

        # 舍入
        item_rounding = item.get("rounding", {})
        scale = item_rounding.get("scale", intermediate_scale if item_type in ("intermediate", "add", "input") else final_scale)
        mode = item_rounding.get("mode", "HALF_UP")

        decimal_result = Decimal(str(result))
        rounded = decimal_result.quantize(
            Decimal(f"0.{'0' * scale}"),
            rounding=ROUND_HALF_UP if mode == "HALF_UP" else None,
        )
        variables[item_code] = rounded
        safe_expr._vars[item_code] = rounded  # 更新表达式变量上下文

        # 保存计算结果
        calc_result = CalculationResult(
            id=f"calc_{uuid.uuid4().hex[:8]}",
            salary_run_id=salary_run_id,
            employee_record_id=emp.id,
            calc_version=calc_version,
            item_code=item_code,
            item_name=item["item_name"],
            amount=rounded,
            formula=expression or source_field or "",
        )
        db.add(calc_result)

        # 保存 trace
        depend_fields = item.get("dependencies", [])
        input_values = {}
        input_sources = {}
        for dep in depend_fields:
            input_values[dep] = str(variables.get(dep, ""))
            if dep in field_sources:
                input_sources[dep] = field_sources[dep]["source_text"]

        trace = CalculationTrace(
            id=f"trace_{uuid.uuid4().hex[:8]}",
            calculation_result_id=calc_result.id,
            step_order=item.get("order", 0),
            expression=expression or source_field or "",
            input_values_json=json.dumps(input_values, ensure_ascii=False),
            result_value=str(rounded),
            source_json=json.dumps(input_sources, ensure_ascii=False),
        )
        db.add(trace)

    db.commit()


def get_calculation_results(
    salary_run_id: str,
    calc_version: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """查询计算结果"""
    db = SessionLocal()
    try:
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message="任务不存在")

        version = calc_version or run.current_calc_version

        # 按员工维度汇总结果
        employees = db.query(EmployeeRecord).filter(
            EmployeeRecord.salary_run_id == salary_run_id,
            EmployeeRecord.status == "NORMAL",
        ).all()

        items = []
        total = 0
        for emp in employees:
            total += 1
            results = db.query(CalculationResult).filter(
                CalculationResult.salary_run_id == salary_run_id,
                CalculationResult.employee_record_id == emp.id,
                CalculationResult.calc_version == version,
            ).all()

            fields: dict[str, str] = {}
            for r in results:
                fields[r.item_code] = str(r.amount)

            items.append({
                "employee_ref_id": emp.id,
                "employee_name": emp.employee_name,
                "gross_salary": fields.get("gross_salary"),
                "deduction_total": fields.get("deduction_total"),
                "net_salary": fields.get("net_salary"),
            })

        # 分页
        offset = (page - 1) * page_size
        paged = items[offset:offset + page_size]

        return {"items": paged, "total": total}
    finally:
        db.close()
