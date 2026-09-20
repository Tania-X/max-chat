# MAX Chat — 类 ChatGPT 的全栈 AI 助手

**简体中文** | [English](README.en.md)

基于 **FastAPI + Google ADK + React** 的多用户 AI 对话应用，采用 **DDD 分层架构**，具备多模型切换、Session 隔离、长期记忆、用户画像、插件 / Skill / MCP 工具框架与全链路可观测性。

## 功能一览

| 模块 | 说明 |
|---|---|
| 用户体系 | 注册 / 登录（JWT），全部数据按用户隔离 |
| 对话 | 多会话管理、SSE 流式输出、Markdown / 代码高亮、停止生成 |
| 多模型 | Gemini（ADK 原生）+ OpenAI / Anthropic / DeepSeek 等（LiteLLM），界面可切换、可测连通性 |
| 记忆与画像 | 对话后自动抽取事实 / 偏好，注入后续对话上下文，支持查看 / 编辑 / 删除 |
| 插件 | `backend/plugins/` 目录约定式扫描，启停开关 + JSON 配置 + 热加载 |
| Skill | `backend/skills/` 指令模板技能，启停 + 配置 + 热加载 |
| MCP | 作为 MCP Client 接入外部 server（stdio / sse），工具自动发现注入，失败降级；stdio 默认关闭，需显式开启 |
| 可观测性 | 每条回复记录 TTFT、tok/s、prompt/completion tokens、成本折算；Trace 瀑布图 + 用量统计图表 |

## 业务定位与扩展点

MAX Chat 是类 ChatGPT 的多用户 AI 助手，核心业务域为：**对话体验、Agent 能力（记忆 / 画像 / 工具）、多模型接入、调用可观测性**。与核心域无关的功能（支付、社交流、内容运营等）不在本项目范围内；默认保持本地优先、零外部依赖（SQLite 即可运行）。

现阶段扩展点：

| 扩展点 | 方式 |
|---|---|
| 新模型提供商 | LiteLLM 适配，设置页配置即用 |
| 插件 | `backend/plugins/`，Python 函数自动转 FunctionTool |
| 技能 | `backend/skills/`，指令模板 + 可选工具集 |
| MCP 工具 | 设置页接入 stdio / sse server |
| 模型定价表 | `observability/infrastructure/pricing.py` |
| 新业务能力 | 按 DDD 新增限界上下文（domain/application/infrastructure/interfaces） |

## 目录结构

```
backend/                 # FastAPI 后端（DDD 六限界上下文）
  app/
    shared/              # 配置、安全、数据库、异常（共享内核）
    identity/            # BC：用户与认证
    conversation/        # BC：会话、消息、SSE 聊天
    agent_runtime/       # BC：ADK Agent 编排、多模型工厂
    memory/              # BC：记忆与画像
    capability/          # BC：插件 / Skill / MCP 统一工具源
    observability/       # BC：Trace、指标、成本
  plugins/time_plugin/   # 示例插件（获取当前时间）
  skills/code_review/    # 示例技能（代码审查）
frontend/                # React 18 + Vite 5 + TS + Tailwind
  src/pages/             # 登录 / 聊天 / 设置 / 用量统计
  src/components/        # 侧栏、消息列表、输入区、Trace 面板、设置 Tab
```

## Docker 快速启动（推荐）

单容器多阶段构建：Node 构建前端 → Python 托管 API 与静态页面；SQLite 持久化在命名卷。

```bash
cp backend/.env.example backend/.env   # 编辑填入模型 Key
docker compose up -d --build
# 访问 http://127.0.0.1:8000（默认仅绑定回环，见下方「安全默认值」）
```

## 启动方式

### 后端

