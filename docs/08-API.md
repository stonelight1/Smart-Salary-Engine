# 08 - API（接口契约）

> Project: Smart Salary Engine（SSE）  
> Version: V1.2  
> Status: MVP 可开发基线

---

## 1. API 设计原则

1. 所有接口使用 `/api/v1` 前缀；
2. 请求和响应使用 JSON，文件上传使用 multipart；
3. 返回统一结构；
4. 错误码稳定，不直接暴露后端异常；
5. 涉及敏感工资数据的接口必须鉴权；
6. MVP 本机单用户可同步返回处理结果；后续数据量变大再升级为 job/status；
7. 导出文件使用下载接口，不暴露真实文件路径。

---

## 2. 统一响应结构

### 2.1 成功响应

```json
{
  "success": true,
  "data": {},
  "request_id": "req_20260705_001"
}
```

### 2.2 失败响应

```json
{
  "success": false,
  "error_code": "BLOCK_ISSUE_EXISTS",
  "message": "存在未处理的严重异常，禁止工资计算",
  "request_id": "req_20260705_001",
  "details": {
    "block_count": 3
  }
}
```

---

## 3. 通用错误码

| 错误码 | HTTP | 说明 |
|---|---:|---|
| UNAUTHORIZED | 401 | 未登录或 Token 无效 |
| FORBIDDEN | 403 | 无权限 |
| INVALID_ARGUMENT | 400 | 参数错误 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| FILE_TYPE_NOT_SUPPORTED | 400 | 文件类型不支持 |
| FILE_TOO_LARGE | 400 | 文件过大 |
| EXCEL_PARSE_FAILED | 400 | Excel 解析失败 |
| RUN_STATUS_NOT_ALLOWED | 409 | 当前任务状态不允许操作 |
| RUN_BUSY | 409 | 当前任务已有操作进行中 |
| BLOCK_ISSUE_EXISTS | 409 | 存在 BLOCK 异常 |
| FORMULA_CONFIG_INVALID | 500 | 公式配置无效 |
| INTERNAL_ERROR | 500 | 系统异常 |

---

## 4. 认证接口

### 4.1 登录

`POST /api/v1/auth/login`

请求：

```json
{
  "username": "hr01",
  "password": "password"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "access_token": "token",
    "token_type": "Bearer",
    "user": {
      "id": "user_001",
      "username": "hr01",
      "role": "HR"
    }
  },
  "request_id": "req_001"
}
```

---

## 5. Salary Run 接口

### 5.1 创建工资核算任务

`POST /api/v1/salary-runs`

请求：

```json
{
  "name": "2026年7月工资核算",
  "payroll_month": "2026-07",
  "remark": "总部工资"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "run_001",
    "name": "2026年7月工资核算",
    "payroll_month": "2026-07",
    "status": "CREATED",
    "created_at": "2026-07-05T20:15:00+09:00"
  },
  "request_id": "req_001"
}
```

### 5.2 查询任务列表

`GET /api/v1/salary-runs?page=1&page_size=20&keyword=2026`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "run_001",
        "name": "2026年7月工资核算",
        "payroll_month": "2026-07",
        "status": "CHECK_FAILED",
        "block_count": 2,
        "warn_count": 5,
        "created_at": "2026-07-05T20:15:00+09:00",
        "updated_at": "2026-07-05T20:30:00+09:00"
      }
    ],
    "total": 1
  },
  "request_id": "req_002"
}
```

### 5.3 查询任务详情

`GET /api/v1/salary-runs/{run_id}`

响应字段：

- 基础信息；
- 当前状态；
- 导入批次数量；
- 员工数量；
- 异常数量；
- 当前计算版本；
- 最近导出文件。

---

## 6. 文件导入接口

### 6.1 上传 Excel

`POST /api/v1/salary-runs/{run_id}/files`

Content-Type: `multipart/form-data`

参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | file | 是 | `.xlsx` 文件 |
| file_role | string | 是 | `MAIN` / `SUPPLEMENT` |
| overwrite | boolean | 否 | 是否覆盖已有数据，默认 false |

响应：

```json
{
  "success": true,
  "data": {
    "import_batch_id": "batch_001",
    "file_id": "file_001",
    "file_name": "7月工资表.xlsx",
    "status": "PARSED",
    "sheet_count": 3,
    "need_confirm_count": 1
  },
  "request_id": "req_003"
}
```

### 6.2 查询 Sheet 识别结果

`GET /api/v1/import-batches/{batch_id}/sheets`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "sheet_mapping_id": "sheet_map_001",
        "sheet_name": "工资表",
        "sheet_type": "salary_main",
        "confidence": 0.93,
        "need_confirm": false,
        "row_count": 120,
        "header_row_index": 2
      }
    ]
  },
  "request_id": "req_004"
}
```

