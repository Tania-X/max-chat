# MAX Chat — 类 ChatGPT 的全栈 AI 助手

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
| MCP | 作为 MCP Client 接入外部 server（stdio / sse），工具自动发现注入，失败降级 |
| 可观测性 | 每条回复记录 TTFT、tok/s、prompt/completion tokens、成本折算；Trace 瀑布图 + 用量统计图表 |

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

## 启动方式

### 后端

```powershell
# 创建虚拟环境（位置随意，示例放在项目外的环境目录）
python -m venv $env:VENV_HOME\max-chat
$env:VENV_HOME\max-chat\Scripts\pip.exe install -r requirements.txt
cd backend
$env:VENV_HOME\max-chat\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

首次启动自动建表（`backend/data/app.db`）。

**配置模型 Key**：编辑 `backend/.env`，填入 `GOOGLE_API_KEY`（Gemini 兜底模型 + 记忆抽取用），或启动后在「设置 → 模型配置」界面添加任意提供商的 Key（Fernet 加密存储）。

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

设置 → MCP → 添加，stdio 填 `npx -y @modelcontextprotocol/server-filesystem <目录>`，或 sse 填远程 URL。

## 可观测性说明

- 每次 LLM 调用落库 `traces` 表：模型、token 用量、TTFT、总耗时、tok/s、成本（内置定价表折算）、工具调用 span
- 聊天页每条 AI 回复底部有点击可展开的 **Trace 面板**（时间线瀑布图 + 工具调用明细）
- 「用量」页提供按天 / 按模型的 token 与成本图表、平均 TTFT 与生成速率
