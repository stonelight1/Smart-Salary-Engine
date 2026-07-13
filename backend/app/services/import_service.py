"""导入服务 - 编排导入、解析、映射业务流程（含自动修复）"""

import logging
import os
import tempfile
import time
import uuid

from app.core.exceptions import BizError
from app.db.database import SessionLocal
from app.models import ImportBatch, WorkbookFile, SheetMapping, ColumnMapping
from app.engines.importer.importer import (
    validate_file,
    save_file,
    parse_workbook,
    normalize_column_name,
    _generate_batch_id,
)
from app.engines.mapper.mapper import identify_sheet_type, match_column
from app.services.pool_service import build_data_pool
from app.services.excel_repair_service import (
    validate_xlsx,
    classify_parse_error,
    try_repair_libreoffice,
    try_rebuild_value_only,
    diagnose_workbook,
    cleanup_temp_files,
    is_libreoffice_available,
)

logger = logging.getLogger(__name__)


def import_file(
    file_bytes: bytes,
    original_name: str,
    salary_run_id: str,
    file_role: str,
    created_by: str,
) -> dict:
    """执行一次文件导入（含自动修复流程）"""
    # 1. 校验
    validate_file(file_bytes, original_name)

    db = SessionLocal()
    temp_dir = None
    repair_attempted = False
    repair_method = "NONE"
    repair_warnings = []
    actual_file_path = None

    try:
        # 检查任务状态
        from app.models import SalaryRun
        run = db.query(SalaryRun).filter(SalaryRun.id == salary_run_id).first()
        if not run:
            raise BizError(error_code="RESOURCE_NOT_FOUND", message=f"任务不存在: {salary_run_id}")
        if run.status not in ("CREATED", "IMPORTED", "CHECK_FAILED", "CALCULATED", "EXPORTED"):
            raise BizError(
                error_code="RUN_STATUS_NOT_ALLOWED",
                message=f"当前任务状态不允许导入: {run.status}",
            )
        if run.status in ("CALCULATED", "EXPORTED"):
            run.status = "IMPORTED"

        # 2. 保存原始文件
        storage_path, file_hash = save_file(file_bytes, original_name, salary_run_id)
        actual_file_path = storage_path
        file_id = f"file_{uuid.uuid4().hex[:8]}"
        batch_id = _generate_batch_id()

        # 3. 写入文件记录
        wf = WorkbookFile(
            id=file_id,
            salary_run_id=salary_run_id,
            original_name=original_name,
            storage_path=storage_path,
            file_size=len(file_bytes),
            file_hash=file_hash,
            created_by=created_by,
        )
        db.add(wf)

        # 4. 写入导入批次
        ib = ImportBatch(
            id=batch_id,
            salary_run_id=salary_run_id,
            file_id=file_id,
            file_role=file_role,
            status="PARSED",
            created_by=created_by,
        )
        db.add(ib)

        # 5. 解析 workbook（首次尝试）
        parse_result = None
        try:
            parse_result = parse_workbook(storage_path)
        except BizError as e:
            # 判断是否可以修复
            if e.error_code == "EXCEL_PARSE_FAILED" and "自动修复" in e.message:
                logger.info(
                    "文件解析失败，进入自动修复流程: file=%s, role=%s, run=%s",
                    original_name, file_role, salary_run_id,
                )
                repaired = _try_auto_repair(storage_path, file_bytes, original_name)
                if repaired["success"]:
                    repair_attempted = True
                    repair_method = repaired["method"]
                    if repaired.get("warnings"):
                        repair_warnings = repaired["warnings"]
                    # 记录 temp_dir 用于后续清理
                    temp_dir = repaired.get("temp_dir")

                    # 使用修复后的文件重新解析
                    try:
                        parse_result = parse_workbook(repaired["output_path"])
                    except BizError as e2:
                        logger.error("修复后文件仍然无法解析: %s", str(e2.message)[:200])
                        diagnose_workbook(repaired["output_path"])
                        raise BizError(
                            error_code="EXCEL_REPAIR_FAILED",
                            message="Excel 文件内部结构异常，自动修复未成功。请使用 Microsoft Excel 打开文件，选择「另存为」Excel 工作簿（.xlsx）后重新上传。",
                        )
                else:
                    # 修复失败 - 记录 temp_dir 用于清理
                    temp_dir = repaired.get("temp_dir")
                    if repaired.get("error") == "CALAMINE_NOT_INSTALLED":
                        raise BizError(
                            error_code="EXCEL_REPAIR_FAILED",
                            message="Excel 文件解析失败，系统无法自动修复（修复组件未安装）。请使用 Excel 打开文件并另存为 .xlsx 后重新上传。",
                        )
                    diagnose_workbook(storage_path)
                    raise BizError(
                        error_code="EXCEL_REPAIR_FAILED",
                        message="Excel 文件内部结构异常，系统自动修复未成功。请使用 Microsoft Excel 打开文件，选择「另存为」Excel 工作簿（.xlsx）后重新上传。",
                    )
            else:
                raise

        if parse_result is None:
            # 不应发生，但预防空指针
            raise BizError(error_code="EXCEL_PARSE_FAILED", message="Excel 解析结果为空")

        need_confirm_count = 0

        # 6. Sheet 识别与映射
        for sheet_info in parse_result["sheets"]:
            sheet_name = sheet_info["sheet_name"]
            headers = sheet_info["headers"]

            ident = identify_sheet_type(
                sheet_name=sheet_name,
                headers=headers,
                data_preview=sheet_info.get("preview_rows"),
            )

            # 未识别到的 Sheet，尝试按姓名列猜测为工资主表
            if ident["sheet_type"] == "unknown":
                header_text = " ".join(h.lower() if h else "" for h in headers)
                if "姓名" in header_text or "工资" in header_text:
                    ident["sheet_type"] = "salary_main"
                    ident["confidence"] = 0.60
                    ident["need_confirm"] = True

            if ident["need_confirm"]:
                need_confirm_count += 1

            sm = SheetMapping(
                id=f"sheet_{uuid.uuid4().hex[:8]}",
                import_batch_id=batch_id,
                sheet_name=sheet_name,
                sheet_type=ident["sheet_type"],
                confidence=ident["confidence"],
                need_confirm=ident["need_confirm"],
                header_row_index=sheet_info.get("header_row_index"),
            )
            db.add(sm)

            # 7. 列映射
            for col_name in headers:
                col_str = str(col_name) if col_name else ""
                if not col_str.strip():
                    continue
                match = match_column(col_str)
                if match["need_confirm"]:
                    need_confirm_count += 1

                cm = ColumnMapping(
                    id=f"col_{uuid.uuid4().hex[:8]}",
                    sheet_mapping_id=sm.id,
                    original_column=col_str,
                    field_code=match["field_code"],
                    field_name=match["field_name"],
                    confidence=match["confidence"],
                    need_confirm=match["need_confirm"],
                )
                db.add(cm)

        # 8. 提交映射结果
        db.commit()

        # 9. 构建员工数据池
        pool_result = build_data_pool(salary_run_id, batch_id)

        result = {
            "import_batch_id": batch_id,
            "file_id": file_id,
            "file_name": original_name,
            "status": "PARSED",
            "sheet_count": parse_result["sheet_count"],
            "need_confirm_count": need_confirm_count,
            "data_pool": pool_result,
            "repaired": repair_attempted,
            "repair_method": repair_method,
        }

        if repair_warnings:
            result["warnings"] = repair_warnings

        if repair_attempted:
            logger.info(
                "文件自动修复成功: method=%s, file=%s, run=%s",
                repair_method, original_name, salary_run_id,
            )

        return result

    except BizError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("导入处理异常: %s", str(e)[:300], exc_info=True)
        raise BizError(
            error_code="EXCEL_PARSE_FAILED",
            message="导入处理失败，请稍后重试。",
        )
    finally:
        db.close()
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            cleanup_temp_files(temp_dir)