### 6.3 确认 Sheet 类型

`PATCH /api/v1/sheet-mappings/{sheet_mapping_id}`

请求：

```json
{
  "sheet_type": "salary_main",
  "header_row_index": 2,
  "confirm_remark": "人工确认为工资主表"
}
```

---

## 7. 列映射接口

### 7.1 查询列映射

`GET /api/v1/sheet-mappings/{sheet_mapping_id}/columns`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "column_mapping_id": "col_map_001",
        "original_column": "基本薪资",
        "field_code": "base_salary",
        "field_name": "基本工资",
        "confidence": 0.95,
        "need_confirm": false
      }
    ]
  },
  "request_id": "req_005"
}
```

### 7.2 修改列映射

`PATCH /api/v1/column-mappings/{column_mapping_id}`

请求：

```json
{
  "field_code": "base_salary",
  "confirm_remark": "人工映射为基本工资"
}
```

---

## 8. 员工数据池接口

### 8.1 查询员工数据池

`GET /api/v1/salary-runs/{run_id}/employees?page=1&page_size=20&keyword=张三`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "employee_ref_id": "emp_001",
        "employee_name": "张三",
        "status": "NORMAL",
        "fields": {
          "base_salary": "8000.00",
          "performance_bonus": "1000.00",
          "net_salary": "8500.00"
        },
        "issue_count": 0
      }
    ],
    "total": 1
  },
  "request_id": "req_006"
}
```

### 8.2 查询员工详情

`GET /api/v1/employees/{employee_ref_id}`

响应包含：

- 员工基础信息；
- 标准字段值；
- 每个字段来源；
- 异常列表；
- 计算结果。

### 8.3 人工修改字段值

`PATCH /api/v1/employees/{employee_ref_id}/fields/{field_code}`

请求：

```json
{
  "value": "8500.00",
  "reason": "根据HR复核结果补录"
}
```

人工修改字段值作为正式数据保存，后端必须记录 `is_manual=true`、处理人、处理时间和原因。

---

## 9. 检查接口

### 9.1 发起数据检查

`POST /api/v1/salary-runs/{run_id}/check`

响应：

```json
{
  "success": true,
  "data": {
    "status": "CHECK_FAILED",
    "block_count": 2,
    "warn_count": 5,
    "info_count": 1
  },
  "request_id": "req_007"
}
```

### 9.2 查询异常列表

