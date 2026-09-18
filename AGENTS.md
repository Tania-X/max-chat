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
