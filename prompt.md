# 项目开发任务：通用智能体开发平台（Mini-Agent Platform）

## 一、项目目标

请设计并实现一个通用、模块化、可扩展的 AI Agent 开发平台，项目暂定名称为 Mini-Agent Platform。

平台采用前后端分离架构，包含两个主要交互端：

1. **用户端：微信小程序**
   - 用户通过微信小程序访问 AI 智能体。
   - 支持多轮 AI 对话、流式输出、历史会话管理、文件上传和知识库问答。
   - 支持不同业务场景的智能体切换。
   - 支持 AI 返回文本、Markdown、表格、图片和结构化结果。

2. **管理员端：Web 管理后台**
   - 管理员通过 Web 页面管理智能体、配置大模型 API Key、管理知识库、配置 Prompt 和管理用户。
   - 可以自主创建多个智能体，并为不同智能体配置独立的模型、知识库、系统提示词和参数。
   - 可以通过上传文档构建私有知识库。
   - 无需修改后端代码，即可通过管理后台创建和发布不同业务场景的 AI 智能体。

项目的核心目标是构建一个可配置、可扩展、可复用的通用智能体开发框架，而不是单一的 AI 聊天应用。

---

## 二、技术架构与技术选型

采用前后端分离、模块化、插件化架构。

### 1. 微信小程序前端

技术要求：
- 原生微信小程序开发。
- JavaScript。
- WXML + WXSS。
- 使用模块化组件设计。
- 支持微信小程序登录。
- 支持流式 AI 对话。
- 支持 Markdown 消息渲染。
- 支持文件和图片上传。
- 支持多智能体切换。

前端需要封装通用组件：

- AgentChat：智能体聊天界面。
- MessageList：消息列表。
- MessageRenderer：多类型消息渲染。
- MarkdownRenderer：Markdown 内容渲染。
- AgentSelector：智能体选择。
- FileUploader：文件上传。
- KnowledgeResult：知识库检索结果。
- FeedbackBar：用户反馈。
- ChatHistory：历史会话。
- LoadingIndicator：AI 生成状态。

聊天消息采用统一的数据协议，支持 text、markdown、image、table、card、file、error 等消息类型。

### 2. Web 管理后台

建议采用：
- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Axios
- Vue Router

管理后台采用现代化 Dashboard 布局，提供侧边栏导航、数据概览、配置表单、数据表格和详情页面。

主要菜单：

1. 系统概览
2. 智能体管理
3. 大模型配置
4. 知识库管理
5. 文档管理
6. Prompt 管理
7. 会话管理
8. 用户管理
9. 插件与工具管理
10. 系统设置
11. 调用日志与统计

### 3. 后端服务

推荐技术：
- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- Pydantic
- MySQL 8
- Redis
- Celery（异步任务）
- LangChain 或 LangGraph（可选，用于 Agent 和 RAG 编排）

后端采用模块化设计，业务模块之间保持低耦合。

