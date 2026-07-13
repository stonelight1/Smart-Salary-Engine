# 07 - Formula（工资公式体系）

> Project: Smart Salary Engine（SSE）  
> Version: V1.2  
> Status: MVP 可开发基线

---

## 1. 设计目标

工资计算是 SSE 的核心模块。公式体系必须满足：

1. 工资项配置化，不硬编码；
2. 支持计算顺序和依赖关系；
3. 金额使用 Decimal，避免浮点误差；
4. 每个工资项保存公式、输入、来源、结果；
5. 严重异常时禁止计算；
6. 公式可测试、可审计、可解释。

---

## 2. 基本原则

| 原则 | 说明 |
|---|---|
| 配置驱动 | 工资项、公式、舍入方式来自配置文件 |
| 显式依赖 | 每个公式声明依赖字段和依赖工资项 |
| 安全表达式 | 禁止执行任意 Python 代码 |
| Decimal 计算 | 金额统一使用 Decimal |
| 中间高精度 | 中间过程不随意四舍五入 |
| 最终到分 | 最终导出金额精确到 0.01 |
| 过程留痕 | 保存公式、输入、来源、结果 |

---

## 3. 工资项分类

| 分类 | 示例 | 说明 |
|---|---|---|
| 基础项 | basic_salary | 来自 Excel 或配置 |
| 加项 | bonus_total, allowance_total | 增加工工资 |
| 减项 | deduction_total, social_security_personal | 扣减工资 |
| 中间项 | gross_salary, taxable_salary | 供后续公式使用 |
| 最终项 | net_salary | 最终实发工资 |
| 展示项 | remark, warning_count | 只展示不参与计算 |

---

## 4. MVP 标准工资项

| item_code | 名称 | 类型 | 默认公式 |
|---|---|---|---|
| base_salary | 基本工资 | 输入项 | 来自字段 `base_salary` |
| attendance_deduction | 考勤扣款 | 减项 | `if_null(attendance_deduction, 0)` |
| performance_bonus | 绩效奖金 | 加项 | `if_null(performance_bonus, 0)` |
| allowance_total | 补贴合计 | 加项 | `sum([meal_allowance, traffic_allowance, communication_allowance])` |
| other_deduction | 其他扣款 | 减项 | `if_null(other_deduction, 0)` |
| social_security_personal | 社保个人扣款 | 减项 | `if_null(social_security_personal, 0)` |
| housing_fund_personal | 公积金个人扣款 | 减项 | `if_null(housing_fund_personal, 0)` |
| gross_salary | 应发工资 | 中间项 | `base_salary + performance_bonus + allowance_total - attendance_deduction` |
| deduction_total | 扣款合计 | 中间项 | `other_deduction + social_security_personal + housing_fund_personal` |
| net_salary | 实发工资 | 最终项 | `gross_salary - deduction_total` |

说明：MVP 不计算个税，也不负责个税申报。若后续需要计算个税，可作为配置公式项加入，但必须明确由用户提供税率规则并自行复核。

---

## 5. 公式配置格式

```yaml
formula_version: v1
rounding:
  default_scale: 2
  default_mode: HALF_UP
  intermediate_scale: 6

items:
  - item_code: base_salary
    item_name: 基本工资
    item_type: input
    data_type: money
    source_field: base_salary
    required: true
    default_value: null
    order: 10
    rounding: false

  - item_code: performance_bonus
    item_name: 绩效奖金
    item_type: add
    data_type: money
    expression: "if_null(performance_bonus, 0)"
    dependencies: [performance_bonus]
    required: false
    order: 20

  - item_code: allowance_total
    item_name: 补贴合计
    item_type: add
    data_type: money
    expression: "sum_values(meal_allowance, traffic_allowance, communication_allowance)"
    dependencies: [meal_allowance, traffic_allowance, communication_allowance]
    required: false
    order: 30

  - item_code: gross_salary
    item_name: 应发工资
    item_type: intermediate
    data_type: money
    expression: "base_salary + performance_bonus + allowance_total - attendance_deduction"
    dependencies: [base_salary, performance_bonus, allowance_total, attendance_deduction]
    required: true
    order: 100

  - item_code: deduction_total
    item_name: 扣款合计
    item_type: intermediate
    data_type: money
    expression: "other_deduction + social_security_personal + housing_fund_personal"
    dependencies: [other_deduction, social_security_personal, housing_fund_personal]
    required: false
    order: 110

  - item_code: net_salary
    item_name: 实发工资
    item_type: final
    data_type: money
    expression: "gross_salary - deduction_total"
    dependencies: [gross_salary, deduction_total]
    required: true
    order: 200
    rounding:
      scale: 2
      mode: HALF_UP
```

---

## 6. 表达式能力

### 6.1 支持运算符

| 运算符 | 说明 |
|---|---|
| `+` | 加法 |
| `-` | 减法 |
| `*` | 乘法 |
| `/` | 除法 |
| `()` | 分组 |
| `>` `<` `>=` `<=` `==` `!=` | 比较 |

### 6.2 支持函数

