# AGENTS.md

## Project
MAX Chat: FastAPI + Google ADK (DDD) backend in `backend/`; React + Vite + Tailwind frontend in `frontend/`.

## Git rules
- Verify you are on the correct branch before ANY git mutation.
- After repo init, all code changes land via pull request — never push to main directly.
- Branches are only created, never deleted. No squash merges; keep history as-is.
- Commits follow Conventional Commits: `feat|fix|refactor|chore|docs|test|perf|ci|build(scope): subject`.

## CI gates
Every push/PR runs: backend compile check, frontend build, gitleaks credential scan, commit-message lint. All must pass.

## Docs
In examples use placeholder paths (`<PROJECT_ROOT>`) or env-var paths (`$env:VENV_HOME`) — never real local paths or personal info.

## PR checklist
- Contract alignment: every PR must verify frontend/backend contracts stay in sync — REST schemas, SSE event shapes (`chunk`/`tool_call`/`tool_result`/`done`/`error`), error format (`{detail, code}`). Any contract change updates both sides in the same PR.
- Env sync: new config keys land in `config.py`, `.env.example` and `docker-compose.yml` together.
- DB schema: breaking ORM changes must note migration steps for persisted SQLite data.
