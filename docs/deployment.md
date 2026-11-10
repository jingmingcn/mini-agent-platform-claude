# 部署文档

## 1. 环境变量

复制 `backend/.env.example` 为 `backend/.env`，生产环境至少修改：

| 变量 | 说明 |
| --- | --- |
| `ENV` | `production` 时若 `SECRET_KEY` 仍为默认值，服务拒绝启动 |
| `SECRET_KEY` | JWT 签名密钥，`openssl rand -hex 32` |
| `ENCRYPTION_KEY` | API Key 加密用 Fernet 密钥。**设置后不要更换**，否则已保存的 API Key 无法解密 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 首次初始化创建的超级管理员 |
| `WECHAT_APPID` / `WECHAT_SECRET` | 小程序登录（code2session） |
| `WECHAT_DEV_LOGIN` | 生产必须为 `false` |
| `CORS_ORIGINS` | 管理后台域名（JSON 数组） |
| `CELERY_ENABLED` | 生产建议 `true`，需配合 `QDRANT_URL`（嵌入式 Qdrant 不能跨进程共享） |

## 2. Docker Compose

```bash
docker compose up -d --build
docker compose logs -f backend worker
```

- backend 容器启动时执行 `alembic upgrade head` 与幂等初始化脚本 `python -m app.scripts.init_db`。
- `admin` 容器为 nginx：静态资源 + 反代 `/api`、`/docs`。SSE 需要 `proxy_buffering off`（已配置）。
- 数据卷：`mysql_data`、`qdrant_data`、`uploads`。

## 3. 数据库初始化与升级

```bash
cd backend
alembic upgrade head                 # 建表 / 升级
python -m app.scripts.init_db        # 幂等初始化（管理员、演示知识库、默认智能体）
alembic revision --autogenerate -m "describe change"   # 修改模型后生成新迁移
alembic downgrade -1                 # 回滚一个版本
```

## 4. HTTPS 与小程序合法域名

微信小程序正式环境要求 HTTPS 且域名在小程序后台「开发管理 → 服务器域名」中登记：
- `request 合法域名`：API 域名（流式对话也走 request）
- `uploadFile 合法域名`、`downloadFile 合法域名`：同 API 域名

在外层负载均衡 / nginx 上终止 TLS 时，对 `/api/v1/chat/stream` 关闭缓冲、加大 `proxy_read_timeout`，否则流式输出会被攒成整块返回。修改 `miniprogram/config.js` 中的 `API_BASE`，以及 `project.config.json` 中的 `appid`。

## 5. 扩容

- backend 无状态，可水平扩展（`WEB_CONCURRENCY` 控制 uvicorn workers）；限流与停止生成标志在配置 Redis 后跨实例生效。
- worker 可独立扩容：`docker compose up -d --scale worker=3`。
- 上传文件存于共享卷 `uploads`；多机部署需改为 NFS / 对象存储（TODO）。

## 6. 模型服务商参考

| Provider | Base URL | Chat Model 示例 | Embedding |
| --- | --- | --- | --- |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini | text-embedding-3-small |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat | 无 |
| Moonshot (Kimi) | https://api.moonshot.cn/v1 | moonshot-v1-8k | 无 |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus | text-embedding-v3 |
| SiliconFlow | https://api.siliconflow.cn/v1 | deepseek-ai/DeepSeek-V3 | BAAI/bge-m3 |