建议目录：

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── agents.py
│   │   ├── models.py
│   │   ├── knowledge.py
│   │   ├── documents.py
│   │   ├── chat.py
│   │   ├── conversations.py
│   │   ├── users.py
│   │   └── logs.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── agent/
│   │   ├── runtime.py
│   │   ├── prompt_manager.py
│   │   ├── memory_manager.py
│   │   └── tool_manager.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   └── provider_manager.py
│   ├── rag/
│   │   ├── document_parser.py
│   │   ├── text_splitter.py
│   │   ├── embedding.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   └── pipeline.py
│   ├── tasks/
│   └── utils/
├── migrations/
├── tests/
├── requirements.txt
└── Dockerfile
```

---

## 三、大模型接入模块（重点）

采用统一的 OpenAI API 兼容接口。

管理员可以在 Web 管理后台添加、修改和测试大模型配置。

每个模型配置包含：

- 模型名称。
- Provider 名称。
- API Base URL。
- API Key。
- Chat Model。
- Embedding Model。
- Temperature。
- Max Tokens。
- 是否启用。
- 是否设置为默认模型。

需要兼容以下模型服务：

- OpenAI
- DeepSeek
- Moonshot AI（Kimi）
- Qwen
- 其他支持 OpenAI Compatible API 的模型服务。

模型配置示例：

```json
{
  "provider": "deepseek",
  "name": "DeepSeek Chat",
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "ADMIN_CONFIGURED_API_KEY",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "enabled": true
}
```

实现统一 LLM Provider 接口：

```python
class BaseLLMProvider:

    def chat(self, messages, **kwargs):
        raise NotImplementedError

    def stream_chat(self, messages, **kwargs):
        raise NotImplementedError

    def embeddings(self, texts, **kwargs):
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError
```

优先使用官方 OpenAI Python SDK，通过 base_url 配置不同的模型服务商。

要求：

1. 不同智能体可以绑定不同模型。
2. 支持管理员动态切换模型。
3. 支持流式和非流式调用。
4. API Key 必须在服务端加密保存。
5. API Key 不能返回给微信小程序或浏览器前端。
6. 支持模型连接测试。
7. 记录 Token 消耗和模型调用日志。
8. 支持请求超时、错误重试和异常处理。
9. Chat Model 和 Embedding Model 可以分别配置。
10. 模型配置发生变化后无需修改业务代码。

---

## 四、RAG 知识库模块（核心功能）

平台必须实现完整的 RAG 知识库管理功能。

管理员可以在 Web 管理后台创建和管理多个独立知识库。

### 1. 知识库管理

每个知识库包含：

- 知识库名称。
- 知识库描述。
- 知识库分类。
- Embedding 模型配置。
- 向量数据库配置。
- 文本切片参数。
- 检索参数。
- 创建时间。
- 知识库状态。

支持创建多个知识库，一个智能体可以关联多个知识库。

### 2. 文档上传

支持以下文件：

- PDF
- DOCX
- TXT
- Markdown
- HTML
- CSV

管理员可以：
- 上传单个或多个文件。
- 删除文件。
- 查看文件解析状态。
- 查看文档切片结果。
- 重新解析文档。
- 删除指定文档的向量数据。
- 查看文档处理失败原因。

### 3. 文档处理 Pipeline

实现标准 RAG 文档处理流程：

```text
上传文档
    |
    v
文件存储
    |
    v
文档解析
    |
    v
文本清洗
    |
    v
文本切片 Chunking
    |
    v
Embedding 向量化
    |
    v
向量数据库存储
    |
    v
知识库构建完成
```

文档处理必须使用异步任务，避免长时间阻塞 HTTP 请求。

### 4. 向量数据库

优先使用 Qdrant 或 Chroma，封装统一 VectorStore 接口，避免业务代码依赖某个具体向量数据库。

支持：
- 向量插入。
- 向量删除。
- 相似度检索。
- Metadata 过滤。
- Top-K 检索。
- 相似度阈值过滤。

每个 Chunk 必须保存：
- chunk_id
- document_id
- knowledge_base_id
- content
- embedding
- metadata
- page_number（适用时）

### 5. RAG 检索生成

实现以下完整流程：

```text
用户问题
    |
    v
问题预处理
    |
    v
Embedding
    |
    v
知识库向量检索
    |
    v
Top-K 结果
    |
    v
可选 Rerank
    |
    v
构建 Knowledge Context
    |
    v
组合 System Prompt
    |
    v
调用 LLM
    |
    v
生成回答
    |
    v
