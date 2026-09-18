# AGENTS.md

## Project
MAX Chat: FastAPI + Google ADK (DDD) backend `backend/`; React + Vite + Tailwind frontend `frontend/`.

## Business
MAX Chat is a ChatGPT-style multi-user AI assistant (chat, memory, tools, multi-model, observability). Changes must serve this core, stay local-first and zero-dependency; reject out-of-scope features. See README for scope.

## Git
- Check branch before ANY git mutation. After init: changes land via PR only, never direct to main.
- Branches: create only, never delete; merge commits, no squash.
- Commits: Conventional Commits (`feat|fix|refactor|chore|docs|test|perf|ci|build(scope): subject`).

## PR checklist
- Contracts: REST schemas, SSE event shapes, error format `{detail, code}` synced both sides.
- Env: new keys → `config.py` (Field description) only; regenerate `.env.example` via `python -m app.shared.env_example` (CI enforces). Compose injects whole `.env` — no per-key edits.
- DB: breaking ORM changes need migration notes.
- CI (backend compile, frontend build, gitleaks, commit-lint) must pass.

## Docs
Examples use placeholders (`<PROJECT_ROOT>`) or env vars (`$env:VENV_HOME`) — never real paths or personal info.
