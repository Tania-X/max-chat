# Testing

`AGENTS.md` states the rule; this file holds the detail. Read it before writing or changing tests.

## Run

```bash
cd backend && python -m pytest -q     # pytest, backend/tests/
cd frontend && npm test               # vitest, frontend/src/**/*.test.ts
```

The whole suite takes ~8s. Run it locally — CI is a backstop, not the first line of defence.

## Placement

- Backend: `backend/tests/test_<area>.py`, one file per concern. Shared fixtures live in `conftest.py` (`client`, `db_session`, `register_user`, `auth`).
- Frontend: `frontend/src/**/*.test.ts`, next to the module under test.

## Rules

- **A bug fix ships with a regression test that fails before the fix.** Prove it: revert the fix locally (`git stash push -- <paths>`), watch the test fail, restore. A test that passes both ways proves nothing.
- Test behaviour, not implementation — assert on API responses and store state, not on private helpers.
- Keep it fast. A slow suite gets skipped, and a skipped suite is worse than none.

## Isolation

- Never touch the real `backend/data/`; tests run against a temp directory.
- Never call a real model provider. Stub `AgentRuntime.run` for chat flows and `settings` for provider/key logic.
- Set test env vars in `backend/tests/conftest.py` **before** importing `app` — several modules call `get_settings()` at import time and would otherwise bind to the real database.
- Frontend tests run in node (no DOM, no jsdom); `localStorage` is stubbed in `src/test/setup.ts`. Keep testable logic in stores/libs rather than components — add jsdom only when a component test is genuinely needed.

## Out of scope

Browser/E2E tests, snapshot tests, coverage thresholds. Treat them like any other out-of-scope work (see `AGENTS.md` → Business) unless explicitly asked for.

## CI

`.github/workflows/ci.yml` runs, on every PR:

| Job | Checks |
|---|---|
| `backend-check` | pytest, `compileall`, `.env.example` freshness, `requirements.lock.txt` freshness |
| `frontend-build` | vitest, eslint, `tsc -b` + vite build |
| `credential-scan` | gitleaks over full history |
| `commit-lint` | Conventional Commits (PRs only) |
