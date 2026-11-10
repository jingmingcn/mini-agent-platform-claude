# Mini-Agent Platform

通用、模块化、可扩展的 AI 智能体开发平台（MVP）。管理员在 **Web 管理后台** 配置大模型、知识库与智能体并发布；用户在 **微信小程序** 中选择智能体，进行流式、多轮、带引用来源的 RAG 对话。

```
┌──────────────┐   SSE / REST   ┌────────────────────── FastAPI backend ───────────────────────┐
│ 微信小程序     │ ─────────────▶ │ api/ → services/ → agent/runtime (memory · RAG · tools · LLM) │
│ (原生 JS)     │                │                │            │                 │              │
└──────────────┘                │            MySQL 8      Qdrant (向量)    OpenAI 兼容 API      │
┌──────────────┐   REST         │                │                                            │
│ Vue3 管理后台  │ ─────────────▶ │  Redis (限流/取消) · Celery worker (文档解析→切片→向量化)     │
└──────────────┘                └──────────────────────────────────────────────────────────────┘
```

## 目录

```
backend/      FastAPI + SQLAlchemy 2 + Alembic + Celery + Qdrant
  app/api/        路由层（auth, models, agents, prompts, knowledge, documents, chat, conversations, files, users, logs, system）
  app/services/   业务服务
  app/agent/      runtime（一次对话的编排）, prompt_manager, memory_manager, tool_manager
  app/llm/        BaseLLMProvider / OpenAICompatibleProvider / provider_manager（构建 + 调用日志）
  app/rag/        document_parser, text_splitter, embedding, vector_store, retriever, pipeline
  app/tasks/      Celery app + 文档处理任务 + 调度器（可退化为进程内线程池）
  migrations/     Alembic 迁移
  tests/          单元 + API 集成测试（26 个）
admin/        Vue 3 + TS + Vite + Element Plus + Pinia + Axios + Vue Router
miniprogram/  原生微信小程序（10 个通用组件 + 4 个页面）
docs/         部署文档
docker-compose.yml
```

## 快速开始（本地开发，无需 Docker）

依赖：Python 3.11+、Node 18+；MySQL / Redis 可选（可用 SQLite + 内存降级）。

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

```bash
cp backend/.env.example backend/.env
```

最简模式编辑 `backend/.env`：`DATABASE_URL=sqlite:///./data/dev.db`、`REDIS_URL=`（留空）、`CELERY_ENABLED=false`。使用 MySQL 时保持默认 `DATABASE_URL` 并先建库 `CREATE DATABASE mini_agent CHARACTER SET utf8mb4;`。

```bash
cd backend && mkdir -p data && .venv/bin/alembic upgrade head && .venv/bin/python -m app.scripts.init_db
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd admin && npm install && npm run dev
```

- 管理后台：http://localhost:5173 （默认账号 `admin` / `Admin@123456`，在 `.env` 中修改）
- Swagger：http://localhost:8000/docs
- 小程序：用微信开发者工具导入 `miniprogram/`，在「详情 → 本地设置」勾选 **不校验合法域名**；`miniprogram/config.js` 中配置 `API_BASE`。未配置 `WECHAT_APPID` 时需在后端开启 `WECHAT_DEV_LOGIN=true`（仅开发）。

初始化脚本会创建：超级管理员、系统设置、**演示知识库「平台使用手册」**（离线 local-hash 向量化，开箱即可检索）、**默认智能体「通用助手」** 和 **RAG 智能体「平台助手」**（均已发布）。配置任意可用的 Chat 模型并设为默认后即可对话。

## Docker Compose 部署

```bash
cp backend/.env.example backend/.env
```

```bash
docker compose up -d --build
```

包含 MySQL 8、Redis、Qdrant、backend（启动时自动 `alembic upgrade head` + 初始化）、Celery worker、admin（nginx，反向代理 `/api` 且关闭 SSE 缓冲）。管理后台 http://localhost:8080 。详见 [docs/deployment.md](docs/deployment.md)。

## 验收流程

**管理员**：登录 → 大模型配置「新增模型」选 DeepSeek / Kimi，填 API Key → 「测试连接」→ 智能体管理新建智能体并填写 System Prompt → 知识库管理新建知识库（Embedding 选择带 Embedding Model 的配置，或留空用内置 local-hash）→ 拖拽上传 PDF / Word → 列表实时显示进度直至「已完成」，可查看切片与检索测试 → 在智能体「知识库配置」中关联 → 保存并发布。

**用户**：打开小程序自动 `wx.login` 登录 → 首页选择智能体 → 提问 → 后端按智能体配置选模型、检索关联知识库、将片段作为不可信数据拼入 System Prompt → SSE 流式返回 → 回答下方「引用来源」面板展示文档名、页码、相似度与原文片段。

> ⚠️ DeepSeek 与 Kimi 目前没有公开 Embedding 接口。用它们做对话时，知识库的 Embedding 需另配一个带 Embedding 的模型配置（通义千问 `text-embedding-v3`、OpenAI `text-embedding-3-small`、SiliconFlow `BAAI/bge-m3` 等），或使用内置 local-hash（词法哈希，仅适合演示）。

