# Mini-Agent 平台使用手册（演示知识库）

## 平台简介
Mini-Agent Platform 是一个通用、模块化的 AI 智能体开发平台。管理员可以在 Web 管理后台创建智能体、配置大模型、构建私有知识库，用户通过微信小程序与智能体对话。

## 如何添加大模型
1. 登录管理后台，进入「大模型配置」。
2. 点击「新增模型」，选择 Provider（OpenAI、DeepSeek、Moonshot Kimi、通义千问 Qwen 或其他 OpenAI 兼容服务）。
3. 填写 API Base URL、API Key、Chat Model，例如 DeepSeek 的 Base URL 为 https://api.deepseek.com/v1，模型为 deepseek-chat。
4. 点击「测试连接」，确认连接成功后保存。
API Key 在服务端使用 Fernet 对称加密保存，任何接口都不会把明文 API Key 返回给浏览器或小程序。

## 如何创建知识库
1. 进入「知识库管理」，点击「新建知识库」。
2. 选择 Embedding 模型。DeepSeek 和 Kimi 目前没有公开的 Embedding 接口，推荐使用通义千问 text-embedding-v3、OpenAI text-embedding-3-small 或 SiliconFlow 的 BAAI/bge-m3。若不选择，则使用内置的 local-hash 离线向量化（仅适合演示）。
3. 设置切片大小（默认 500 字）和重叠长度（默认 80 字）。
4. 上传 PDF、DOCX、TXT、Markdown、HTML、CSV 文件，系统会异步完成解析、清洗、切片、向量化和入库。

## 文档处理状态说明
- pending：已上传，等待处理。
- processing：正在解析或向量化，可以在列表中看到进度百分比。
- completed：处理完成，可以被检索。
- failed：处理失败，可在文档详情中查看失败原因，修复后点击「重新解析」。

## 智能体配置
每个智能体可以独立配置：系统提示词、绑定的模型、温度、关联的一个或多个知识库、检索 Top-K、相似度阈值、无结果时的拒答策略、上下文记忆条数、欢迎语和推荐问题。只有「已发布」状态的智能体才会出现在微信小程序中。访问权限设置为「受限」时，只有被授权的用户可以看到并使用该智能体。

## 拒答策略
- fallback（兜底回答）：知识库无相关内容时，模型可以使用自身知识回答，但必须声明"以下回答基于模型通用知识"。
- strict（严格拒答）：知识库无相关内容时，直接返回管理员配置的拒答话术，不调用大模型。

## 常见问题
问：小程序里看不到新建的智能体？
答：请确认智能体已经点击「发布」，并且访问权限为「公开」或者当前用户已被授权。

问：回答里的 [1] [2] 是什么？
答：这是引用标记，对应回答下方「引用来源」面板中的知识库文档片段，点击可以查看原文。

问：平台的技术栈是什么？
答：后端 FastAPI + SQLAlchemy + MySQL + Redis + Celery + Qdrant；管理后台 Vue 3 + TypeScript + Element Plus；用户端为原生微信小程序。
