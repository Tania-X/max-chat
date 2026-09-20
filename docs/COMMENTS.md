# Comments

`AGENTS.md` states the rule; this file holds the detail. Read it before adding or changing comments.

## The test

A comment must say something the code cannot: a constraint, a failure mode, an external contract, or why the obvious alternative would break.

**Explain why the code is the way it is — not how it came to be that way.**

**If deleting it loses no information, delete it.**

One or two lines. If it needs a paragraph, the code needs splitting.

## Where comments are required

On non-obvious core paths — the places where getting it wrong is silent rather than loud:

- SSE event lifecycle, streaming and cancellation behaviour
- auth and ownership checks
- secret and encryption handling
- model credential passing
- capability (plugin / skill / MCP) loading
- background task lifetime
- back-compat branches, e.g. legacy plaintext credentials

## What not to write

- Restating the signature — `# get user list` above `get_users()`.
- Change narration. The diff is already in the commit message, so a comment must not retell it:
  - ✗ `# 原来是轮询，改成 SSE 后不再丢事件` — explains why A became B.
  - ✓ `# 客户端断开时请求会被取消，所以这里用独立会话` — explains why B has to be this way.

  The past may still be named when it **constrains the present** — `# 历史数据是明文入库的，解密失败时按明文兼容`. State that as a live constraint, not as a story about the change.
- Ownerless TODOs. Link an issue or leave it out.
- Framework or library tutorials.

## Style

- Comments and docstrings in Chinese, matching the existing code. This file and `AGENTS.md` stay English.
- Module and non-trivial function docstrings: one line stating the responsibility.
- Update a comment in the same commit as the behaviour it describes. A stale comment is worse than none.

## Canonical examples

Two existing comments worth copying the shape of:

- `backend/app/conversation/interfaces/chat.py` → `persist_turn`: explains *why* it opens its own database session (the request is cancelled when the client disconnects), not what it inserts.
- `backend/app/capability/infrastructure/mcp_manager.py` → the stdio gate: states the consequence of enabling it.