## 核心设计

### 大模型接入
- `BaseLLMProvider` 定义 `chat / stream_chat / embeddings / test_connection`；`OpenAICompatibleProvider` 基于官方 `openai` SDK，通过 `base_url` 接入 OpenAI、DeepSeek、Moonshot、Qwen（compatible-mode）、SiliconFlow 等。
- 超时、重试（SDK 指数退避，可按配置设置）、错误码翻译为可读中文信息；流式请求带 `stream_options.include_usage`，服务端不支持时自动降级并估算 Token。
- 智能体可绑定任意模型，未绑定则使用默认模型；修改模型配置无需改业务代码。
- API Key：Fernet 加密入库，接口只返回 `****末四位`；日志统一经过脱敏过滤器。
- 每次调用写 `api_logs`（Token、耗时、状态、错误），并按天聚合到 `usage_statistics`。

### RAG
- 上传 → 存储（UUID 文件名）→ 解析（PDF 按页 / DOCX 含表格 / HTML 去脚本 / CSV 行转键值 / TXT·MD 自动识别编码）→ 清洗 → 递归中英文切片（chunk_size / overlap 可配）→ 批量 Embedding → Qdrant（每个知识库一个 collection，payload 含 chunk_id / document_id / knowledge_base_id / content / page_number / metadata）。MySQL `document_chunks` 保存切片元数据。
- 异步：`CELERY_ENABLED=true` 走 Celery；否则进程内线程池。文档状态 pending → processing（带进度与阶段）→ completed / failed（失败原因可见），支持重新解析、删除向量、整库重建。
- 检索：问题预处理 → 按 Embedding 配置分组只算一次向量 → 多知识库联合检索 → 阈值过滤 → 去重 → 可插拔 Reranker（默认直通）→ Top-K。
- 生成：知识片段以 `<knowledge><source id=n ...>` 包裹并转义分隔符，系统提示明确其为**不可信数据**、禁止执行其中指令、要求 `[n]` 标注并区分「知识库内容」与「模型通用知识」。无结果时按智能体策略：`fallback`（声明基于通用知识）或 `strict`（直接返回拒答话术，不调用模型）。

### 对话
- `POST /chat/stream` 返回 SSE：`meta`（会话/消息 ID）→ `citations` → `tool`* → `delta`* → `done` / `error`。校验错误（越权、未发布等）在流开始前以普通 JSON 错误返回。
- 客户端断开（含小程序 `requestTask.abort()`）→ 服务端中止上游请求，已生成内容保存为 `interrupted`；也可调用 `POST /chat/stop`（Redis 标志，支持多进程）。网络中断后小程序拉取服务端消息恢复会话。
- 多轮记忆：按条数与 Token 预算从最早消息开始截断，保证 user/assistant 成对。`regenerate` 软删除最后一轮回答并重算。
- 小程序使用 `wx.request({enableChunked:true})` + 自实现的增量 UTF-8 解码与 SSE 解析。

### 权限与安全
- JWT 分 `admin` / `user` 两种类型，互不可用；管理员角色 `super_admin / admin / viewer`（只读）。所有权限在后端依赖注入中校验。
- 用户只能访问自己的会话、附件（越权统一返回 404）；小程序只能看到「已发布 + 公开或已授权」的智能体，且看不到 System Prompt / 模型 / 知识库配置。
- bcrypt 密码；上传扩展名 + 大小 + 魔数校验、DOCX 解压体积检查、PDF 页数与文本量上限；ORM 参数化查询；工具调用白名单 + Pydantic 参数校验（计算器使用 AST 白名单，不使用 eval）；关键操作写 `audit_logs`（敏感字段打码）；Redis/内存固定窗口限流（聊天、登录单独限额）。

## 测试

```bash
cd backend && .venv/bin/python -m pytest -q
```

覆盖：加解密/脱敏、切片、六种格式解析、提示注入转义、工具校验、记忆截断、OpenAI 兼容协议（Mock HTTP：非流式、流式 usage、无 usage 估算、批量 Embedding、401/404/429/500 映射）、完整验收流程（模型→知识库→上传→检索→智能体→发布→小程序登录→流式 RAG 对话→多轮→重新生成→反馈→统计/审计）、跨用户隔离、受限智能体、严格拒答、只读角色。设置 `TEST_DATABASE_URL=mysql+pymysql://...` 可在 MySQL 上运行同一套测试。

## 已知限制 / TODO

- 图片消息：可上传并展示，但尚未以多模态输入传给视觉模型（会提示模型"用户上传了图片"）。
- 记忆压缩：目前为截断策略；`conversations.summary` 字段已预留，摘要压缩未实现。
- Rerank：提供 `BaseReranker` 接口，未接入具体 rerank 模型。
- 插件系统：内置 `get_current_time`、`calculator` 两个工具；动态插件 / HTTP 工具配置、多智能体协作、可视化工作流未实现。
- 扫描版 PDF 无 OCR。
- 用户头像仅本地展示，未上传到对象存储。
- 知识库访问权限通过「智能体访问权限」间接控制，没有单独的知识库级用户授权。
