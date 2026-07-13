# 10 - Coding Rule（编码规范）

> Project: Smart Salary Engine（SSE）  
> Version: V1.2  
> Status: MVP 可开发基线

---

## 1. 总原则

1. 禁止写死 Sheet 名和列名；
2. 禁止直接修改原始 Excel；
3. 禁止使用 float 计算工资金额；
4. 禁止直接 `eval` 执行公式；
5. 所有核心数据必须有来源；
6. 所有计算必须保存过程；
7. 所有 API 必须有明确错误码；
8. 所有引擎必须可单元测试；
9. 业务规则优先配置化。

---

## 2. 后端目录规范

```text
backend/app/
├── api/                 # FastAPI 路由
│   ├── auth_api.py
│   ├── salary_run_api.py
│   ├── import_api.py
│   ├── issue_api.py
│   ├── calculation_api.py
│   └── export_api.py
├── core/                # 配置、异常、日志、安全
├── db/                  # 数据库连接、迁移
├── models/              # ORM 模型
├── schemas/             # Pydantic DTO
├── services/            # 业务服务
├── engines/             # 可测试的核心引擎
│   ├── importer/
│   ├── mapper/
│   ├── checker/
│   ├── calculator/
│   ├── explainer/
│   └── exporter/
└── utils/
```

---

## 3. Python 编码规范

### 3.1 类型注解

所有函数必须写类型注解。

```python
def normalize_money(value: str | None) -> Decimal | None:
    ...
```

### 3.2 金额计算

必须使用 Decimal。

```python
from decimal import Decimal, ROUND_HALF_UP

amount = Decimal("100.00")
result = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

禁止：

```python
amount = 0.1 + 0.2
```

### 3.3 公式执行

禁止：

```python
eval(expression)
```

推荐：

- 使用安全表达式解析器；
- 或自行实现 AST 白名单；
- 函数必须注册在 allowlist 中。

### 3.4 异常处理

业务异常使用统一异常类：

```python
raise BizError(
    error_code="BLOCK_ISSUE_EXISTS",
    message="存在未处理的严重异常，禁止工资计算",
    details={"block_count": block_count},
)
```

不允许将原始堆栈直接返回前端。

---

## 4. API 规范

### 4.1 路由命名

- 使用 REST 风格；
- 使用复数资源名；
- 使用 `/api/v1` 前缀。

示例：

```text
POST /api/v1/salary-runs
GET  /api/v1/salary-runs/{run_id}
POST /api/v1/salary-runs/{run_id}/check
```

### 4.2 响应结构

所有接口必须返回统一结构：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_001"
}
```

失败：

```json
{
  "success": false,
  "error_code": "INVALID_ARGUMENT",
  "message": "参数错误",
  "request_id": "req_001",
  "details": {}
}
```

---

## 5. 配置规范

配置文件放在 `config/`：

- `fields.yaml`；
- `sheet_rules.yaml`；
- `check_rules.yaml`；
- `formula_rules.yaml`；
- `export_templates.yaml`。

要求：

1. 启动时校验配置；
2. 配置缺失直接启动失败；
3. 配置字段必须有 schema 校验；
4. 公式依赖字段不存在时禁止计算；
5. 生产环境修改配置必须记录版本。

---

## 6. Excel 处理规范

1. 原始 Excel 只读保存；
2. 所有导出文件通过复制模板新生成；
3. 不允许覆盖用户上传文件；
4. 读取单元格必须记录来源；
5. 表头识别失败必须产生异常；
6. 公式单元格读取缓存值，并记录 WARN；
7. 合并单元格必须谨慎处理，无法确定则人工确认。
8. 工资结果导出默认复制工资主表作为模板，尽量保留样式、列宽、表头和格式。

---

## 7. 数据库规范

1. 所有表必须有 `id`、`created_at`、`updated_at`；
2. 关键操作记录 `created_by`/`updated_by`；
3. 任务相关表必须有 `salary_run_id`；
4. 金额字段使用 Decimal/Numeric，不使用 float；
5. JSON 字段只存扩展信息，不作为核心查询条件；
6. 删除优先软删除或状态作废；
7. 计算结果使用版本号，不覆盖历史。

---

## 8. 前端编码规范

### 8.1 TypeScript

- 禁止 `any` 滥用；
- API 响应定义类型；
- 页面状态使用明确枚举。

示例：

```ts
export type RunStatus =
  | 'CREATED'
  | 'IMPORTED'
  | 'CHECK_FAILED'
  | 'CHECK_PASSED'
  | 'CALCULATED'
  | 'EXPORTED'
  | 'FAILED'
```

### 8.2 组件拆分

建议组件：

```text
components/
├── RunStepBar.vue
├── FileUploadPanel.vue
├── SheetMappingTable.vue
├── ColumnMappingTable.vue
├── IssueLevelTag.vue
├── IssueResolveDialog.vue
├── FieldSourceDrawer.vue
├── CalculationResultTable.vue
└── SalaryExplainPanel.vue
```

### 8.3 错误处理

- API 错误统一拦截；
- `UNAUTHORIZED` 跳转登录；
- `BLOCK_ISSUE_EXISTS` 跳转异常中心；
- 上传错误在上传组件内展示；
- 系统错误用弹窗并展示 request_id。

---

## 9. 测试规范

### 9.1 后端测试

必须覆盖：

| 模块 | 测试内容 |
|---|---|
| Importer | 文件解析、表头识别、空文件、损坏文件 |
| Mapper | Sheet 识别、列名匹配、低置信度 |
| Data Pool | 姓名合并、重名阻断、冲突 |
| Check Engine | BLOCK/WARN/INFO 规则 |
| Calculator | Decimal、公式依赖、舍入、异常 |
| Exporter | 导出文件内容、不修改原文件、保留主表模板样式 |
| API | 成功/失败响应、错误码、鉴权 |

### 9.2 前端测试

至少覆盖：

- 关键页面渲染；
- 上传失败提示；
- 计算按钮禁用逻辑；
- 异常处理弹窗；
- API 错误展示。

---

## 10. 日志规范

日志必须包含：

- request_id；
- user_id；
- salary_run_id；
- operation；
- result；
- duration_ms。

禁止普通日志直接打印：

- 完整工资表；
- 身份证；
- 银行卡；
- 大批量工资金额明细；
- access token。

---

## 11. Git 与提交规范

提交信息建议：

```text
feat(import): support sheet auto detection
fix(calc): use Decimal rounding for net salary
refactor(api): unify error response
 test(check): add duplicate employee tests
 docs(formula): add formula config example
```

分支建议：

```text
main
feature/importer
feature/check-engine
feature/calculator
feature/frontend-flow
```

---

## 12. CI 检查项

MVP 至少执行：

- 后端单元测试；
- 前端 type check；
- 前端 build；
- 格式检查；
- 配置文件 schema 校验。

---

## 13. 禁止清单

严禁：

1. 直接覆盖原始 Excel；
2. 工资金额使用 float；
3. 公式使用 eval；
4. Sheet 名硬编码；
5. 列名硬编码；
6. BLOCK 异常未处理仍允许计算；
7. 只保存最终工资，不保存过程；
8. API 返回不稳定结构；
9. 日志打印完整敏感数据；
10. 把系统内数据当长期员工档案维护。