def _try_auto_repair(
    storage_path: str,
    file_bytes: bytes,
    original_name: str,
) -> dict:
    """
    尝试自动修复 Excel 文件。

    修复链:
    1. LibreOffice Headless → 重新保存为标准 xlsx
    2. python-calamine → 仅读取数据值后重建 xlsx

    Returns:
        {"success": True, "output_path": "...", "method": "...", "temp_dir": "...", "warnings": [...]}
        {"success": False, "error": "...", "temp_dir": "..."}
    """
    temp_dir_obj = tempfile.mkdtemp(prefix="excel_repair_")
    start_time = time.time()

    try:
        # 1. 尝试 LibreOffice 修复
        if is_libreoffice_available():
            logger.info("尝试 LibreOffice Headless 修复: %s", original_name)
            lo_result = try_repair_libreoffice(storage_path, temp_dir_obj)
            if lo_result["success"]:
                logger.info(
                    "LibreOffice 修复成功: %s, 耗时=%.2fs",
                    original_name, time.time() - start_time,
                )
                return {
                    "success": True,
                    "output_path": lo_result["output_path"],
                    "method": "LIBREOFFICE_RESAVE",
                    "temp_dir": temp_dir_obj,
                    "warnings": [],
                }
            else:
                logger.warning("LibreOffice 修复失败: %s", lo_result.get("error"))
        else:
            logger.info("LibreOffice 不可用，跳过修复尝试")

        # 2. 尝试 python-calamine 降级重建
        logger.info("尝试 python-calamine 降级读取: %s", original_name)
        calamine_result = try_rebuild_value_only(storage_path, temp_dir_obj)
        if calamine_result["success"]:
            logger.info(
                "calamine 降级重建成功: %s, 耗时=%.2fs",
                original_name, time.time() - start_time,
            )
            return {
                "success": True,
                "output_path": calamine_result["output_path"],
                "method": "VALUE_ONLY_REBUILD",
                "temp_dir": temp_dir_obj,
                "warnings": calamine_result.get("warnings", []),
            }
        else:
            logger.warning("calamine 降级重建失败: %s", calamine_result.get("error"))

        # 全部失败
        return {"success": False, "error": "ALL_REPAIR_METHODS_FAILED", "temp_dir": temp_dir_obj}

    except Exception as e:
        logger.error("自动修复异常: %s", str(e)[:300], exc_info=True)
        return {"success": False, "error": "REPAIR_EXCEPTION", "temp_dir": temp_dir_obj}
