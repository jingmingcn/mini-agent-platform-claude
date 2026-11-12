# Mini-Agent Android 客户端

Mini-Agent Platform 的 Android 原生客户端，直接对接后端 RESTful API（`/api/v1/`），
复用平台的多智能体、流式 AI 对话、RAG 知识库问答、历史会话与文件上传能力。

与微信小程序端对齐的核心流程：**登录 → 选择智能体 → 发送消息 → 接收流式回复（打字机 + RAG 引用）→ 管理历史会话**。

---

## 技术栈

| 关注点 | 选型 |
| --- | --- |
| 语言 | Kotlin |
| UI | Jetpack Compose + Material 3（支持暗黑模式） |
| 架构 | MVVM（ViewModel + StateFlow + Repository） |
| 网络 | Retrofit + OkHttp |
| 流式 | OkHttp 原生流 + Kotlin Flow 解析 SSE（`text/event-stream`） |
| 异步 | Kotlin Coroutines + Flow |
| 依赖注入 | Hilt |
| 本地存储 | Jetpack DataStore（Token / Base URL / 设备标识） |
| 序列化 | kotlinx.serialization |
| Markdown | compose-markdown（Markwon，支持代码块/表格/列表） |
| 图片 | Coil |

最低支持 Android 8.0（API 26），`targetSdk 36`，`compileSdk 37`。

> **已验证的构建工具链**（本机实际编译通过，产物 `app-debug.apk`）：
> AGP 9.4.0 · Gradle 9.6 · Kotlin 2.2.10（随 AGP 内置）· KSP 2.2.10-2.0.2 · Hilt 2.59.2 · JDK 17+。
> AGP 9 起 Kotlin 支持已内置，故未单独应用 `kotlin-android` 插件；
> `gradle.properties` 中的 `android.disallowKotlinSourceSets=false` 用于让 KSP 正常注册生成源目录。

---

## 目录结构

```
app/src/main/java/com/miniagent/app/
├─ MiniAgentApp.kt            # Hilt Application
├─ MainActivity.kt           # 单 Activity 入口
├─ core/
│  ├─ config/SettingsStore   # DataStore：token / baseUrl / 设备 id / 缓存资料
│  ├─ designsystem/          # 主题、配色、排版（含暗黑模式）
│  ├─ network/               # 统一响应封装、Retrofit ApiService、SSE 客户端、拦截器
│  └─ ui/                    # Loading / Empty / Error / Avatar 等通用组件
├─ data/
│  ├─ model/Dtos.kt          # 与后端对齐的数据模型
│  └─ repository/            # Auth / Agent / Conversation / Chat / File 仓库
├─ di/NetworkModule.kt       # OkHttp / 拦截器 / SSE client 提供
├─ feature/
│  ├─ auth/                  # 登录
│  ├─ agents/                # 首页：智能体列表、搜索、分类
│  ├─ chat/                  # 流式对话（核心）、Markdown、RAG 引用、附件
│  ├─ history/               # 历史会话：列表、删除、重命名
│  └─ profile/               # 个人中心、服务环境切换、退出登录
└─ navigation/               # 路由、底部导航、401 强制登出
```

---

## 配置后端地址（Base URL）

**唯一的编译期配置点**在 `app/build.gradle.kts` 的 `DEFAULT_BASE_URL`：

```kotlin
buildConfigField("String", "DEFAULT_BASE_URL", "\"http://10.0.2.2:8000/api/v1\"")
```

| 运行环境 | Base URL |
| --- | --- |
| Android 模拟器（访问本机后端） | `http://10.0.2.2:8000/api/v1` |
| 真机（同一局域网） | `http://<你电脑的局域网IP>:8000/api/v1` |
| 生产 | `https://your-domain.com/api/v1` |

也可以在 App 运行时修改：**个人中心 → 服务环境设置**（存入 DataStore，重新登录后生效）。
登录页也提供了 Base URL 输入框。

> 明文 HTTP 仅对本地开发地址放行，见 `res/xml/network_security_config.xml`；
> 真机测试其它局域网 IP 时请把 IP 加进该文件，或改用 HTTPS。

---

## 登录说明（重要）

后端的终端用户（`user` 身份）登录通道是 `POST /auth/wechat/login`；
**聊天相关接口只接受 `user` 身份，管理员账号不可用于对话**。

本 App 采用**设备身份登录**：以每台设备生成的稳定 id 作为 `code` 与 `dev_openid`
调用 `/auth/wechat/login`。这要求后端开启开发登录：

```env
# backend/.env
WECHAT_DEV_LOGIN=true
# 且不要配置 WECHAT_APPID / WECHAT_SECRET
```

生产环境接入真实微信/手机号登录时，只需替换
`data/repository/AuthRepository.login()` 里的 `code`（改为微信 Open SDK 拿到的 `wx.login` code）即可，
其余流程不变。

---

## 本地运行

1. 启动后端（示例，使用本地 SQLite 快速起步）：
   ```bash
   cd backend
   cp .env.example .env
   # 编辑 .env：设置 DATABASE_URL=sqlite:///./data/dev.db 、WECHAT_DEV_LOGIN=true
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   确认 `http://127.0.0.1:8000/docs` 可访问，并在管理后台创建并**发布**至少一个
   `access_level=public` 的智能体（配置好可用的大模型）。

2. 打开 Android 工程：用 Android Studio 打开本 `android/` 目录。
   首次打开会提示生成 Gradle Wrapper / 同步依赖。
   （命令行用户可在装有 Gradle 的环境执行 `gradle wrapper` 生成 wrapper 后再 `./gradlew assembleDebug`。）

3. 需要本地 Android SDK：Android Studio 会自动写入 `local.properties` 的 `sdk.dir`，
   命令行构建请设置 `ANDROID_HOME` 或手动创建 `local.properties`。

4. 运行到模拟器（默认 Base URL 已指向 `10.0.2.2:8000`）。

### 端到端验证路径

登录 → 首页选择已发布智能体 → 发送一条消息 → 观察打字机式流式回复 →
（若该智能体开启 RAG）展开「引用来源」查看文档片段 → 返回「会话」查看历史并可删除。

---

## 与后端接口对照

| 功能 | 接口 |
| --- | --- |
| 登录 | `POST /auth/wechat/login` |
| 当前身份 | `GET /auth/me` |
| 首页配置 | `GET /app/config` |
| 智能体列表 / 详情 | `GET /agents` · `GET /agents/{id}` |
| 会话列表 | `GET /conversations` |
| 会话消息 | `GET /conversations/{id}/messages` |
| 重命名 / 删除会话 | `PATCH` · `DELETE /conversations/{id}` |
| 点赞点踩 | `POST /messages/{id}/feedback` |
| 流式对话 | `POST /chat/stream`（SSE：`meta`/`citations`/`tool`/`delta`/`done`/`error`） |
| 停止生成 | `POST /chat/stop` |
| 文件上传 | `POST /files/upload` |

统一响应封装 `{code, message, data}`，`code=0` 为成功；
`401` 由拦截器捕获并触发强制登出回到登录页。

---

## 说明

- 工程结构完整、可用 Android Studio 直接打开构建；本仓库未附带 Gradle Wrapper 的
  二进制 `gradle-wrapper.jar`，首次用 Android Studio 打开或执行 `gradle wrapper` 即可补全。
- 停止生成：客户端断开流即被后端视为取消，已生成内容会保存为 `interrupted`。
- 流式滚动、键盘弹起（`imePadding`）、加载/空/异常兜底均已处理。