| 函数 | 说明 | 示例 |
|---|---|---|
| `if_null(value, default)` | 空值默认 | `if_null(bonus, 0)` |
| `sum_values(a,b,c)` | 合计，空值按 0 | `sum_values(a,b,c)` |
| `max_value(a,b)` | 最大值 | `max_value(x, 0)` |
| `min_value(a,b)` | 最小值 | `min_value(x, 10000)` |
| `round_money(value, scale)` | 金额舍入 | `round_money(x, 2)` |
| `case_when(condition, a, b)` | 条件选择 | `case_when(days > 0, a, b)` |

### 6.3 禁止能力

公式表达式禁止：

- 任意 Python 代码；
- 文件读写；
- 网络请求；
- import；
- eval/exec；
- 调用未注册函数。

实现建议：使用安全表达式解析器，或基于 AST 白名单解析，不得直接 `eval` 用户配置。

---

## 7. 计算顺序

公式项通过 `order` 排序执行。

规则：

1. `order` 小的先计算；
2. 公式依赖的字段必须已经存在；
3. 如果依赖另一个工资项，该工资项必须先计算；
4. 检测到循环依赖时公式配置无效；
5. 同一 `item_code` 不允许重复。

示例：

```text
base_salary/order=10
performance_bonus/order=20
allowance_total/order=30
gross_salary/order=100
deduction_total/order=110
net_salary/order=200
```

---

## 8. 精度与舍入

### 8.1 金额类型

后端统一使用 Decimal。

禁止：

```python
float_salary = 0.1 + 0.2
```

推荐：

```python
Decimal("0.10") + Decimal("0.20")
```

### 8.2 舍入规则

| 场景 | 规则 |
|---|---|
| 中间计算 | 保留 6 位小数，不强制展示 |
| 最终工资项 | 保留 2 位小数 |
| 导出 Excel | 保留 2 位小数 |
| 默认舍入 | HALF_UP，四舍五入 |
| 除法 | 必须指定 scale |

### 8.3 配置示例

```yaml
rounding:
  intermediate_scale: 6
  final_scale: 2
  mode: HALF_UP
```

---

## 9. 空值处理

| 字段情况 | 处理 |
|---|---|
| required=true 且为空 | BLOCK，禁止计算 |
| required=false 且为空 | 按公式 `if_null` 处理 |
| 金额字段空字符串 | null |
| `-`、`—` | null |
| 非法金额 | BLOCK |

---

## 10. 计算前校验

计算前必须校验：

1. 无 OPEN 状态的 BLOCK 异常；
2. 公式配置格式正确；
3. 所有 `source_field` 在字段配置中存在；
4. 所有依赖字段存在；
5. 无循环依赖；
6. 必填字段不为空；
7. 金额字段能转换为 Decimal。

任一失败，计算接口返回错误。

---

## 11. 计算输出结构

```json
{
  "salary_run_id": "run_001",
  "employee_ref_id": "emp_001",
  "employee_name": "张三",
  "calc_version": 1,
  "items": [
    {
      "item_code": "gross_salary",
      "item_name": "应发工资",
      "amount": "9200.00",
      "formula": "base_salary + performance_bonus + allowance_total - attendance_deduction",
      "inputs": [
        {
          "field_code": "base_salary",
          "value": "8000.00",
          "source": "7月工资表.xlsx / 工资表 / 第12行 / 基本工资"
        },
        {
          "field_code": "performance_bonus",
          "value": "1000.00",
          "source": "7月奖金表.xlsx / 奖金 / 第12行 / 绩效"
        }
      ]
    }
  ],
  "final": {
    "net_salary": "8500.00"
  }
}
```

---

## 12. 计算解释模板

示例解释：

```text
张三本次实发工资为 8500.00 元。

应发工资 = 基本工资 8000.00 + 绩效奖金 1000.00 + 补贴合计 200.00 - 考勤扣款 0.00 = 9200.00 元。
扣款合计 = 其他扣款 100.00 + 社保个人扣款 400.00 + 公积金个人扣款 200.00 = 700.00 元。
实发工资 = 应发工资 9200.00 - 扣款合计 700.00 = 8500.00 元。

其中基本工资来自：7月工资表.xlsx / 工资表 / 第12行 / 基本工资。
绩效奖金来自：7月奖金表.xlsx / 奖金 / 第12行 / 绩效。
```

---

## 13. 公式测试用例要求

每个公式配置必须至少覆盖：

1. 正常计算；
2. 空值默认；
3. 必填字段缺失；
4. 金额非法；
5. 负数场景；
6. 舍入场景；
7. 极大金额；
8. 依赖字段缺失；
9. 循环依赖检测。

---

## 14. 验收标准

1. 公式来自配置文件；
2. 禁止直接使用 Python eval；
3. 金额使用 Decimal；
4. 最终工资保留 2 位小数；
5. BLOCK 异常存在时禁止计算；
6. 每个工资项保存计算 trace；
7. 每个输入字段可以追溯来源；
8. 公式配置错误时能给出明确错误；
9. 重新计算生成新的计算版本。