```powershell
# 创建虚拟环境（位置随意，示例放在项目外的环境目录）
python -m venv $env:VENV_HOME\max-chat
$env:VENV_HOME\max-chat\Scripts\pip.exe install -r backend\requirements.lock.txt
cd backend
$env:VENV_HOME\max-chat\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

首次启动自动建表（`backend/data/app.db`）。

**配置模型 Key**：编辑 `backend/.env`，填入 `GOOGLE_API_KEY`（Gemini 兜底模型 + 记忆抽取用），或启动后在「设置 → 模型配置」界面添加任意提供商的 Key（Fernet 加密存储）。

**关于密钥**：`JWT_SECRET` 与 `FERNET_KEY` 留空即可——首次启动会自动生成强随机值并以 0600 权限写入 `backend/data/secrets.json`，随数据目录一起持久化；若曾使用过旧版本的公开默认值，启动时会自动替换并提示重新登录。

### 前端

```powershell
cd frontend
npm install   # 已安装可跳过
npm run dev   # http://localhost:5173，/api 已代理到 8000
```

## 自定义扩展

### 写一个插件

```
backend/plugins/my_plugin/
├── manifest.json   # {"name":"my_plugin","description":"...","entry":"entry.py"}
└── entry.py        # tools = [你的python函数]（带 docstring，ADK 自动转 FunctionTool）
```

刷新设置页即被扫描注册，开关即时生效（热加载）。

### 写一个 Skill

```
backend/skills/my_skill/
└── skill.json   # {"name":"my_skill","description":"...","instruction":"指令模板，支持 {{参数}} 占位"}
```

### 接入 MCP Server

设置 → MCP → 添加，sse 填远程 URL 即可；stdio 填 `npx -y @modelcontextprotocol/server-filesystem <目录>`。

> stdio 传输会以本机权限拉起你填入的任意命令，等同于代码执行，因此**默认关闭**：
> 需在 `backend/.env` 设置 `ALLOW_STDIO_MCP=true` 后才会生效（重启后生效）。

## 安全默认值

本项目定位为**本地优先**，默认配置按"不暴露、不弱口令"取舍：

| 项 | 默认行为 |
|---|---|
| 监听地址 | `docker compose` 仅绑定 `127.0.0.1:8000`，不暴露到局域网 |
| JWT 密钥 | 无公开默认值；未配置则自动生成并持久化到 `data/secrets.json` |
| JWT 算法 | 仅允许 HS256/HS384/HS512，配置其他值会在启动时直接报错 |
| API Key 存储 | 始终经 Fernet 加密后入库（密钥自动生成，不存在明文降级） |
| 模型凭据传递 | 按请求显式传入，不写入进程环境变量，用户之间不会串用 |
| base_url | 拒绝非 http(s) 与链路本地/云元数据地址（SSRF 防护） |
| stdio MCP | 默认关闭，需 `ALLOW_STDIO_MCP=true` 显式开启 |

如需对外提供服务（局域网/公网），请至少：改为 `"8000:8000"` 暴露端口、在 `.env` 中显式设置 `JWT_SECRET`、并确认是否真的需要开放注册与 stdio MCP。

## 开发与测试

```bash
pip install -r backend/requirements.lock.txt -r backend/requirements-dev.txt
cd backend && python -m pytest -q            # 后端测试
python backend/scripts/check_requirements_lock.py   # 依赖锁文件一致性
```

CI 门禁与测试规范详见 [docs/TESTING.md](docs/TESTING.md)；注释规范见 [docs/COMMENTS.md](docs/COMMENTS.md)；贡献流程见 [AGENTS.md](AGENTS.md)。

改动直接依赖后需同步重新生成锁文件：

```bash
pip install -r backend/requirements.txt && pip freeze --exclude-editable > backend/requirements.lock.txt
```

## 可观测性说明

- 每次 LLM 调用落库 `traces` 表：模型、token 用量、TTFT、总耗时、tok/s、成本（内置定价表折算）、工具调用 span
- 聊天页每条 AI 回复底部有点击可展开的 **Trace 面板**（时间线瀑布图 + 工具调用明细）
- 「用量」页提供按天 / 按模型的 token 与成本图表、平均 TTFT 与生成速率
- 「设置 → 记忆」页展示**记忆抽取健康度**（近 30 天）：抽取次数、失败率、平均耗时与累计成本；失败按原因分类（未返回 JSON / 结构不符 / 调用失败 / 未配置 Key），可展开查看最近失败详情与模型原始输出
