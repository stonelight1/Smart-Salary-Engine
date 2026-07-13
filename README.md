# Smart Salary Engine (SSE)

智能薪资数据整理与工资核算平台。

## 项目定位

SSE 是 HR 的 **Excel 工资核算整理台**，不是人事系统。系统不替代 HR、OA、ERP、考勤、社保、个税或银行发薪系统，而是解决 HR 在工资核算前后最痛苦的部分：

- 多份 Excel 数据来源不统一
- Sheet、列名、字段格式不稳定
- 人工复制粘贴容易出错
- 补充数据反复导入，来源难追溯
- 工资计算过程难解释
- 发薪前异常难集中检查

## 项目特性

- 前后端分离，支持本地开发和 Docker 部署
- 后端基于 FastAPI，启动时自动加载 YAML 配置、初始化 SQLite 数据库
- 前端基于 Vue 3 + TypeScript + Vite + Element Plus
- 上传、导出、数据目录已按项目约定拆分，便于后续扩展

## 环境要求

- Python 3.13+
- Node.js 20+
- `uv`
- `npm`

## 配置说明

项目根目录已提供 [.env.sample](./.env.sample)，首次启动前可以复制为 `.env` 并按需调整：

- `VITE_API_BASE`：前端调用后端 API 的基础地址
- `SSE_DB_PATH`：数据库文件路径，默认指向 `data/sse.db`
- `SSE_MAX_UPLOAD_MB`：上传文件大小上限

说明：

- 后端启动时会自动加载 `config/` 下的 YAML 文件
- SQLite 数据库默认写入 `data/sse.db`
- `uploads/`、`exports/`、`data/` 会作为运行时目录使用

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus |
| 后端 | Python 3.13 + FastAPI + SQLAlchemy + Pydantic |
| 数据库 | SQLite（MVP）/ PostgreSQL（后续） |
| Excel | OpenPyXL + Pandas |
| 金额 | Decimal（禁止 float） |

## 项目结构

```
salary-system/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # 路由层
│   │   ├── core/      # 配置、异常、日志
│   │   ├── db/        # 数据库连接
│   │   ├── models/    # ORM 模型
│   │   ├── schemas/   # Pydantic DTO
│   │   ├── services/  # 业务服务
│   │   └── engines/   # 核心引擎
│   └── tests/
├── frontend/          # Vue 3 前端
│   └── src/
├── config/            # YAML 配置文件
├── docs/              # 项目文档
├── uploads/           # 上传文件存储
└── exports/           # 导出文件存储
```

## 开发顺序

1. 后端基础 + 数据库 + 配置加载
2. Excel Importer + Sheet/Column Mapper
3. Data Pool + 来源追踪
4. Check Engine + 异常处理
5. Calculate Engine + Formula Trace
6. Explain + Export
7. 前端完整流程串联
8. 测试、打磨、部署

## 本地启动

### 后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 构建检查

```bash
cd frontend
npm run build
```

## Docker 启动

仓库根目录已提供 `docker-compose.yml`，可直接启动前后端：

```bash
docker compose up --build
```

- 后端：`http://localhost:8000`
- 前端：`http://localhost`

## 核心原则

- **Excel 是唯一业务数据来源** — 系统不凭空创建工资业务数据
- **原始文件不可变** — 只读保存，导出时复制模板
- **过程可追溯** — 字段来源、异常处理、公式计算全留痕
- **规则可配置** — Sheet 识别、字段映射、检查、公式、导出列不硬编码
- **金额使用 Decimal** — 禁止 float 计算
- **BLOCK 阻断** — 严重异常未处理时禁止工资计算
