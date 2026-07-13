"""Sheet / Column 映射引擎

负责：
- Sheet 类型识别（关键词 + 表头命中率）
- 列名规范化与匹配
- 置信度计算
"""

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "config"


def _load_config() -> dict[str, Any]:
    """加载字段和 Sheet 配置"""
    fields_path = CONFIG_DIR / "fields.yaml"
    sheet_path = CONFIG_DIR / "sheet_rules.yaml"
    with open(fields_path, encoding="utf-8") as f:
        fields = yaml.safe_load(f)
    with open(sheet_path, encoding="utf-8") as f:
        sheets = yaml.safe_load(f)
    return {"fields": fields, "sheets": sheets}


def identify_sheet_type(
    sheet_name: str,
    headers: list[str],
    data_preview: list[list[str | None]] | None = None,
) -> dict[str, Any]:
    """识别 Sheet 类型

    评分模型: sheet_score = name_score * 0.4 + header_score * 0.5 + data_score * 0.1
    """
    config = _load_config()
    sheet_config = config.get("sheets", {})
    sheet_types = sheet_config.get("sheet_types", {})
    thresholds = sheet_config.get("thresholds", {"auto_confirm": 0.85, "need_confirm": 0.60})
    field_config = config.get("fields", {}).get("fields", {})

    if data_preview is None:
        data_preview = []

    best_match = None
    best_score = 0.0

    normalized_sheet_name = sheet_name.lower().replace(" ", "")

    for type_code, type_info in sheet_types.items():
        keywords = [k.lower().replace(" ", "") for k in type_info.get("keywords", [])]
        required = type_info.get("required_fields", [])

        # 1. Sheet 名关键词匹配
        name_score = _calc_name_score(normalized_sheet_name, keywords)

        # 2. 表头命中率
        header_score, matched_fields = _calc_header_score(headers, required, field_config)

        # 3. 数据特征（简单判断）
        data_score = _calc_data_score(data_preview, type_info.get("expected_field_types", []))

        final_score = name_score * 0.4 + header_score * 0.5 + data_score * 0.1

        if final_score > best_score:
            best_score = final_score
            best_match = type_code

    need_confirm = best_score < thresholds["auto_confirm"]

    result = {
        "sheet_type": best_match or "unknown",
        "confidence": round(best_score, 2),
        "need_confirm": need_confirm,
    }

    if best_score < thresholds["need_confirm"]:
        result["sheet_type"] = "unknown"

    return result


def _calc_name_score(normalized_name: str, keywords: list[str]) -> float:
    """计算 Sheet 名关键词匹配得分"""
    if not keywords:
        return 0.0
    for kw in keywords:
        if kw in normalized_name:
            return 1.0
    return 0.0


def _calc_header_score(
    headers: list[str],
    required_fields: list[str],
    field_config: dict[str, Any],
) -> tuple[float, list[str]]:
    """计算表头命中率"""
    matched = []
    header_str = " ".join(h.lower() for h in headers)

    for req_field in required_fields:
        field_info = field_config.get(req_field, {})
        aliases = [a.lower() for a in field_info.get("aliases", [req_field])]
        for alias in aliases:
            if alias in header_str:
                matched.append(req_field)
                break

    # 检查所有已知字段别名在表头中的命中率
    all_known_aliases = []
    for fc in field_config.values():
        all_known_aliases.extend(a.lower() for a in fc.get("aliases", []))

    header_hits = sum(1 for a in all_known_aliases if a in header_str)
    total_headers = len(headers) if headers else 1
    hit_rate = min(header_hits / total_headers, 1.0) if total_headers > 0 else 0.0

    # 有必填字段命中则加分
    bonus = 0.2 if len(matched) == len(required_fields) > 0 else 0.0

    score = min(hit_rate * 0.8 + bonus * 0.2, 1.0)
    return score, matched


def _calc_data_score(
    preview: list[list[str | None]],
    expected_types: list[str],
) -> float:
    """计算数据特征评分"""
    if not preview or not expected_types:
        return 0.0
    # 简单检查：有数字/金额数据
    money_count = 0
    total_cells = 0
    for row in preview:
        for cell in row:
            total_cells += 1
            if cell and any(c.isdigit() for c in cell):
                money_count += 1
    return min(money_count / max(total_cells, 1) * 2, 1.0) if total_cells > 0 else 0.0


def match_column(
    original_column: str,
    headers: list[str] | None = None,
) -> dict[str, Any]:
    """将原始列名匹配到标准字段

    使用：完全匹配 → 别名匹配 → 规范化匹配 → 模糊匹配
    """
    from app.engines.importer.importer import normalize_column_name

    config = _load_config()
    field_config = config.get("fields", {}).get("fields", {})
    normalized = normalize_column_name(original_column)
    normalized_lower = normalized.lower()

    best_match = None
    best_score = 0.0

    for field_code, field_info in field_config.items():
        aliases = [normalize_column_name(a).lower() for a in field_info.get("aliases", [])]
        field_name = field_info.get("name", "")
        threshold = field_info.get("match_threshold", 0.85)

        # 完全匹配
        if normalized_lower in aliases:
            score = 1.0
        # 规范化比较
        elif field_name and (normalized_lower == field_name.lower() or normalize_column_name(field_name).lower() == normalized_lower):
            score = 0.95
        else:
            # 模糊匹配：包含关系
            max_similarity = 0.0
            for alias in aliases:
                # 子串匹配
                if alias in normalized_lower or normalized_lower in alias:
                    max_similarity = max(max_similarity, 0.85)
                # 字符重叠
                overlap = len(set(alias) & set(normalized_lower))
                similarity = overlap / max(len(set(alias) | set(normalized_lower)), 1)
                max_similarity = max(max_similarity, similarity)
            score = max_similarity

        if score > best_score:
            best_score = score
            best_match = field_code

    need_confirm = best_score < 0.9

    return {
        "field_code": best_match if best_score >= 0.7 else None,
        "field_name": field_config.get(best_match, {}).get("name") if best_match else None,
        "confidence": round(best_score, 2),
        "need_confirm": need_confirm,
    }
