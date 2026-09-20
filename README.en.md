# MAX Chat — a full-stack ChatGPT-style AI assistant

[简体中文](README.md) | **English**

A multi-user AI chat application built on **FastAPI + Google ADK + React**, with a **DDD layered architecture**: multi-model switching, session isolation, long-term memory, user profile, a plugin / skill / MCP tool framework, and end-to-end observability.

## Features

| Module | Description |
|---|---|
| Identity | Registration / login (JWT); all data is scoped per user |
| Chat | Multiple sessions, SSE streaming, Markdown / code highlighting, stop generation |
| Multi-model | Gemini (native ADK) plus OpenAI / Anthropic / DeepSeek etc. via LiteLLM; switchable in the UI, with a connectivity test |
| Memory & profile | Facts and preferences are extracted after each turn and injected into later context; view / edit / delete |
| Plugins | Convention-based scan of `backend/plugins/`; enable toggle + JSON config + hot reload |
| Skills | Instruction-template skills in `backend/skills/`; enable + config + hot reload |
| MCP | Acts as an MCP client for external servers (stdio / sse); tools are discovered and injected automatically, degrading gracefully on failure. stdio is off by default and must be enabled explicitly |
| Observability | Every reply records TTFT, tok/s, prompt/completion tokens and estimated cost; Trace waterfall + usage charts |

## Scope and extension points

MAX Chat is a ChatGPT-style multi-user assistant. Its core domain is **conversation experience, agent capabilities (memory / profile / tools), multi-model integration, and call observability**. Anything outside that domain (payments, social feeds, content operations, …) is out of scope. The project stays local-first and dependency-free by default — SQLite is enough to run it.

Current extension points:

| Extension point | How |
|---|---|
| New model provider | LiteLLM adapter; configure it in the settings page |
| Plugin | `backend/plugins/`; a Python function becomes a FunctionTool automatically |
| Skill | `backend/skills/`; instruction template plus an optional tool set |
| MCP tools | Add a stdio / sse server from the settings page |
| Model pricing table | `observability/infrastructure/pricing.py` |
| New business capability | Add a bounded context following the DDD layout (domain/application/infrastructure/interfaces) |

## Layout

```
backend/                 # FastAPI backend (six DDD bounded contexts)
  app/
    shared/              # config, security, database, exceptions (shared kernel)
    identity/            # BC: users and authentication
    conversation/        # BC: sessions, messages, SSE chat
    agent_runtime/       # BC: ADK agent orchestration, multi-model factory
    memory/              # BC: memory and user profile
    capability/          # BC: plugins / skills / MCP as one tool source
    observability/       # BC: traces, metrics, cost
  plugins/time_plugin/   # example plugin (current time)
  skills/code_review/    # example skill (code review)
frontend/                # React 18 + Vite 5 + TS + Tailwind
  src/pages/             # login / chat / settings / usage
  src/components/        # sidebar, message list, composer, trace panel, settings tabs
```

## Docker quickstart (recommended)

Single container, multi-stage build: Node builds the frontend → Python serves the API and the static files; SQLite is persisted in a named volume.

```bash
cp backend/.env.example backend/.env   # edit and fill in your model keys
docker compose up -d --build
# open http://127.0.0.1:8000 (bound to loopback by default — see "Secure defaults")
```

## Running locally

### Backend

```powershell
# create a virtualenv (any location; the example puts it outside the project)
python -m venv $env:VENV_HOME\max-chat
$env:VENV_HOME\max-chat\Scripts\pip.exe install -r backend\requirements.lock.txt
cd backend
$env:VENV_HOME\max-chat\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Tables are created automatically on first start (`backend/data/app.db`).

**Configuring model keys**: edit `backend/.env` and set `GOOGLE_API_KEY` (used by the fallback Gemini model and by memory extraction), or add a key for any provider from *Settings → Model config* in the UI (stored encrypted with Fernet).

**About secrets**: leave `JWT_SECRET` and `FERNET_KEY` empty — on first start strong random values are generated and written to `backend/data/secrets.json` with `0600` permissions, persisting alongside the data directory. If an older version's public default was in use, it is replaced automatically at startup and you are prompted to log in again.

### Frontend

```powershell
cd frontend
npm install   # skip if already installed
npm run dev   # http://localhost:5173, /api is proxied to 8000
```

## Extending

### Write a plugin

```
backend/plugins/my_plugin/
├── manifest.json   # {"name":"my_plugin","description":"...","entry":"entry.py"}
└── entry.py        # tools = [your python functions] (with docstrings; ADK turns them into FunctionTools)
```

Refresh the settings page and it is scanned and registered; the toggle takes effect immediately (hot reload).

### Write a skill

```
backend/skills/my_skill/
└── skill.json   # {"name":"my_skill","description":"...","instruction":"template, supports {{param}} placeholders"}
```

### Connect an MCP server

*Settings → MCP → Add*. For sse, just fill in the remote URL; for stdio, fill in e.g. `npx -y @modelcontextprotocol/server-filesystem <directory>`.

> The stdio transport spawns whatever command you enter with local privileges — equivalent to code execution — so it is **off by default**:
> set `ALLOW_STDIO_MCP=true` in `backend/.env` to enable it (takes effect after a restart).

## Secure defaults

The project is **local-first**, and the defaults trade for "not exposed, no weak credentials":

| Item | Default behaviour |
|---|---|
| Listen address | `docker compose` binds `127.0.0.1:8000` only; not exposed to the LAN |
| JWT secret | No public default; generated and persisted to `data/secrets.json` when unset |
| JWT algorithm | Only HS256/HS384/HS512; any other value fails fast at startup |
| API key storage | Always encrypted with Fernet before it is stored (the key is generated automatically; there is no plaintext fallback) |
| Model credentials | Passed explicitly per request, never written to process environment variables, so users cannot cross-contaminate each other |
| base_url | Non-http(s), link-local and cloud-metadata addresses are rejected (SSRF protection) |
| stdio MCP | Off by default; requires `ALLOW_STDIO_MCP=true` |

To expose the service (LAN or internet), at minimum: change the port mapping to `"8000:8000"`, set `JWT_SECRET` explicitly in `.env`, and decide whether you really want open registration and stdio MCP.

## Development and testing

```bash
pip install -r backend/requirements.lock.txt -r backend/requirements-dev.txt
cd backend && python -m pytest -q            # backend tests
python backend/scripts/check_requirements_lock.py   # dependency lock consistency
```

CI gates and testing conventions: [docs/TESTING.md](docs/TESTING.md). Comment conventions: [docs/COMMENTS.md](docs/COMMENTS.md). Contribution workflow: [AGENTS.md](AGENTS.md).

After changing a direct dependency, regenerate the lock file:

```bash
pip install -r backend/requirements.txt && pip freeze --exclude-editable > backend/requirements.lock.txt
```

## Observability

- Every LLM call is stored in the `traces` table: model, token usage, TTFT, total duration, tok/s, cost (from the built-in pricing table) and tool-call spans
- Each AI reply in the chat page has a collapsible **Trace panel** at the bottom (timeline waterfall + tool-call detail)
- The *Usage* page charts tokens and cost by day / by model, with average TTFT and generation rate