返回答案和引用来源
```

要求：

- 支持知识库检索开关。
- 支持多个知识库联合检索。
- 支持 Top-K 和相似度阈值配置。
- 支持返回引用文档名称。
- 支持显示原文片段。
- 支持检索结果溯源。
- 当知识库没有相关内容时，允许配置拒答策略。
- 区分模型自身知识和知识库检索结果。

---

## 五、智能体管理模块

管理员可以通过 Web 后台创建不同类型的智能体。

每个智能体具有以下配置：

```json
{
  "name": "科研助手",
  "description": "科研知识问答助手",
  "system_prompt": "你是一个专业的科研助手",
  "llm_config_id": 1,
  "knowledge_base_ids": [1, 2],
  "temperature": 0.3,
  "enable_rag": true,
  "enable_memory": true,
  "enable_tools": false,
  "status": "published"
}
```

功能包括：

1. 创建智能体。
2. 编辑智能体。
3. 删除智能体。
4. 发布和下线智能体。
5. 配置智能体头像和描述。
6. 配置系统提示词。
7. 绑定模型。
8. 绑定一个或多个知识库。
9. 配置 RAG 参数。
10. 配置上下文记忆。
11. 配置欢迎语和推荐问题。
12. 配置用户访问权限。

微信小程序只展示已发布且用户有权访问的智能体。

---

## 六、AI 对话模块

微信小程序实现统一的 AI 对话入口。

主要功能：

1. 智能体选择。
2. 创建新会话。
3. 多轮对话。
4. 历史会话列表。
5. 删除会话。
6. 消息流式输出。
7. Markdown 渲染。
8. 代码块展示。
9. 图片上传。
10. 文件上传。
11. 停止生成。
12. 重新生成。
13. 复制回答。
14. 点赞和点踩。
15. RAG 引用来源展示。

每条消息至少保存：

- message_id
- conversation_id
- role
- content
- message_type
- token_usage
- created_at

多轮对话必须正确组织 system、user、assistant 等标准消息角色。

上下文需要支持最大 Token 限制，并能够通过历史消息截断或摘要压缩控制长度。

流式输出优先采用 SSE 或其他兼容微信小程序网络能力的实现方式，明确处理连接中断、客户端取消、超时和重新连接。

---

## 七、用户与权限管理

### 用户端

- 微信登录。
- 用户基本信息。
- 用户会话管理。
- 智能体访问。
- 使用量统计。

### 管理端

- 管理员账号登录。
- 管理员角色管理。
- 用户列表。
- 用户状态管理。
- 智能体访问权限。
- 知识库访问权限。
- 操作日志。

必须进行后端权限校验，不能只依赖前端隐藏按钮。

---

## 八、数据库设计

使用 MySQL，设计规范化数据库结构。

至少包括以下数据表：

1. admin_users：管理员。
2. users：微信用户。
3. llm_configs：大模型配置。
4. agents：智能体。
5. agent_knowledge_bases：智能体与知识库关联。
6. knowledge_bases：知识库。
7. documents：知识库文档。
8. document_chunks：文档切片元数据。
9. conversations：会话。
10. messages：消息。
11. agent_prompts：提示词。
12. api_logs：API 调用日志。
13. usage_statistics：使用统计。
14. user_agent_permissions：用户智能体权限。

数据库设计需要：
- 主键。
- 外键或逻辑关联。
- 创建和更新时间。
- 必要索引。
- 软删除机制（适用时）。

向量数据不必直接存储在 MySQL 中，可以保存在 Qdrant 等向量数据库中，MySQL 保存对应的元数据和关联关系。

---

## 九、API 接口设计

采用 RESTful API。

统一接口前缀：

```text
/api/v1/
```

至少实现：

### 认证接口

```text
POST /auth/admin/login
POST /auth/wechat/login
GET  /auth/me
```

### 模型管理接口

```text
GET    /models
POST   /models
PUT    /models/{id}
DELETE /models/{id}
POST   /models/{id}/test
```

### 智能体管理接口

```text
GET    /agents
POST   /agents
GET    /agents/{id}
PUT    /agents/{id}
DELETE /agents/{id}
POST   /agents/{id}/publish
```

### 知识库接口

```text
GET    /knowledge-bases
POST   /knowledge-bases
GET    /knowledge-bases/{id}
PUT    /knowledge-bases/{id}
DELETE /knowledge-bases/{id}
POST   /knowledge-bases/{id}/documents
GET    /knowledge-bases/{id}/documents
POST   /knowledge-bases/{id}/rebuild
```

### 对话接口

```text
POST /chat/completions
POST /chat/stream
GET  /conversations
GET  /conversations/{id}/messages
DELETE /conversations/{id}
```

所有接口需要实现输入校验、异常处理、权限控制和统一响应格式。

---

## 十、UI 与交互设计要求

### 微信小程序

采用简洁、现代化的 AI 助手界面。

首页：
- 平台名称和欢迎语。
- 智能体列表。
- 推荐智能体。
- 最近会话。
- 快捷提问入口。

聊天页面：
- 顶部智能体名称。
- 消息对话区域。
- Markdown 消息展示。
- 输入框。
- 发送按钮。
- 文件上传入口。
- 停止生成按钮。
- 引用来源折叠面板。

### Web 管理后台

采用专业 SaaS Dashboard 风格。

首页显示：
- 智能体数量。
- 模型配置数量。
- 知识库数量。
- 文档数量。
- 用户数量。
- 今日调用次数。
- Token 消耗统计。
- 最近调用日志。

智能体配置页面应采用清晰的分区表单：

- 基本信息。
- 模型配置。
- Prompt 配置。
- 知识库配置。
- 记忆配置。
- 工具配置。
- 发布配置。

知识库管理页面应支持文件拖拽上传、处理进度、文档列表和检索测试。

---

## 十一、安全性要求

必须重点实现：

1. API Key 使用服务端加密存储。
2. API Key 不允许通过 API 返回给前端。
3. 管理员密码采用安全哈希算法保存。
4. JWT 身份认证。
5. 用户和管理员权限隔离。
6. 上传文件类型和大小校验。
7. 文件解析过程进行安全限制。
8. 防止 SQL 注入。
9. 防止越权访问其他用户的会话和知识库。
10. 对 RAG 文档中的指令性内容进行不可信数据处理，不能将其作为系统指令执行。
11. 对工具调用增加权限校验和参数校验。
12. 记录关键操作审计日志。
13. 对 API 接口进行限流。
14. 避免在日志中记录 API Key 和敏感信息。

---

## 十二、开发实施要求

请按照以下顺序实施项目。

### 第一阶段：项目基础建设

1. 创建完整项目目录。
2. 搭建 FastAPI 后端。
3. 搭建 Vue 3 管理后台。
4. 创建微信小程序项目。
5. 配置 MySQL 和 Redis。
6. 创建数据库模型和初始化脚本。
7. 实现管理员登录。

### 第二阶段：核心 AI 功能

1. 实现 OpenAI Compatible LLM Provider。
2. 实现模型配置管理。
3. 实现模型连接测试。
4. 实现智能体 CRUD。
5. 实现 Prompt 管理。
6. 实现多轮聊天。
7. 实现流式响应。

### 第三阶段：RAG 功能

1. 实现知识库 CRUD。
2. 实现文档上传。
3. 实现文档解析。
4. 实现文本切片。
5. 实现 Embedding。
6. 实现向量数据库存储。
7. 实现向量检索。
8. 实现 RAG 对话。
9. 实现引用来源展示。
10. 实现异步文档处理。

### 第四阶段：微信小程序

1. 实现微信用户登录。
2. 实现智能体列表。
3. 实现 AI 聊天。
4. 实现流式输出。
5. 实现历史会话。
6. 实现文件上传。
7. 实现知识库问答。
8. 实现多类型消息渲染。

### 第五阶段：测试和部署

1. 编写核心单元测试。
2. 编写 API 集成测试。
3. 测试不同模型服务商。
4. 测试 RAG 文档处理流程。
5. 测试多轮对话。
6. 测试用户权限隔离。
7. 编写 Docker Compose。
8. 编写部署文档。
9. 提供环境变量配置示例。
10. 提供数据库初始化和升级脚本。

---

## 十三、代码质量与交付标准

请严格遵守以下要求：

1. 所有模块采用清晰的分层架构。
2. 避免将所有业务代码写在单个文件中。
3. 核心功能必须真正实现，不允许只创建空页面或 Mock 接口。
4. 对暂时无法完成的功能明确标记 TODO，不得伪装成已经实现。
5. 使用统一的异常处理和日志体系。
6. 核心接口提供完整的类型定义。
7. 后端 API 提供 Swagger 文档。
8. 提供数据库迁移脚本。
9. 提供 `.env.example`。
10. 提供 README.md。
11. 提供 Docker Compose 部署方案。
12. 所有前端页面需要有实际可用的交互。
13. 关键业务流程必须能够端到端运行。
14. 提供至少一个默认智能体和一个演示知识库的初始化方案。

### 最终验收场景

必须能够完整实现以下业务流程：

**管理员操作：**

1. 登录 Web 管理后台。
2. 添加 DeepSeek 或 Kimi 的 API Key。
3. 测试模型连接。
4. 创建一个新的智能体。
5. 配置智能体的 System Prompt。
6. 创建一个知识库。
7. 上传 PDF 或 Word 文档。
8. 等待文档解析和向量化完成。
9. 将知识库关联到智能体。
10. 发布智能体。

**用户操作：**

1. 打开微信小程序。
2. 登录系统。
3. 选择管理员发布的智能体。
4. 输入问题。
5. 后端根据智能体配置调用对应的大模型。
6. 自动检索关联知识库。
7. 将检索结果与用户问题组合。
8. 调用大模型生成回答。
9. 微信小程序流式显示回答。
10. 展示回答引用的知识库文档及相关原文。

最终要求：交付一个可以本地启动、可以配置真实 API Key、可以上传真实文档、可以进行真实 RAG 检索和 AI 对话的完整 MVP 系统。

**开发原则：先完成端到端可运行的 MVP，再逐步扩展插件系统、多智能体协作和可视化工作流。不要一开始过度设计。**