`GET /api/v1/salary-runs/{run_id}/issues?level=BLOCK&status=OPEN&page=1&page_size=20`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "issue_id": "issue_001",
        "level": "BLOCK",
        "issue_code": "FIELD_REQUIRED_MISSING",
        "message": "张三缺少基本工资，无法计算工资",
        "employee_name": "张三",
        "field_code": "base_salary",
        "status": "OPEN"
      }
    ],
    "total": 1
  },
  "request_id": "req_008"
}
```

### 9.3 处理异常

`PATCH /api/v1/issues/{issue_id}`

请求：

```json
{
  "action": "FILL_VALUE",
  "value": "8000.00",
  "reason": "根据工资主表补录"
}
```

响应：

```json
{
  "success": true,
  "data": {
    "issue_id": "issue_001",
    "status": "RESOLVED"
  },
  "request_id": "req_009"
}
```

---

## 10. 计算接口

### 10.1 发起工资计算

`POST /api/v1/salary-runs/{run_id}/calculate`

请求：

```json
{
  "formula_version": "v1"
}
```

成功响应：

```json
{
  "success": true,
  "data": {
    "status": "CALCULATED",
    "calc_version": 1,
    "employee_count": 120,
    "success_count": 120,
    "failed_count": 0
  },
  "request_id": "req_010"
}
```

失败响应示例：

```json
{
  "success": false,
  "error_code": "BLOCK_ISSUE_EXISTS",
  "message": "存在未处理的严重异常，禁止工资计算",
  "request_id": "req_011",
  "details": {
    "block_count": 2
  }
}
```

### 10.2 查询计算结果

`GET /api/v1/salary-runs/{run_id}/calculation-results?calc_version=1&page=1&page_size=20`

响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "employee_ref_id": "emp_001",
        "employee_name": "张三",
        "gross_salary": "9200.00",
        "deduction_total": "700.00",
        "net_salary": "8500.00"
      }
    ],
    "total": 1
  },
  "request_id": "req_012"
}
```

---

## 11. 工资解释接口

### 11.1 查询员工工资解释

`GET /api/v1/salary-runs/{run_id}/employees/{employee_ref_id}/explain?calc_version=1`

响应：

```json
{
  "success": true,
  "data": {
    "employee_name": "张三",
    "calc_version": 1,
    "net_salary": "8500.00",
    "summary": "张三本次实发工资为 8500.00 元。",
    "items": [
      {
        "item_code": "gross_salary",
        "item_name": "应发工资",
        "amount": "9200.00",
        "formula": "base_salary + performance_bonus + allowance_total - attendance_deduction",
        "inputs": [
          {
            "field_code": "base_salary",
            "field_name": "基本工资",
            "value": "8000.00",
            "source_text": "7月工资表.xlsx / 工资表 / 第12行 / 基本工资"
          }
        ]
      }
    ],
    "warnings": []
  },
  "request_id": "req_013"
}
```

---

## 12. 导出接口

### 12.1 发起导出

`POST /api/v1/salary-runs/{run_id}/export`

请求：

```json
{
  "calc_version": 1,
  "use_main_workbook_template": true,
  "include_trace": true,
  "include_issues": true,
  "include_sources": true
}
```

MVP 默认 `use_main_workbook_template=true`：复制工资主表作为导出模板，尽量保留原表样式、列宽、表头和格式，并将计算过程、异常报告、来源明细作为附加 Sheet。

响应：

```json
{
  "success": true,
  "data": {
    "export_file_id": "export_001",
    "file_name": "2026年7月工资核算_工资结果_v1.xlsx",
    "download_url": "/api/v1/export-files/export_001/download"
  },
  "request_id": "req_014"
}
```

### 12.2 下载导出文件

`GET /api/v1/export-files/{export_file_id}/download`

响应：

- 文件流；
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`。

---

## 13. 配置查询接口

### 13.1 查询标准字段

`GET /api/v1/config/fields`

### 13.2 查询公式版本

`GET /api/v1/config/formulas`

### 13.3 查询检查规则

`GET /api/v1/config/check-rules`

MVP 可以只读；后续再支持页面配置和更新。

---

## 14. API 验收标准

1. 每个接口有请求体、响应体、错误码；
2. 工资计算前存在 BLOCK 异常时返回 `BLOCK_ISSUE_EXISTS`；
3. 下载文件不暴露服务器真实路径；
4. 所有敏感接口必须登录；
5. 上传非法文件返回明确错误；
6. 状态不允许操作时返回 `RUN_STATUS_NOT_ALLOWED`；
7. 响应包含 `request_id`；
8. 前后端可基于本文档并行开发。
